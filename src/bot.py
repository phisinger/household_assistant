"""Telegram bot handler using aiogram."""

import logging

from aiogram import Dispatcher, Router, types

from src.agent import AgentProcessor

logger = logging.getLogger(__name__)

# Global agent processor (initialized in main.py)
agent_processor: AgentProcessor | None = None
router = Router()


@router.message()
async def handle_message(message: types.Message) -> None:
    """Handle incoming Telegram messages.

    Args:
        message: Incoming Telegram message
    """
    if not agent_processor:
        logger.error("Agent processor not initialized")
        await message.reply("Bot is not initialized. Please try again later.")
        return

    if not message.text:
        logger.warning(f"Received non-text message from {message.chat.id}")
        await message.reply("Please send a text message.")
        return

    try:
        import asyncio

        # Process message with agent (with timeout)
        chat_id = message.chat.id
        logger.info(f"Processing message from {chat_id}: {message.text[:50]}")

        try:
            response = await asyncio.wait_for(
                agent_processor.process(chat_id, message.text),
                timeout=45.0,  # seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Agent processing timed out for chat {chat_id}")
            response = "Sorry, the request took too long. Please try again."

        logger.info(f"Got response: {response[:50]}")

        # Send response
        await message.reply(response)

    except Exception:
        logger.exception(f"Error handling message from {message.chat.id}")
        await message.reply(
            "Sorry, I encountered an error while processing your message. Please try again."
        )


def setup_bot_handlers(dp: Dispatcher) -> None:
    """Setup bot message handlers.

    Args:
        dp: aiogram Dispatcher instance
    """
    dp.include_router(router)


def set_agent_processor(processor: AgentProcessor) -> None:
    """Set the global agent processor instance.

    Args:
        processor: AgentProcessor instance
    """
    global agent_processor
    agent_processor = processor
    logger.info("Agent processor set in bot handler")
