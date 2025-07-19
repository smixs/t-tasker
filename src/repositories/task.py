"""Task repository for database operations."""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db import Task
from src.models.task import TaskSchema

logger = logging.getLogger(__name__)


class TaskRepository:
    """Repository for task operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    async def create(
        self,
        user_id: int,
        message_text: str,
        message_type: str,
        task_schema: TaskSchema,
        todoist_id: str | None = None,
        todoist_url: str | None = None
    ) -> Task:
        """Create task record.

        Args:
            user_id: Telegram user ID
            message_text: Original message text
            message_type: Message type (text, voice, video_note)
            task_schema: Parsed task schema
            todoist_id: Todoist task ID
            todoist_url: Todoist task URL

        Returns:
            Created task
        """
        task = Task(
            user_id=user_id,
            message_text=message_text,
            message_type=message_type,
            task_content=task_schema.content,
            task_description=task_schema.description,
            task_due=task_schema.due_string,
            task_priority=task_schema.priority,
            task_project=task_schema.project_name,
            task_labels=json.dumps(task_schema.labels) if task_schema.labels else None,
            todoist_id=todoist_id,
            todoist_url=todoist_url
        )

        self.session.add(task)
        await self.session.commit()

        logger.info(f"Created task record {task.id} for user {user_id}")
        return task

    async def get_user_tasks(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> list[Task]:
        """Get user's tasks.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of tasks
            offset: Offset for pagination

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars())

    async def count_user_tasks(self, user_id: int) -> int:
        """Count user's tasks.

        Args:
            user_id: Telegram user ID

        Returns:
            Number of tasks
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Task.id)).where(Task.user_id == user_id)
        )
        return result.scalar() or 0

    async def get_last_task(self, user_id: int) -> Task | None:
        """Get user's last created task with todoist_id.

        Args:
            user_id: Telegram user ID

        Returns:
            Last task or None if no tasks with todoist_id
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.todoist_id.isnot(None))
            .order_by(Task.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_recent_tasks(
        self,
        user_id: int,
        limit: int = 5
    ) -> list[Task]:
        """Get user's recent tasks with todoist_id.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of tasks

        Returns:
            List of recent tasks
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.todoist_id.isnot(None))
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def delete_task_record(self, task_id: int) -> bool:
        """Delete task record from database.

        Args:
            task_id: Database task ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if task:
            await self.session.delete(task)
            await self.session.commit()
            logger.info(f"Deleted task record {task_id}")
            return True

        return False
