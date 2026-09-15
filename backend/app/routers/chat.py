from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models import Conversation, Message, utcnow
from app.schemas import ChatRequest, ChatResponse
from app.services.conversation_service import get_conversation, get_recent_context, make_title
from app.services.openai_service import generate_reply

router = APIRouter(prefix="/api", tags=["chat"])



@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    if request.retention == "ephemeral":
        try:
            answer = await generate_reply([{"role": "user", "content": request.message}])
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            print(f"OpenAI request failed: {exc}")
            raise HTTPException(status_code=502, detail="The AI service request failed.") from exc

        return ChatResponse(
            answer=answer,
            model=settings.openai_model,
            conversation_id=None,
            saved=False,
        )

    if request.conversation_id is not None:
        conversation = await get_conversation(db, request.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    else:
        conversation = Conversation(
            title=make_title(request.message),
            content_type="general",
            retention_type=request.retention,
        )
        db.add(conversation)
        await db.flush()

    context = await get_recent_context(db, conversation.id)
    context.append({"role": "user", "content": request.message})

    try:
        answer = await generate_reply(context)
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        print(f"OpenAI request failed: {exc}")
        raise HTTPException(status_code=502, detail="The AI service request failed.") from exc
    
    remember = request.retention =="memory"

    db.add_all([
        Message(conversation_id=conversation.id, role="user", content=request.message, memory_candidate = remember,),
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            model=settings.openai_model,
            memory_candidate = remember,
        ),
    ])
    conversation.updated_at = utcnow()
    await db.commit()

    return ChatResponse(
        answer=answer,
        model=settings.openai_model,
        conversation_id=conversation.id,
        saved=True,
    )
