"""Intent models for classifying user messages."""

from typing import Literal, Union
from pydantic import BaseModel, Field

from src.models.task import TaskSchema


class TaskCreation(BaseModel):
    """Intent to create a new task."""
    
    type: Literal["create_task"] = Field(
        ...,
        description="Discriminator field for task creation intent"
    )
    task: TaskSchema = Field(
        ...,
        description="Parsed task information to be created"
    )


class CommandExecution(BaseModel):
    """Intent to execute a command on existing tasks."""
    
    type: Literal["command"] = Field(
        ...,
        description="Discriminator field for command execution intent"
    )
    command_type: Literal[
        "view_tasks",
        "delete_task", 
        "update_task",
        "complete_task"
    ] = Field(
        ...,
        description="Type of command to execute"
    )
    target: Literal["last", "all", "today", "tomorrow", "specific"] = Field(
        default="last",
        description="Target for the command (e.g., last task, all tasks, today's tasks)"
    )
    filters: dict[str, str | int | list[str]] | None = Field(
        None,
        description="Filters for viewing tasks (e.g., priority, project, labels)"
    )
    updates: dict[str, str | int | list[str]] | None = Field(
        None,
        description="Updates to apply to tasks (e.g., priority, due_date, content)"
    )
    task_identifier: str | None = Field(
        None,
        description="Specific task identifier if target='specific'"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "command",
                    "command_type": "view_tasks",
                    "target": "today",
                    "filters": {"priority": 3}
                },
                {
                    "type": "command", 
                    "command_type": "delete_task",
                    "target": "last"
                },
                {
                    "type": "command",
                    "command_type": "update_task",
                    "target": "last",
                    "updates": {"priority": 4, "due_string": "tomorrow"}
                },
                {
                    "type": "command",
                    "command_type": "complete_task",
                    "target": "last"
                }
            ]
        }
    }


# Union type for all possible intents
Intent = Union[TaskCreation, CommandExecution]