"""LangChain agent with Notion MCP integration."""

import logging
from typing import Any

# from langchain.schema import SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.language_models import BaseLLM
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.config import settings
from src.session import SessionManager

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful Notion assistant. You can search, read, create, "
    "and update pages and databases in the user's Notion workspace. "
    "Be concise and helpful."
)


class SessionChatHistory(BaseChatMessageHistory):
    """Custom chat history backed by SQLite SessionManager."""

    def __init__(self, chat_id: int | str, session_manager: SessionManager):
        """Initialize with session manager and chat ID."""
        self.chat_id = chat_id
        self.session_manager = session_manager
        self._messages: list[BaseMessage] = []

    async def load_messages(self) -> None:
        """Load messages from session manager."""
        messages_data = await self.session_manager.get_messages(self.chat_id)
        self._messages = []
        for msg_data in messages_data:
            if msg_data.get("type") == "human":
                self._messages.append(HumanMessage(content=msg_data.get("content", "")))
            elif msg_data.get("type") == "ai":
                self._messages.append(AIMessage(content=msg_data.get("content", "")))

    @property
    def messages(self) -> list[BaseMessage]:
        """Return loaded messages."""
        return self._messages

    async def add_message(self, message: BaseMessage) -> None:
        """Add message and persist to database."""
        self._messages.append(message)
        await self._persist()

    async def _persist(self) -> None:
        """Save messages to session manager."""
        messages_data = [
            {
                "type": "human" if isinstance(m, HumanMessage) else "ai",
                "content": m.content,
            }
            for m in self._messages
        ]
        await self.session_manager.save_messages(self.chat_id, messages_data)

    async def clear(self) -> None:
        """Clear all messages."""
        self._messages = []
        await self.session_manager.clear_chat(self.chat_id)


class AgentProcessor:
    """Processes user messages with LangChain agent."""

    def __init__(
        self,
        llm: BaseLLM | None = None,
        tools: list[BaseTool] | None = None,
        session_manager: SessionManager | None = None,
        system_prompt: str | None = None,
    ):
        """Initialize agent processor.

        Args:
            llm: Language model (defaults to ChatOpenAI with poe.com)
            tools: List of tools for agent (defaults to empty)
            session_manager: Session manager instance
            system_prompt: System prompt for the agent
        """
        # Initialize LLM pointing to poe.com via OpenAI-compatible API
        self.llm = llm or ChatOpenAI(
            model=settings.poe_model_name,
            api_key=settings.poe_api_key,
            base_url=settings.poe_api_base_url,
            temperature=0.7,
            timeout=30.0,
        )

        self.tools = tools or []
        self.session_manager = session_manager or SessionManager()
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._mcp_client = None
        logger.info(
            f"AgentProcessor initialized with LLM: {settings.poe_model_name} "
            f"(base_url: {settings.poe_api_base_url})"
        )

    async def initialize(self) -> None:
        """Initialize processor (create DB, setup tools)."""
        await self.session_manager.initialize()

        # Connect to MCP servers
        server_configs: dict[str, dict[str, Any]] = {}
        if settings.notion_mcp_url:
            server_configs["notion"] = {
                "url": f"{settings.notion_mcp_url}/mcp",
                "transport": "http",
                "headers": {
                    "Authorization": f"Bearer {settings.notion_mcp_auth_token}"
                },
            }

        # Built-in MCP server for Home Assistant
        # if settings.home_assistant_url and settings.home_assistant_token:
        #     server_configs["home_assistant"] = {
        #         "url": f"{settings.home_assistant_url}/api/mcp",
        #         "transport": "streamable_http",
        #         "headers": {"Authorization": f"Bearer {settings.home_assistant_token}"},
        #     }

        # Awesome HA MCP server upgrade (https://github.com/homeassistant-ai/ha-mcp)
        if settings.ha_mcp_url:
            server_configs["home_assistant"] = {
                "url": f"{settings.ha_mcp_url}/mcp",
                "transport": "http",
            }

        client = MultiServerMCPClient(server_configs)

        # Load each server independently so one failure doesn't block others
        for server_name in server_configs:
            try:
                tools = await client.get_tools(server_name=server_name)
                self.tools.extend(tools)
                logger.info(f"Loaded {len(tools)} tools from {server_name} MCP")
            except Exception as e:
                logger.exception(f"Could not load tools from {server_name} MCP: {e}")

        self._mcp_client = client

        logger.info("Agent processor initialized")

    async def process(self, chat_id: int | str, user_message: str) -> str:
        """Process a user message and return agent response.

        Args:
            chat_id: Telegram chat ID
            user_message: User's text message

        Returns:
            Agent's text response
        """
        try:
            # Load conversation history
            logger.info(f"[{chat_id}] Loading chat history...")
            chat_history = SessionChatHistory(chat_id, self.session_manager)
            await chat_history.load_messages()

            if self.tools:
                # Tool-calling agent path (langchain 1.x API)
                logger.info(
                    f"[{chat_id}] Using tool-calling agent with {len(self.tools)} tools"
                )
                from langchain.agents import create_agent

                agent = create_agent(
                    self.llm, self.tools, system_prompt=self.system_prompt
                )
                messages = list(chat_history.messages) + [
                    HumanMessage(content=user_message)
                ]

                logger.info(
                    f"[{chat_id}] Invoking agent with {len(chat_history.messages)} history messages"
                )
                result = await agent.ainvoke({"messages": messages})
                response_text = result["messages"][-1].content
                logger.info(f"[{chat_id}] Agent response received")
            else:
                # Bare LLM path (no tools)
                logger.info(f"[{chat_id}] Using bare LLM (no tools)")
                messages = [SystemMessage(content=self.system_prompt)]
                messages.extend(
                    m
                    for m in chat_history.messages
                    if isinstance(m, (HumanMessage, AIMessage))
                )
                messages.append(HumanMessage(content=user_message))

                logger.info(
                    f"[{chat_id}] Invoking LLM with {len(messages)} messages..."
                )
                try:
                    llm_response = await self.llm.ainvoke(messages)
                    logger.info(f"[{chat_id}] LLM response received")
                    response_text = (
                        llm_response.content
                        if hasattr(llm_response, "content")
                        else str(llm_response)
                    )
                except Exception as llm_error:
                    logger.error(f"[{chat_id}] LLM invocation failed: {llm_error}")
                    # Fallback: call with just the last message as string
                    logger.info(f"[{chat_id}] Trying fallback with simple invoke...")
                    llm_response = await self.llm.invoke(user_message)
                    response_text = (
                        llm_response.content
                        if hasattr(llm_response, "content")
                        else str(llm_response)
                    )

            # Add user and AI response to history
            logger.info(f"[{chat_id}] Saving messages to history...")
            await chat_history.add_message(HumanMessage(content=user_message))
            await chat_history.add_message(AIMessage(content=response_text))

            logger.info(
                f"Chat {chat_id}: {user_message[:50]}... -> {response_text[:50]}..."
            )
            return response_text

        except Exception as e:
            logger.exception(f"Error processing message for chat {chat_id}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            return error_msg

    async def add_tools(self, tools: list[BaseTool]) -> None:
        """Add tools to the agent.

        Args:
            tools: List of tools to add
        """
        self.tools.extend(tools)
        logger.info(f"Added {len(tools)} tools to agent")

    async def cleanup(self) -> None:
        """Cleanup resources (close MCP client if needed)."""
        if self._mcp_client and hasattr(self._mcp_client, "close"):
            await self._mcp_client.close()
            logger.info("MCP client closed")
        logger.info("Agent processor cleanup completed")
