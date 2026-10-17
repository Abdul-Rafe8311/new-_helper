"""``GET /r/{edition_item_id}``: log that a story was opened, then send the reader to its source."""

import uuid
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep, current_user
from app.core.errors import AppError
from app.models import Article, Edition, EditionItem, EventType, ReaderEvent

router = APIRouter(prefix="/r", tags=["editions"], dependencies=[Depends(current_user)])


@router.get(
    "/{edition_item_id}",
    status_code=302,
    response_class=RedirectResponse,
    responses={302: {"description": "Redirect to the original article"}},
)
async def open_original(
    edition_item_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> RedirectResponse:
    row = (
        await session.execute(
            select(EditionItem.id, EditionItem.edition_id, Article.id, Article.url)
            .join(Edition, Edition.id == EditionItem.edition_id)
            .join(Article, Article.id == EditionItem.article_id)
            .where(EditionItem.id == edition_item_id, Edition.user_id == user.id)
        )
    ).first()
    # Scraped URLs are untrusted: only ever redirect to http(s).
    if row is None or urlsplit(row[3]).scheme not in ("http", "https"):
        raise AppError(404, "not_found", "That story is not in your paper")
    item_id, edition_id, article_id, url = row
    session.add(
        ReaderEvent(
            user_id=user.id,
            edition_id=edition_id,
            article_id=article_id,
            edition_item_id=item_id,
            type=EventType.OPEN,
            meta={"via": "redirect"},
        )
    )
    await session.commit()
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})
