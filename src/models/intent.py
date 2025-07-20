"""Intent models for classifying user messages."""

from typing import Literal, Union
from pydantic import BaseModel, Field

from src.models.task import TaskSchema


class TaskCreation(BaseModel):
    """Intent to create a new task."""

    type: Literal["create_task"] = Field(..., description="Discriminator field for task creation intent")
    task: TaskSchema = Field(..., description="Parsed task information to be created")


class CommandExecution(BaseModel):
    """Intent to execute a command on existing tasks."""

    type: Literal["command"] = Field(..., description="Discriminator field for command execution intent")
    command_type: Literal["view_tasks", "delete_task", "update_task", "complete_task"] = Field(
        ..., description="Type of command to execute"
    )
    target: Literal["last", "all", "today", "tomorrow", "specific"] = Field(
        default="last", description="Target for the command (e.g., last task, all tasks, today's tasks)"
    )
    filters: dict[str, str | int | list[str]] | None = Field(
        None, description="Filters for viewing tasks (e.g., priority, project, labels)"
    )
    updates: dict[str, str | int | list[str]] | None = Field(
        None, description="Updates to apply to tasks (e.g., priority, due_date, content)"
    )
    task_identifier: str | None = Field(None, description="Specific task identifier if target='specific'")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"type": "command", "command_type": "view_tasks", "target": "today", "filters": {"priority": 3}},
                {"type": "command", "command_type": "delete_task", "target": "last"},
                {
                    "type": "command",
                    "command_type": "update_task",
                    "target": "last",
                    "updates": {"priority": 4, "due_string": "tomorrow"},
                },
                {"type": "command", "command_type": "complete_task", "target": "last"},
            ]
        }
    }


class IntentWrapper(BaseModel):
    """Wrapper for intent classification result."""

    intent_type: Literal["create_task", "command"] = Field(
        ..., description="Type of intent - either create_task or command"
    )
    task_data: TaskSchema | None = Field(None, description="Task data if intent_type is create_task")
    command_type: Literal["view_tasks", "delete_task", "update_task", "complete_task"] | None = Field(
        None, description="Type of command if intent_type is command"
    )
    target: Literal["last", "all", "today", "tomorrow", "specific"] | None = Field(
        None, description="Target for the command"
    )
    filters: dict[str, str | int | list[str]] | None = Field(None, description="Filters for viewing tasks")
    updates: dict[str, str | int | list[str]] | None = Field(None, description="Updates to apply to tasks")
    task_identifier: str | None = Field(None, description="Specific task identifier if target='specific'")

    def to_intent(self) -> Union[TaskCreation, CommandExecution]:
        """Convert wrapper to appropriate intent type."""
        if self.intent_type == "create_task":
            if not self.task_data:
                raise ValueError("task_data is required for create_task intent")
            return TaskCreation(type="create_task", task=self.task_data)
        else:
            if not self.command_type:
                raise ValueError("command_type is required for command intent")
            return CommandExecution(
                type="command",
                command_type=self.command_type,
                target=self.target or "last",
                filters=self.filters,
                updates=self.updates,
                task_identifier=self.task_identifier,
            )


# Union type for all possible intents
Intent = Union[TaskCreation, CommandExecution]
