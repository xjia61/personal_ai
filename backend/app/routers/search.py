from fastapi import APIRouter, HTTPException, Query

from app.services.search_service import (
    WebSearchError,
    search_web,
)

router = APIRouter(
    prefix="/api/search",
    tags=["search"],
)


@router.get("")
async def web_search(
    q: str = Query(min_length=2),
):
    try:
        results = await search_web(
            query=q,
            max_results=5,
        )

        return {
            "query": q,
            "results": results,
        }

    except WebSearchError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc