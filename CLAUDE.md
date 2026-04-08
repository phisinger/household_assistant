# Household Assistant

AI-powered Telegram bot with Notion (shopping list) + Home Assistant (smart home control) via MCP.

## Stack

- **Bot**: aiogram 3.26+ (Telegram)
- **API**: FastAPI webhook on port 8000
- **LLM**: ChatOpenAI → poe.com (Gemini backend)
- **Storage**: SQLite per-chat history
- **MCP**: Notion + Home Assistant via HTTP transport

## Files

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI app, system prompt loading, webhook |
| `src/bot.py` | Telegram message handler |
| `src/agent.py` | LangChain agent, MCP tool loading |
| `src/session.py` | SQLite chat history with TTL expiry |
| `src/config.py` | Settings from `.env` |
| `src/system_prompt.md` | AI behavior (German): shopping + home control |

## Setup

```bash
cp .env.example .env
# Fill required vars: TELEGRAM_BOT_TOKEN, POE_API_KEY, NOTION_API_KEY, 
#                      NOTION_MCP_AUTH_TOKEN, HOMEASSISTANT_MCP_AUTH_TOKEN

pip install -e .
docker compose up --build
```

## Environment Variables

**Required**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`, `POE_API_KEY`, `NOTION_API_KEY`, `NOTION_MCP_AUTH_TOKEN`, `HOMEASSISTANT_MCP_AUTH_TOKEN`

**Optional**: `POE_MODEL_NAME` (gemini-2-flash), `NOTION_MCP_URL` (http://notion-mcp:3000), `HOMEASSISTANT_MCP_URL` (http://homeassistant-mcp:3001), `DATABASE_PATH` (./data/sessions.db), `SESSION_TTL_MINUTES` (15)

## Architecture

```
Telegram → FastAPI /webhook → aiogram → Agent
  → system_prompt.md injected
  → LLM + MCP tools (Notion, Home Assistant)
  → SQLite history
```

## Implementation

**System Prompt**: Edit `src/system_prompt.md`, restart to apply (no code changes needed)

**MCP Tools**: Loaded from `NOTION_MCP_URL` and `HOMEASSISTANT_MCP_URL` at startup. Gracefully degrades if unavailable.

**Sessions**: Auto-cleanup of expired chats on access (TTL: 15 min default). Messages stored as JSON per chat.

**Webhook**: Requires `X-Telegram-Bot-Api-Secret-Token` header matching `TELEGRAM_WEBHOOK_SECRET`.

## Deployment

Container binds to 127.0.0.1:8000 (localhost only). Access via Cloudflare Tunnel (nilli-telegram) for public HTTPS.

- Webhook URL: https://nilli-telegram.aiautomationhosting.cloud/webhook
- Monitor: `systemctl status cloudflared && sudo journalctl -u cloudflared -f`
