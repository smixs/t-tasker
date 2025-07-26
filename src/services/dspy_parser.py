"""DSPy-based parser for extracting tasks from real-world messages."""

import re
from typing import Literal

import dspy
from pydantic import BaseModel

from src.models.task import TaskSchema


class RealTaskExtraction(dspy.Signature):
    """Extract concise task from long contextual message."""
    
    message: str = dspy.InputField(desc="long message, possibly with context")
    user_language: str = dspy.InputField(desc="language: ru or en")
    
    # Core task - the most important thing
    content: str = dspy.OutputField(desc="CONCISE task essence, max 100 chars")
    
    # Full context preservation
    description: str = dspy.OutputField(desc="full context, preserve lists as-is")
    
    # Date if mentioned
    due_string: str = dspy.OutputField(desc="date if mentioned, WITHOUT timezone, empty string if no date")
    
    # Extracted entities for tagging
    entities: list[str] = dspy.OutputField(desc="people, companies, projects from text")
    action_type: str = dspy.OutputField(desc="action type: встреча/звонок/документ/решение/проверка")


class StandardTagGenerator(dspy.Signature):
    """Generate standardized tags based on context."""
    
    content: str = dspy.InputField(desc="task essence")
    entities: list[str] = dspy.InputField(desc="extracted entities")
    action_type: str = dspy.InputField(desc="action type")
    
    tags: list[str] = dspy.OutputField(desc="standardized tags, max 5")


class IntentClassification(dspy.Signature):
    """Determine user intent from message."""
    
    message: str = dspy.InputField(desc="user message")
    user_language: str = dspy.InputField(desc="user language")
    
    intent_type: Literal["create_task", "command"] = dspy.OutputField(
        desc="intent type: create_task or command"
    )
    command_type: str = dspy.OutputField(
        desc="command type if intent_type=command, empty string if not command"
    )
    target: str = dspy.OutputField(
        desc="command target (last/all/today/tomorrow), empty string if not command"
    )


class DateNormalization(dspy.Signature):
    """Convert date to Todoist API format."""
    
    raw_date: str = dspy.InputField(desc="date from message")
    user_language: str = dspy.InputField(desc="user language")
    
    normalized_date: str = dspy.OutputField(desc="date for Todoist API WITHOUT timezone")


# Standard tag mappings
STANDARD_TAGS = {
    # Action types
    "встреча": ["встреча", "митинг", "встретиться", "познакомиться"],
    "звонок": ["звонить", "позвонить", "созвон", "звонила"],
    "документы": ["документ", "драфт", "договор", "юрлицо"],
    "решение": ["решить", "определить", "принять решение"],
    "проверка": ["проверить", "статус", "обсудить"],
    
    # Priorities
    "срочно": ["дедлайн", "пятница", "понедельник", "завтра", "сегодня"],
    "важно": ["критично", "обязательно", "приоритет"],
}


def standardize_tags(raw_tags: list[str], entities: list[str]) -> list[str]:
    """Convert raw tags to standardized ones."""
    standard = set()
    
    # Keep important tags from generated list
    for tag in raw_tags:
        if len(tag) > 2:  # Skip too short tags
            tag_lower = tag.lower()
            
            # Check if it matches standard tags
            matched = False
            for std_tag, keywords in STANDARD_TAGS.items():
                if any(kw in tag_lower for kw in keywords):
                    standard.add(std_tag)
                    matched = True
                    break
            
            # Keep non-standard but important tags (like "кредит", "финансы")
            if not matched and tag not in entities:
                standard.add(tag)
    
    # Add companies/projects from entities (standardized)
    for entity in entities:
        if len(entity) > 2:  # Skip too short entities
            # Uppercase short names, keep others as-is
            standardized_entity = entity.upper() if len(entity) <= 5 else entity
            standard.add(standardized_entity)
    
    return list(standard)[:5]  # Max 5 tags


class RealWorldTodoistParser(dspy.Module):
    """DSPy module for parsing real-world messages into Todoist tasks."""
    
    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(RealTaskExtraction)
        self.generate_tags = dspy.Predict(StandardTagGenerator)
        self.normalize_date = dspy.Predict(DateNormalization)
        self.classify_intent_module = dspy.ChainOfThought(IntentClassification)
    
    def parse_task(self, message: str, user_language: str = "ru") -> TaskSchema:
        """Parse task from complex real-world message."""
        # Extract main information
        extraction = self.extract(message=message, user_language=user_language)
        
        # Normalize date if present
        due_string = None
        if extraction.due_string:
            date_result = self.normalize_date(
                raw_date=extraction.due_string,
                user_language=user_language
            )
            due_string = date_result.normalized_date
        
        # Generate standardized tags
        tag_result = self.generate_tags(
            content=extraction.content,
            entities=extraction.entities,
            action_type=extraction.action_type
        )
        
        # Standardize tags
        final_tags = standardize_tags(tag_result.tags, extraction.entities)
        
        # Determine priority based on urgency
        priority = 3 if "срочно" in final_tags else 2
        
        return TaskSchema(
            content=extraction.content[:100],  # Trim to 100 chars
            description=extraction.description if extraction.description else None,
            due_string=due_string,
            priority=priority,
            labels=final_tags if final_tags else None
        )
    
    def forward(self, message: str) -> dict:
        """Forward method required by DSPy for optimization."""
        # Extract main information
        extraction = self.extract(message=message, user_language="ru")
        
        # Generate standardized tags
        tag_result = self.generate_tags(
            content=extraction.content,
            entities=extraction.entities,
            action_type=extraction.action_type
        )
        
        return {
            "content": extraction.content[:100],
            "description": extraction.description,
            "due_string": extraction.due_string,
            "entities": extraction.entities,
            "action_type": extraction.action_type,
            "tags": standardize_tags(tag_result.tags, extraction.entities)
        }
    
    def classify_intent(self, message: str, user_language: str = "ru") -> dict:
        """Classify intent as task creation or command."""
        result = self.classify_intent_module(message=message, user_language=user_language)
        
        return {
            "intent_type": result.intent_type,
            "command_type": result.command_type,
            "target": result.target
        }


def is_complex_message(message: str) -> bool:
    """Determine if message is complex enough for DSPy parsing."""
    message_length = len(message)
    has_lists = bool(re.search(r'\d+\.', message))
    has_multiple_paragraphs = message.count('\n') > 2
    
    return message_length > 200 or has_lists or has_multiple_paragraphs