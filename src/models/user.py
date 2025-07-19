"""User model for storing Telegram user data and encrypted Todoist tokens."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class User(Base):
    """User model for storing Telegram users and their Todoist tokens."""

    __tablename__ = "users"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # Telegram data
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )
    telegram_username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    telegram_first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    telegram_last_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # Todoist data (encrypted)
    todoist_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted Todoist Personal Token"
    )

    # User preferences
    default_project: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Default Todoist project name"
    )
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="ru",
        server_default="ru",
        comment="Preferred language for transcription"
    )

    # Statistics
    task_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total number of tasks created"
    )
    last_task_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of last task creation"
    )

    # System fields
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default="CURRENT_TIMESTAMP"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default="CURRENT_TIMESTAMP",
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return (
            f"<User(id={self.id}, "
            f"telegram_user_id={self.telegram_user_id}, "
            f"username={self.telegram_username})>"
        )

    @property
    def has_todoist_token(self) -> bool:
        """Check if user has configured Todoist token."""
        return self.todoist_token_encrypted is not None

    @property
    def display_name(self) -> str:
        """Get display name for the user."""
        if self.telegram_first_name:
            name = self.telegram_first_name
            if self.telegram_last_name:
                name += f" {self.telegram_last_name}"
            return name
        return self.telegram_username or f"User {self.telegram_user_id}"
