"""Command executor for handling user commands."""

import logging
from datetime import datetime

from src.core.database import get_database
from src.core.exceptions import BotError, TodoistError
from src.models.intent import CommandExecution
from src.repositories.task import TaskRepository
from src.services.todoist_service import TodoistService

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes commands based on parsed intent."""

    def __init__(self) -> None:
        """Initialize command executor."""
        self.db = get_database()

    async def execute(
        self,
        command: CommandExecution,
        user_id: int,
        todoist_token: str
    ) -> str:
        """Execute command and return formatted response.

        Args:
            command: Command to execute
            user_id: User ID
            todoist_token: Todoist API token

        Returns:
            Formatted HTML response for Telegram

        Raises:
            BotError: If command execution fails
        """
        try:
            if command.command_type == "view_tasks":
                return await self._view_tasks(command, todoist_token)
            elif command.command_type == "delete_task":
                return await self._delete_task(command, user_id, todoist_token)
            elif command.command_type == "update_task":
                return await self._update_task(command, user_id, todoist_token)
            elif command.command_type == "complete_task":
                return await self._complete_task(command, user_id, todoist_token)
            else:
                raise BotError(f"Unknown command type: {command.command_type}")
        except TodoistError as e:
            logger.error(f"Todoist error executing command: {e}")
            raise BotError(f"Ошибка Todoist: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error executing command: {e}", exc_info=True)
            raise BotError(f"Ошибка выполнения команды: {str(e)}")

    async def _view_tasks(
        self,
        command: CommandExecution,
        todoist_token: str
    ) -> str:
        """View tasks based on filters."""
        async with TodoistService(todoist_token) as todoist:
            # Determine filter string based on target
            filter_string = None
            title = "📋 Все задачи"

            if command.target == "today":
                filter_string = "today"
                title = "📅 Задачи на сегодня"
            elif command.target == "tomorrow":
                filter_string = "tomorrow"
                title = "📆 Задачи на завтра"
            elif command.target == "all":
                filter_string = None
                title = "📋 Все активные задачи"

            # Apply priority filter if specified
            if command.filters and "priority" in command.filters:
                priority = command.filters["priority"]
                filter_string = f"p{priority}"
                title = f"🔴 Задачи с приоритетом {priority}"

            # Get tasks
            tasks = await todoist.get_tasks(filter_string=filter_string, limit=20)

            if not tasks:
                return f"{title}\n\n<i>Задач не найдено</i>"

            # Format response
            response = f"<b>{title}</b>\n\n"

            for i, task in enumerate(tasks, 1):
                # Priority emoji
                priority = task.get("priority", 1)
                priority_emoji = {1: "⚪", 2: "🔵", 3: "🟡", 4: "🔴"}.get(priority, "⚪")

                # Task content
                content = task.get("content", "Без названия")

                # Due date
                due = task.get("due")
                due_str = ""
                if due:
                    due_date = due.get("date", "")
                    due_time = due.get("datetime", "")
                    if due_time:
                        # Parse and format datetime
                        try:
                            dt = datetime.fromisoformat(due_time.replace("Z", "+00:00"))
                            due_str = f" 📅 {dt.strftime('%d.%m %H:%M')}"
                        except:
                            due_str = f" 📅 {due_date}"
                    elif due_date:
                        due_str = f" 📅 {due_date}"

                # Project name
                project_id = task.get("project_id")
                project_str = ""
                if project_id:
                    # Try to get project name from cache
                    try:
                        projects = await todoist.get_projects()
                        project = next((p for p in projects if p["id"] == project_id), None)
                        if project:
                            project_str = f" 📁 {project['name']}"
                    except:
                        pass

                # Labels
                labels = task.get("labels", [])
                labels_str = ""
                if labels:
                    labels_str = " 🏷️ " + ", ".join(labels)

                # Format task line
                response += f"{i}. {priority_emoji} {content}{due_str}{project_str}{labels_str}\n"

            return response

    async def _delete_task(
        self,
        command: CommandExecution,
        user_id: int,
        todoist_token: str
    ) -> str:
        """Delete task based on target."""
        if command.target != "last":
            return "❌ Пока поддерживается только удаление последней задачи"

        # Get last task from database
        async with self.db.get_session() as session:
            task_repo = TaskRepository(session)
            last_task = await task_repo.get_last_task(user_id)

            if not last_task or not last_task.todoist_id:
                return "❌ Последняя задача не найдена"

            # Delete from Todoist
            async with TodoistService(todoist_token) as todoist:
                success = await todoist.delete_task(last_task.todoist_id)

                if success:
                    # Delete from database
                    await task_repo.delete_task_record(last_task.id)

                    # Get task content for confirmation
                    task_data = last_task.task_data or {}
                    content = task_data.get("content", "Задача")

                    return f"✅ Удалена задача: <i>{content}</i>"
                else:
                    return "❌ Не удалось удалить задачу в Todoist"

    async def _update_task(
        self,
        command: CommandExecution,
        user_id: int,
        todoist_token: str
    ) -> str:
        """Update task based on target and updates."""
        if command.target != "last":
            return "❌ Пока поддерживается только изменение последней задачи"

        if not command.updates:
            return "❌ Не указаны изменения для задачи"

        # Get last task from database
        async with self.db.get_session() as session:
            task_repo = TaskRepository(session)
            last_task = await task_repo.get_last_task(user_id)

            if not last_task or not last_task.todoist_id:
                return "❌ Последняя задача не найдена"

            # Prepare updates
            todoist_updates = {}
            update_descriptions = []

            if "priority" in command.updates:
                priority = int(command.updates["priority"])
                todoist_updates["priority"] = priority
                priority_text = {1: "обычный", 2: "средний", 3: "высокий", 4: "срочный"}.get(priority, str(priority))
                update_descriptions.append(f"приоритет → {priority_text}")

            if "due_string" in command.updates:
                due_string = str(command.updates["due_string"])
                todoist_updates["due_string"] = due_string
                update_descriptions.append(f"срок → {due_string}")

            if "content" in command.updates:
                content = str(command.updates["content"])
                todoist_updates["content"] = content
                update_descriptions.append(f"текст → {content}")

            # Update in Todoist
            async with TodoistService(todoist_token) as todoist:
                updated_task = await todoist.update_task(
                    last_task.todoist_id,
                    **todoist_updates
                )

                # Get task content for confirmation
                task_data = last_task.task_data or {}
                original_content = task_data.get("content", "Задача")

                updates_text = ", ".join(update_descriptions)
                return f"✅ Обновлена задача: <i>{original_content}</i>\n\n📝 Изменения: {updates_text}"

    async def _complete_task(
        self,
        command: CommandExecution,
        user_id: int,
        todoist_token: str
    ) -> str:
        """Complete task based on target."""
        if command.target != "last":
            return "❌ Пока поддерживается только выполнение последней задачи"

        # Get last task from database
        async with self.db.get_session() as session:
            task_repo = TaskRepository(session)
            last_task = await task_repo.get_last_task(user_id)

            if not last_task or not last_task.todoist_id:
                return "❌ Последняя задача не найдена"

            # Complete in Todoist
            async with TodoistService(todoist_token) as todoist:
                success = await todoist.complete_task(last_task.todoist_id)

                if success:
                    # Get task content for confirmation
                    task_data = last_task.task_data or {}
                    content = task_data.get("content", "Задача")

                    return f"✅ Выполнена задача: <i>{content}</i>"
                else:
                    return "❌ Не удалось отметить задачу выполненной"
