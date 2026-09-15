# Personal AI — V0.2

This version adds PostgreSQL-backed conversation history.

## What changed

- PostgreSQL via Docker Compose
- SQLAlchemy async ORM
- `Conversation` and `Message` tables
- Saved multi-turn conversations
- `retention="ephemeral"` mode for throwaway requests
- Conversation list/detail/delete endpoints
- Recent saved messages are automatically reused as context
- Memory-ready fields for the next selective-memory stage

## 1. Start PostgreSQL

From the project root:

```bash
docker compose up -d
docker compose ps
```

## 2. Install backend dependencies

```bash
cd backend
source .venv/bin/activate   # if you already created the venv
pip install -r requirements.txt
```

If this is a fresh copy:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure `.env`

Keep your existing OpenAI key and add the database URL:

```env
OPENAI_API_KEY=your_real_key
OPENAI_MODEL=gpt-5.6-luna
DATABASE_URL=postgresql+asyncpg://personal_ai:personal_ai@localhost:5432/personal_ai
CONTEXT_MESSAGE_LIMIT=20
```

## 4. Run FastAPI

```bash
fastapi dev app/main.py
```

Open http://127.0.0.1:8000/docs

## 5. Test a saved conversation

First request to `POST /api/chat`:

```json
{
  "message": "My favorite programming language is Python.",
  "retention": "save"
}
```

Copy the returned `conversation_id`, then send:

```json
{
  "message": "What language did I just say I like?",
  "conversation_id": 1,
  "retention": "save"
}
```

The model should answer Python because the backend reloads recent messages from PostgreSQL.

## 6. Test a request that is not stored

```json
{
  "message": "Translate: I will arrive ten minutes late.",
  "retention": "ephemeral"
}
```

The response should contain:

```json
"saved": false
```

and `conversation_id` should be `null`.

## 7. View history

- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`

## Next

V0.3 will add the React interface: sidebar history, new chat, reopening old chats, and a Save/Ephemeral control.
