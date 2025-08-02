"""User repository for database operations."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by Telegram ID.

        Args:
            user_id: Telegram user ID

        Returns:
            User object or None
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None
    ) -> User:
        """Create or update user.

        Args:
            user_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            language_code: User's language code

        Returns:
            User object
        """
        user = await self.get_by_id(user_id)

        if user:
            # Update existing user
            if username is not None:
                user.username = username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if language_code is not None:
                user.language_code = language_code

            logger.info(f"Updated user {user_id}")
        else:
            # Create new user
            user = User(
                id=user_id,
                username=username,
                first_name=first_name or "Unknown",
                last_name=last_name,
                language_code=language_code or "ru"
            )
            self.session.add(user)
            logger.info(f"Created new user {user_id}")

        await self.session.commit()
        return user

    async def update_todoist_token(self, user_id: int, encrypted_token: str) -> bool:
        """Update user's Todoist token.

        Args:
            user_id: Telegram user ID
            encrypted_token: Encrypted Todoist token

        Returns:
            Success status
        """
        user = await self.get_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return False

        user.todoist_token_encrypted = encrypted_token
        await self.session.commit()
        logger.info(f"Updated Todoist token for user {user_id}")
        return True

    async def get_todoist_token(self, user_id: int) -> str | None:
        """Get user's encrypted Todoist token.

        Args:
            user_id: Telegram user ID

        Returns:
            Encrypted token or None
        """
        user = await self.get_by_id(user_id)
        return user.todoist_token_encrypted if user else None

    async def increment_tasks_count(self, user_id: int) -> None:
        """Increment user's task count.

        Args:
            user_id: Telegram user ID
        """
        user = await self.get_by_id(user_id)
        if user:
            user.tasks_created += 1
            user.last_task_at = datetime.now(UTC)
            await self.session.commit()

    async def delete(self, user_id: int) -> bool:
        """Delete user and all related data.

        Args:
            user_id: Telegram user ID

        Returns:
            Success status
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False

        await self.session.delete(user)
        await self.session.commit()
        logger.info(f"Deleted user {user_id}")
        return True

    async def update(self, user: User) -> None:
        """Update user in database.
        
        Args:
            user: User object to update
        """
        await self.session.commit()
        logger.info(f"Updated user {user.id}")
    
    async def get_all_users(self) -> list[User]:
        """Get all users from database.
        
        Returns:
            List of all users
        """
        result = await self.session.execute(select(User))
        return list(result.scalars().all())
