import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://personal_ai:personal_ai@localhost:5432/personal_ai",
    )
    context_message_limit: int = int(os.getenv("CONTEXT_MESSAGE_LIMIT", "20"))


settings = Settings()
