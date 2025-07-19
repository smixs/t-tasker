"""Task schema for OpenAI parsing."""


from pydantic import BaseModel, Field, field_validator


class TaskSchema(BaseModel):
    """Schema for parsed task from user message."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Task content/title"
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Additional task description"
    )
    due_string: str | None = Field(
        None,
        description="Due date in natural language (e.g., 'tomorrow', 'next Monday')"
    )
    priority: int | None = Field(
        None,
        ge=1,
        le=4,
        description="Task priority: 1 (normal), 2 (medium), 3 (high), 4 (urgent)"
    )
    project_name: str | None = Field(
        None,
        max_length=100,
        description="Project name to add task to"
    )
    labels: list[str] | None = Field(
        None,
        max_length=10,
        description="Task labels"
    )
    recurrence: str | None = Field(
        None,
        description="Recurrence pattern (e.g., 'every day', 'every week')"
    )
    duration: int | None = Field(
        None,
        ge=1,
        le=1440,  # Max 24 hours
        description="Estimated duration in minutes"
    )

    @field_validator("content")
    @classmethod
    def clean_content(cls, v: str) -> str:
        """Clean and validate task content."""
        # Remove extra whitespace
        v = " ".join(v.split())

        # Ensure it's not empty after cleaning
        if not v:
            raise ValueError("Task content cannot be empty")

        return v

    @field_validator("labels")
    @classmethod
    def clean_labels(cls, v: list[str] | None) -> list[str] | None:
        """Clean and validate labels."""
        if not v:
            return None

        # Remove duplicates and clean
        cleaned = []
        for label in v:
            label = label.strip().lower()
            if label and label not in cleaned:
                cleaned.append(label)

        return cleaned if cleaned else None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int | None) -> int | None:
        """Validate priority value."""
        if v is None:
            return None

        # Map to Todoist priority (reversed)
        # User: 1 (normal) -> Todoist: 1
        # User: 2 (medium) -> Todoist: 2
        # User: 3 (high) -> Todoist: 3
        # User: 4 (urgent) -> Todoist: 4
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "Купить молоко",
                    "due_string": "завтра",
                    "priority": 1,
                    "labels": ["покупки"]
                },
                {
                    "content": "Встреча с клиентом",
                    "description": "Обсудить новый проект",
                    "due_string": "пятница в 15:00",
                    "priority": 3,
                    "project_name": "Работа",
                    "duration": 60
                },
                {
                    "content": "Оплатить счета",
                    "due_string": "каждый месяц 25 числа",
                    "recurrence": "every month on the 25th",
                    "priority": 2,
                    "labels": ["финансы", "регулярные"]
                }
            ]
        }
    }
