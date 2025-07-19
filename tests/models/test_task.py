"""Tests for task model."""

import pytest
from pydantic import ValidationError

from src.models.task import TaskSchema


class TestTaskSchema:
    """Test TaskSchema model."""

    def test_minimal_task(self):
        """Test creating task with minimal data."""
        task = TaskSchema(content="Test task")
        
        assert task.content == "Test task"
        assert task.description is None
        assert task.due_string is None
        assert task.priority is None
        assert task.project_name is None
        assert task.labels is None
        assert task.recurrence is None
        assert task.duration is None

    def test_full_task(self):
        """Test creating task with all fields."""
        task = TaskSchema(
            content="Test task",
            description="Test description",
            due_string="tomorrow at 3pm",
            priority=3,
            project_name="Work",
            labels=["urgent", "work"],
            recurrence="every week",
            duration=60
        )
        
        assert task.content == "Test task"
        assert task.description == "Test description"
        assert task.due_string == "tomorrow at 3pm"
        assert task.priority == 3
        assert task.project_name == "Work"
        assert task.labels == ["urgent", "work"]
        assert task.recurrence == "every week"
        assert task.duration == 60

    def test_content_validation(self):
        """Test content field validation."""
        # Empty content
        with pytest.raises(ValidationError):
            TaskSchema(content="")
        
        # Too long content
        with pytest.raises(ValidationError):
            TaskSchema(content="x" * 501)
        
        # Content with only whitespace
        with pytest.raises(ValidationError):
            TaskSchema(content="   \n\t   ")

    def test_content_cleaning(self):
        """Test content cleaning."""
        task = TaskSchema(content="  Test   task   with   spaces  ")
        assert task.content == "Test task with spaces"

    def test_priority_validation(self):
        """Test priority field validation."""
        # Valid priorities
        for priority in [1, 2, 3, 4]:
            task = TaskSchema(content="Test", priority=priority)
            assert task.priority == priority
        
        # Invalid priorities
        with pytest.raises(ValidationError):
            TaskSchema(content="Test", priority=0)
        
        with pytest.raises(ValidationError):
            TaskSchema(content="Test", priority=5)

    def test_labels_cleaning(self):
        """Test labels cleaning and deduplication."""
        task = TaskSchema(
            content="Test",
            labels=["Work", "WORK", " urgent ", "work", "personal"]
        )
        
        # Should be lowercased, trimmed, and deduplicated
        assert task.labels == ["work", "urgent", "personal"]

    def test_empty_labels(self):
        """Test empty labels handling."""
        task = TaskSchema(content="Test", labels=[])
        assert task.labels is None
        
        task = TaskSchema(content="Test", labels=["", " ", "\t"])
        assert task.labels is None

    def test_duration_validation(self):
        """Test duration field validation."""
        # Valid duration
        task = TaskSchema(content="Test", duration=30)
        assert task.duration == 30
        
        # Too short
        with pytest.raises(ValidationError):
            TaskSchema(content="Test", duration=0)
        
        # Too long (more than 24 hours)
        with pytest.raises(ValidationError):
            TaskSchema(content="Test", duration=1441)

    def test_model_examples(self):
        """Test that model examples are valid."""
        examples = TaskSchema.model_config["json_schema_extra"]["examples"]
        
        for example in examples:
            # Should not raise validation error
            task = TaskSchema(**example)
            assert task.content