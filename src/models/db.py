"""Database models for the bot."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class User(Base):
    """User model."""

    __tablename__ = "users"

    # Telegram user ID as primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ru")

    # Todoist integration
    todoist_token_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    todoist_default_project: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Statistics
    tasks_created: Mapped[int] = mapped_column(default=0)
    last_task_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation."""
        return f"<User(id={self.id}, username='{self.username}')>"


class Task(Base):
    """Task history model."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    # Original message
    message_text: Mapped[str] = mapped_column(String(4096))
    message_type: Mapped[str] = mapped_column(String(20))  # text, voice, video_note

    # Parsed task data
    task_content: Mapped[str] = mapped_column(String(500))
    task_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    task_due: Mapped[str | None] = mapped_column(String(100), nullable=True)
    task_priority: Mapped[int | None] = mapped_column(nullable=True)
    task_project: Mapped[str | None] = mapped_column(String(100), nullable=True)
    task_labels: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON array

    # Todoist integration
    todoist_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    todoist_url: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tasks")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Task(id={self.id}, content='{self.task_content[:50]}...')>"
