"""Tests for intent models."""

import pytest
from pydantic import ValidationError

from src.models.intent import TaskCreation, CommandExecution, Intent
from src.models.task import TaskSchema


class TestTaskCreation:
    """Test TaskCreation model."""

    def test_task_creation_valid(self):
        """Test creating valid TaskCreation instance."""
        task = TaskSchema(
            content="Buy milk tomorrow",
            due_string="tomorrow",
            priority=1
        )
        intent = TaskCreation(
            type="create_task",
            task=task
        )
        
        assert intent.type == "create_task"
        assert intent.task.content == "Buy milk tomorrow"
        assert intent.task.due_string == "tomorrow"

    def test_task_creation_invalid_type(self):
        """Test TaskCreation with invalid type."""
        task = TaskSchema(content="Test task")
        
        with pytest.raises(ValidationError):
            TaskCreation(
                type="invalid_type",  # Should be "create_task"
                task=task
            )

    def test_task_creation_missing_task(self):
        """Test TaskCreation without task field."""
        with pytest.raises(ValidationError):
            TaskCreation(type="create_task")


class TestCommandExecution:
    """Test CommandExecution model."""

    def test_view_tasks_command(self):
        """Test creating view_tasks command."""
        cmd = CommandExecution(
            type="command",
            command_type="view_tasks",
            target="today",
            filters={"priority": 3}
        )
        
        assert cmd.type == "command"
        assert cmd.command_type == "view_tasks"
        assert cmd.target == "today"
        assert cmd.filters == {"priority": 3}

    def test_delete_task_command(self):
        """Test creating delete_task command."""
        cmd = CommandExecution(
            type="command",
            command_type="delete_task",
            target="last"
        )
        
        assert cmd.type == "command"
        assert cmd.command_type == "delete_task"
        assert cmd.target == "last"
        assert cmd.filters is None
        assert cmd.updates is None

    def test_update_task_command(self):
        """Test creating update_task command."""
        cmd = CommandExecution(
            type="command",
            command_type="update_task",
            target="last",
            updates={
                "priority": 4,
                "due_string": "tomorrow",
                "labels": ["urgent", "work"]
            }
        )
        
        assert cmd.type == "command"
        assert cmd.command_type == "update_task"
        assert cmd.updates["priority"] == 4
        assert cmd.updates["due_string"] == "tomorrow"
        assert cmd.updates["labels"] == ["urgent", "work"]

    def test_complete_task_command(self):
        """Test creating complete_task command."""
        cmd = CommandExecution(
            type="command",
            command_type="complete_task",
            target="specific",
            task_identifier="12345"
        )
        
        assert cmd.type == "command"
        assert cmd.command_type == "complete_task"
        assert cmd.target == "specific"
        assert cmd.task_identifier == "12345"

    def test_default_target(self):
        """Test default target value."""
        cmd = CommandExecution(
            type="command",
            command_type="delete_task"
        )
        
        assert cmd.target == "last"  # Default value

    def test_invalid_command_type(self):
        """Test invalid command_type."""
        with pytest.raises(ValidationError):
            CommandExecution(
                type="command",
                command_type="invalid_command"
            )

    def test_invalid_target(self):
        """Test invalid target."""
        with pytest.raises(ValidationError):
            CommandExecution(
                type="command",
                command_type="view_tasks",
                target="invalid_target"
            )


class TestIntentUnion:
    """Test Intent Union type."""

    def test_intent_as_task_creation(self):
        """Test Intent can be TaskCreation."""
        task = TaskSchema(content="Test task")
        intent: Intent = TaskCreation(
            type="create_task",
            task=task
        )
        
        assert isinstance(intent, TaskCreation)
        assert intent.type == "create_task"

    def test_intent_as_command_execution(self):
        """Test Intent can be CommandExecution."""
        intent: Intent = CommandExecution(
            type="command",
            command_type="view_tasks",
            target="all"
        )
        
        assert isinstance(intent, CommandExecution)
        assert intent.type == "command"

    def test_intent_discrimination(self):
        """Test discriminating between intent types."""
        # Task creation intent
        task_intent: Intent = TaskCreation(
            type="create_task",
            task=TaskSchema(content="Buy groceries")
        )
        
        # Command execution intent
        cmd_intent: Intent = CommandExecution(
            type="command",
            command_type="delete_task"
        )
        
        # Check discrimination
        if isinstance(task_intent, TaskCreation):
            assert task_intent.task.content == "Buy groceries"
        
        if isinstance(cmd_intent, CommandExecution):
            assert cmd_intent.command_type == "delete_task"