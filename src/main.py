"""FastAPI main application with Telegram webhook."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from src.agent import AgentProcessor
from src.bot import set_agent_processor, setup_bot_handlers
from src.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global instances
bot: Bot | None = None
dp: Dispatcher | None = None
agent_processor: AgentProcessor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global bot, dp, agent_processor

    logger.info("Starting up...")

    try:
        # Load system prompt from file if available
        system_prompt = None
        system_prompt_path = Path(__file__).parent / "system_prompt.md"
        if system_prompt_path.exists():
            system_prompt = system_prompt_path.read_text(encoding="utf-8")
            logger.info(f"Loaded system prompt from {system_prompt_path}")

        # Initialize agent processor
        agent_processor = AgentProcessor(system_prompt=system_prompt)
        await agent_processor.initialize()
        set_agent_processor(agent_processor)

        # Initialize bot and dispatcher with FSM storage
        bot = Bot(token=settings.telegram_bot_token)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Setup bot handlers
        setup_bot_handlers(dp)

        # Register webhook
        await bot.set_webhook(
            url=f"{settings.telegram_webhook_url}",
            secret_token=settings.telegram_webhook_secret,
        )

        logger.info(
            f"Webhook registered: {settings.telegram_webhook_url}"
        )

        yield

    finally:
        logger.info("Shutting down...")
        if agent_processor:
            await agent_processor.cleanup()
        if bot:
            await bot.session.close()


# Create FastAPI app
app = FastAPI(
    title="Notion Assistant",
    description="AI-powered Telegram bot with Notion integration",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/webhook")
async def handle_telegram_update(
    update: Update,
    x_telegram_bot_api_secret_token: str = Header(None),
) -> JSONResponse:
    """Handle incoming Telegram updates via webhook.

    Args:
        update: Telegram update object
        x_telegram_bot_api_secret_token: Telegram secret token header

    Returns:
        JSON response
    """
    if not x_telegram_bot_api_secret_token:
        logger.warning("Missing Telegram secret token in webhook request")
        raise HTTPException(status_code=403, detail="Missing secret token")

    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        logger.warning("Invalid Telegram secret token in webhook request")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    if not dp:
        logger.error("Dispatcher not initialized")
        raise HTTPException(status_code=500, detail="Bot not initialized")

    try:
        # Process update with dispatcher
        await dp.feed_update(bot, update)
        return JSONResponse({"ok": True})

    except Exception as e:
        logger.exception(f"Error processing Telegram update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/webhook")
async def delete_webhook() -> dict:
    """Delete webhook (for development/cleanup).

    Returns:
        Success message
    """
    if not bot:
        raise HTTPException(status_code=500, detail="Bot not initialized")

    try:
        await bot.delete_webhook()
        logger.info("Webhook deleted")
        return {"message": "Webhook deleted successfully"}

    except Exception as e:
        logger.exception(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete webhook")


if __name__ == "__main__":

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )
