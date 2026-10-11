"""Guest session middleware: no login, just a signed cookie + a `sessions` row.

Every request gets (or keeps) an opaque session id. The cookie is signed so a client
can't forge an arbitrary session id to read another session's quota/usage row.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from itsdangerous import BadSignature, URLSafeSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.db import SessionLocal
from app.entities import Session as SessionRow


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        serializer = URLSafeSerializer(settings.session_secret)
        cookie = request.cookies.get(settings.session_cookie_name)

        session_id: uuid.UUID | None = None
        if cookie:
            try:
                session_id = uuid.UUID(serializer.loads(cookie))
            except (BadSignature, ValueError):
                session_id = None

        now = datetime.now(timezone.utc)
        async with SessionLocal() as db:
            row = None
            if session_id is not None:
                row = await db.get(SessionRow, session_id)
                if row is not None and row.expires_at.replace(tzinfo=timezone.utc) < now:
                    row = None  # expired: issue a fresh one

            is_new = row is None
            if is_new:
                row = SessionRow(expires_at=now + timedelta(hours=settings.session_ttl_hours))
                db.add(row)
            else:
                row.last_active_at = now
            await db.commit()
            await db.refresh(row)
            session_id = row.id

        request.state.session_id = session_id
        response = await call_next(request)

        if is_new:
            response.set_cookie(
                settings.session_cookie_name,
                serializer.dumps(str(session_id)),
                httponly=True,
                samesite="lax",
                max_age=settings.session_ttl_hours * 3600,
            )
        return response
