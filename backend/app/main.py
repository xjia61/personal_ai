from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import close_db, init_db
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.search import router as search_router
from app.routers.jobs import router as jobs_router

from time import perf_counter
from fastapi import Request

from app.routers.career import router as career_router

from app.core.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Personal AI API", version="0.2.0", lifespan=lifespan)

logger = setup_logging()


@app.middleware("http")
async def log_requests(request: Request, call_next):

    start = perf_counter()

    response = await call_next(request)

    duration = (
        perf_counter() - start
    ) * 1000

    if request.url.path.startswith("/api/"):

        logger.info(
            "api_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
            }
        )

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(search_router)
app.include_router(jobs_router)
app.include_router(career_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
