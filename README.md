# Notion Assistant

AI-powered personal assistant: Telegram bot with Notion shopping list management and Home Assistant control via MCP.

## Features

- 🤖 Gemini LLM via poe.com  
- 💬 Multi-turn conversations with session memory (15 min TTL)
- 📝 Notion integration (shopping list, recipe management)
- 🏠 Home Assistant smart home control
- ⚙️ Customizable system prompt (edit markdown, no code changes)
- 🐳 Docker containerization

## Stack

- **Telegram**: aiogram 3.26+
- **API**: FastAPI webhook on port 8000
- **LLM**: ChatOpenAI → poe.com (Gemini backend)
- **Storage**: SQLite per-chat conversation history
- **MCP**: Notion + Home Assistant via HTTP

## Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot Token (from @BotFather)
- poe.com API Key
- Notion Integration Token

### Setup
```bash
git clone <repository>
cd notion_assistant
cp .env.example .env

# Fill .env with credentials
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
TELEGRAM_WEBHOOK_SECRET=your_secret
POE_API_KEY=your_poe_key
NOTION_API_KEY=your_notion_key
NOTION_MCP_AUTH_TOKEN=your_mcp_token

pip install -e .
docker compose up --build
```

### Local Development
```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# For local webhook testing with ngrok
ngrok http 8000
# Update .env: TELEGRAM_WEBHOOK_URL=https://<ngrok-url>/webhook
```

## System Prompt Customization

The bot's behavior is defined in `src/system_prompt.md` (loaded at startup):

**Current prompt** (German): Shopping list management (Notion) + Home Assistant control

**To customize**:
1. Edit `src/system_prompt.md`
2. Restart container: `docker compose restart assistant`
3. Changes apply immediately (no code changes needed)

## Project Structure

```
src/
  ├── main.py              # FastAPI app, loads system_prompt.md
  ├── bot.py               # Telegram message handler
  ├── agent.py             # LangChain agent + MCP tool loading
  ├── session.py           # SQLite sessions (15 min TTL)
  ├── config.py            # .env configuration
  └── system_prompt.md     # AI system prompt (customizable)

docker-compose.yml         # Assistant + notion-mcp services
pyproject.toml             # Dependencies
.env.example               # Environment template
```

## API Endpoints

- `GET /health` - Health check
- `POST /webhook` - Telegram webhook (requires `X-Telegram-Bot-Api-Secret-Token` header)
- `DELETE /webhook` - Delete webhook (dev only)

## Environment Variables

**Required**:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_URL`
- `TELEGRAM_WEBHOOK_SECRET`
- `POE_API_KEY`
- `NOTION_API_KEY`
- `NOTION_MCP_AUTH_TOKEN`
- `HOMEASSISTANT_MCP_AUTH_TOKEN`

**Optional**:
- `POE_MODEL_NAME` (default: gemini-2-flash)
- `NOTION_MCP_URL` (default: http://notion-mcp:3000)
- `HOMEASSISTANT_MCP_URL` (default: http://homeassistant-mcp:3001)
- `DATABASE_PATH` (default: ./data/sessions.db)
- `SESSION_TTL_MINUTES` (default: 15)

## License

MIT
