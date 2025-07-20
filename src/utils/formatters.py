"""Message formatters for Telegram responses."""

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.models.db import Task
from src.models.task import TaskSchema


def task_to_telegram_html(task: TaskSchema, todoist_task: dict[str, Any] | None = None) -> str:
    """Format task for Telegram HTML response.

    Args:
        task: Parsed task schema
        todoist_task: Created task response from Todoist API

    Returns:
        Formatted HTML message
    """
    lines = ["✅ <b>Задача создана!</b>\n"]

    # Task content
    lines.append(f"📝 <b>{escape_html(task.content)}</b>")

    # Description
    if task.description:
        lines.append(f"📄 {escape_html(task.description)}")

    # Project
    if task.project_name:
        lines.append(f"📁 Проект: <i>{escape_html(task.project_name)}</i>")

    # Due date
    if task.due_string:
        lines.append(f"📅 Срок: {escape_html(task.due_string)}")

    # Priority
    if task.priority and task.priority > 1:
        priority_emoji = get_priority_emoji(task.priority)
        lines.append(f"{priority_emoji} Приоритет: {task.priority}")

    # Labels
    if task.labels:
        labels_str = ", ".join(f"#{escape_html(label)}" for label in task.labels)
        lines.append(f"🏷 Метки: {labels_str}")

    # Recurrence
    if task.recurrence:
        lines.append(f"🔄 Повтор: {escape_html(task.recurrence)}")

    # Duration
    if task.duration:
        hours = task.duration // 60
        minutes = task.duration % 60
        if hours:
            duration_str = f"{hours}ч {minutes}м" if minutes else f"{hours}ч"
        else:
            duration_str = f"{minutes}м"
        lines.append(f"⏱ Длительность: {duration_str}")

    # Add Todoist link if available
    if todoist_task and "url" in todoist_task:
        lines.append(f"\n🔗 <a href='{todoist_task['url']}'>Открыть в Todoist</a>")

    return "\n".join(lines)


def format_error_message(error: Exception) -> str:
    """Format error message for user.

    Args:
        error: Exception object

    Returns:
        User-friendly error message
    """
    # Check if it's one of our custom exceptions with user_message
    if hasattr(error, "user_message"):
        return f"❌ {error.user_message}"

    # Generic error
    return "❌ Произошла ошибка при обработке вашего запроса. Попробуйте еще раз."


def format_task_preview(task: TaskSchema) -> str:
    """Format task preview for confirmation.

    Args:
        task: Parsed task schema

    Returns:
        Formatted preview message
    """
    lines = ["🔍 <b>Распознанная задача:</b>\n"]

    lines.append(f"<b>{escape_html(task.content)}</b>")

    if task.description:
        lines.append(f"<i>{escape_html(task.description)}</i>")

    details = []
    if task.project_name:
        details.append(f"📁 {task.project_name}")
    if task.due_string:
        details.append(f"📅 {task.due_string}")
    if task.priority and task.priority > 1:
        details.append(f"{get_priority_emoji(task.priority)} P{task.priority}")

    if details:
        lines.append("\n" + " • ".join(details))

    return "\n".join(lines)


def format_processing_message() -> str:
    """Get processing message."""
    return "⏳ Обрабатываю ваше сообщение..."


def format_quota_status(used: int, limit: int) -> str:
    """Format quota status message.

    Args:
        used: Number of requests used
        limit: Request limit

    Returns:
        Formatted quota message
    """
    percentage = (used / limit) * 100
    bar_length = 10
    filled = int(bar_length * percentage / 100)
    bar = "█" * filled + "░" * (bar_length - filled)

    lines = [
        "<b>📊 Статус квоты Todoist</b>\n",
        f"{bar} {percentage:.0f}%",
        f"Использовано: {used} / {limit} запросов",
        f"Осталось: {limit - used} запросов",
    ]

    if percentage > 80:
        lines.append("\n⚠️ <i>Приближаетесь к лимиту!</i>")

    return "\n".join(lines)


def escape_html(text: str) -> str:
    """Escape HTML special characters.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def get_priority_emoji(priority: int) -> str:
    """Get emoji for priority level.

    Args:
        priority: Priority level (1-4)

    Returns:
        Priority emoji
    """
    emojis = {
        1: "⚪",  # Low
        2: "🔵",  # Normal
        3: "🟡",  # High
        4: "🔴",  # Urgent
    }
    return emojis.get(priority, "⚪")


def create_task_keyboard(task_id: int, todoist_id: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for task management.

    Args:
        task_id: Database task ID
        todoist_id: Todoist task ID

    Returns:
        Inline keyboard markup
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Изменить",
                callback_data=f"edit_task:{task_id}:{todoist_id}"
            ),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_recent_tasks_keyboard(tasks: list[Task]) -> InlineKeyboardMarkup:
    """Create inline keyboard for recent tasks list.

    Args:
        tasks: List of task objects

    Returns:
        Inline keyboard markup
    """
    buttons = []

    for task in tasks:
        # Create row with task content and action buttons
        row = [
            InlineKeyboardButton(
                text=f"❌ {task.task_content[:20]}..." if len(task.task_content) > 20 else f"❌ {task.task_content}",
                callback_data=f"delete_task:{task.id}:{task.todoist_id}"
            ),
            InlineKeyboardButton(
                text="✅",
                callback_data=f"complete_task:{task.id}:{task.todoist_id}"
            ),
        ]
        buttons.append(row)

    # Add refresh button
    buttons.append([
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data="refresh_recent_tasks"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
