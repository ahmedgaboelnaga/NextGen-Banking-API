import random
import uuid

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from authlib.integrations.starlette_client import OAuth

from backend.app.auth.models import User
from backend.app.auth.oauth.models import UserProvider
from backend.app.auth.schema import AccountStatusSchema, SecurityQuestionSchema
from backend.app.auth.utils import generate_password_hash, generate_username
from backend.app.core.config import settings
from backend.app.core.i18n import _
from backend.app.core.logging import get_logger

logger = get_logger()

# ---------------------------------------------------------------------------
# Authlib OAuth client — single application-wide instance
# ---------------------------------------------------------------------------

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class OAuthService:
    # ------------------------------------------------------------------
    # Provider record helpers
    # ------------------------------------------------------------------

    async def get_provider_record(
        self,
        provider: str,
        provider_id: str,
        session: AsyncSession,
    ) -> UserProvider | None:
        """Return the UserProvider row that maps (provider, provider_id) to a user."""
        result = await session.exec(
            select(UserProvider)
            .where(UserProvider.provider == provider)
            .where(UserProvider.provider_id == str(provider_id))
        )
        return result.first()

    async def link_provider(
        self,
        user_uid: uuid.UUID,
        provider: str,
        provider_id: str,
        session: AsyncSession,
    ) -> UserProvider:
        """Create a new UserProvider record linking a user to an OAuth provider."""
        record = UserProvider(
            user_uid=user_uid,
            provider=provider,
            provider_id=str(provider_id),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        logger.info(
            f"Linked provider '{provider}' (id={provider_id}) to user {user_uid}"
        )
        return record

    async def get_user_by_provider_uid(
        self,
        record: UserProvider,
        session: AsyncSession,
    ) -> User:
        """Resolve the User that owns a given UserProvider record."""
        result = await session.exec(select(User).where(User.id == record.user_uid))
        user = result.first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": _("Associated user account not found."),
                    "action": _("Please contact support."),
                },
            )
        return user

    # ------------------------------------------------------------------
    # OAuth user creation
    # ------------------------------------------------------------------

    async def _generate_unique_id_no(self, session: AsyncSession) -> int:
        """Generate a random 7-digit id_no that doesn't already exist."""
        for _ in range(10):
            candidate = random.randint(1_000_000, 9_999_999)
            result = await session.exec(select(User).where(User.id_no == candidate))
            if result.first() is None:
                return candidate
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("Failed to generate a unique user ID. Please try again."),
                "action": _("Please try again later."),
            },
        )

    async def create_oauth_user(
        self,
        google_info: dict,
        session: AsyncSession,
    ) -> User:
        """
        Create a brand-new User from Google userinfo payload.
        The account is immediately active because Google verified the email.
        """
        email: str = google_info["email"]
        first_name: str = (google_info.get("given_name") or email.split("@")[0])[:30]
        last_name: str = (google_info.get("family_name") or "User")[:30]

        id_no = await self._generate_unique_id_no(session)

        # A random hash the user can never reproduce — locks out password login
        dummy_hash = generate_password_hash(uuid.uuid4().hex)

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            id_no=id_no,
            hashed_password=dummy_hash,
            username=generate_username(),
            is_active=True,
            account_status=AccountStatusSchema.ACTIVE,
            # Required schema fields — user can update these later
            security_question=SecurityQuestionSchema.FAVORITE_COLOR,
            security_answer="oauth_placeholder",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Created new OAuth user: {user.email}")
        return user

    # ------------------------------------------------------------------
    # Main entry-point
    # ------------------------------------------------------------------

    async def get_or_create_user_via_google(
        self,
        google_info: dict,
        session: AsyncSession,
    ) -> User:
        """
        Full Google OAuth user-resolution flow:

        1. If a UserProvider row already maps this Google sub → return that user.
        2. If a User with the same email exists → link the provider and return the user.
        3. Otherwise create a new User and link the provider.

        Uses user_auth_service for all shared user-lookup logic.
        """
        # Import here to avoid circular imports
        from backend.app.api.services.user_auth import user_auth_service

        provider = "google"
        provider_id: str = str(google_info["sub"])
        email: str = google_info["email"]

        # ① Check for an existing provider binding
        record = await self.get_provider_record(provider, provider_id, session)
        if record is not None:
            user = await self.get_user_by_provider_uid(record, session)
            logger.info(f"OAuth login for existing user: {user.email}")
            return user

        # ② Check for an existing user with the same email (account linking).
        #    include_inactive=True so we link even if the account is not yet verified.
        user = await user_auth_service.get_user_by_email(
            email=email, session=session, include_inactive=True
        )
        if user is not None:
            await self.link_provider(user.id, provider, provider_id, session)
            logger.info(f"Linked Google account to existing user: {user.email}")
            return user

        # ③ Brand-new user
        user = await self.create_oauth_user(google_info, session)
        await self.link_provider(user.id, provider, provider_id, session)
        return user


oauth_service = OAuthService()
