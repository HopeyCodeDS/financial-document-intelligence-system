"""
UserService — authentication business logic.

Sits between the auth router and the repository so that login flow,
password verification, and audit emission live in one testable place.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.repositories.user import UserRepository
from app.models.audit_log import AuditEventStatus
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services.audit.logger import AuditLogger


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)
        self._audit = AuditLogger(session)

    async def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> User | None:
        """
        Return the User on valid credentials, otherwise None.
        """
        user = await self._repo.get_by_email(email)
        # Run verify even when the user is unknown to keep timing constant
        # against email enumeration attacks.
        provided_hash = user.password_hash if user else _get_dummy_hash()
        ok = verify_password(password, provided_hash)

        if user is None or not ok or not user.is_active:
            await self._audit.log_security_event(
                event_type="auth.login.failed",
                actor=email.lower(),
                status=AuditEventStatus.failure,
                details={
                    "reason": (
                        "unknown_email" if user is None
                        else "inactive" if not user.is_active
                        else "bad_password"
                    ),
                },
                ip_address=ip_address,
            )
            return None

        await self._repo.touch_last_login(user.id)
        await self._audit.log_security_event(
            event_type="auth.login.succeeded",
            actor=str(user.id),
            status=AuditEventStatus.success,
            details={"email": user.email, "role": user.role.value},
            ip_address=ip_address,
        )
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._repo.get_by_id(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self._repo.get_by_email(email)

    async def create(self, payload: UserCreate) -> User:
        """
        Create a new user. Used by seed scripts and admin flows.
        """
        user = User(
            email=str(payload.email),
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
            role=payload.role,
        )
        return await self._repo.save(user)

    async def ensure(self, payload: UserCreate) -> tuple[User, bool]:
        """
        Idempotent create: returns (user, created_flag).
        """
        existing = await self._repo.get_by_email(str(payload.email))
        if existing is not None:
            return existing, False
        return await self.create(payload), True


_DUMMY_HASH: str | None = None


def _get_dummy_hash() -> str:
    """Lazily computed bcrypt hash used to keep `authenticate()` timing constant
    when the supplied email is unknown. Computed once on first use so module
    import never depends on bcrypt being healthy."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("__nonexistent_user_dummy__")
    return _DUMMY_HASH
