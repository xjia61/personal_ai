from openai import AsyncOpenAI
from app.config import settings

SYSTEM_INSTRUCTIONS = """
You are a helpful personal AI assistant.
Answer clearly and concisely.
Use supplied conversation history when it is relevant.
Do not claim to remember information that has not been supplied to you.
"""


async def generate_reply(messages: list[dict[str, str]]) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to backend/.env.")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.responses.create(
        model=settings.openai_model,
        instructions=SYSTEM_INSTRUCTIONS,
        input=messages,
    )
    return response.output_text
