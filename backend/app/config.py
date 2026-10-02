import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://personal_ai:personal_ai@localhost:5433/personal_ai",
    )
    context_message_limit: int = int(os.getenv("CONTEXT_MESSAGE_LIMIT", "20"))


settings = Settings()
