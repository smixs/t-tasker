"""Metrics for evaluating DSPy parser quality."""

import re
from typing import Any

import dspy


def _get_attr(obj, attr_name, default=None):
    """Get attribute from object or dict."""
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)
    elif isinstance(obj, dict) and attr_name in obj:
        return obj[attr_name]
    return default


def brevity_metric(example: dspy.Example, pred: Any, trace=None) -> float:
    """Check if extracted task essence is concise."""
    content = _get_attr(pred, 'content')
    if not content:
        return 0.0
    
    content_length = len(content)
    
    # Too long - bad
    if content_length > 100:
        return 0.0
    
    # Too short - also not great
    if content_length < 10:
        return 0.5
    
    # Good length
    return 1.0


def context_preservation_metric(example: dspy.Example, pred: Any, trace=None) -> float:
    """Check if important context is preserved."""
    description = _get_attr(pred, 'description')
    if not description:
        return 0.0
    
    content = _get_attr(pred, 'content', '')
    score = 1.0
    
    # Check if lists are preserved
    if "1." in example.message and "\n" in example.message:
        if "1." not in description:
            score *= 0.5
    
    # Check if key entities are mentioned
    if hasattr(example, 'entities'):
        mentioned_entities = 0
        for entity in example.entities:
            if entity in description or entity in content:
                mentioned_entities += 1
        
        if example.entities:
            entity_score = mentioned_entities / len(example.entities)
            score = score * 0.5 + entity_score * 0.5
    
    return max(0.0, score)


def date_accuracy_metric(example: dspy.Example, pred: Any, trace=None) -> float:
    """Check if date parsing is correct and timezone-free."""
    due_string = _get_attr(pred, 'due_string')
    
    if not due_string:
        return 1.0 if not hasattr(example, 'due_string') else 0.0
    
    # Check for timezone mentions that should be removed
    timezone_patterns = [
        "по Минску", "по Ташкенту", "по Москве", 
        "по ", "MSK", "UTC", "GMT"
    ]
    
    if due_string:
        for tz in timezone_patterns:
            if tz in due_string:
                return 0.0
    
    # If example has expected due_string, compare
    if hasattr(example, 'due_string') and example.due_string:
        if due_string == example.due_string:
            return 1.0
        # Partial credit for having a date when expected
        elif due_string:
            return 0.5
        else:
            return 0.0
    
    return 1.0


def tag_quality_metric(example: dspy.Example, pred: Any, trace=None) -> float:
    """Check tag quality and relevance."""
    pred_tags = _get_attr(pred, 'tags', _get_attr(pred, 'labels', []))
    
    if not pred_tags:
        return 0.0 if hasattr(example, 'tags') and example.tags else 1.0
    
    # No tags when expected
    if hasattr(example, 'tags') and example.tags and not pred_tags:
        return 0.0
    
    # Too many tags
    if len(pred_tags) > 5:
        return 0.7
    
    # Check tag relevance if we have expected tags
    if hasattr(example, 'tags') and example.tags:
        matches = sum(1 for tag in pred_tags if tag in example.tags)
        relevance = matches / len(example.tags) if example.tags else 0
        
        # Bonus for having reasonable number of tags
        count_score = 1.0 if 1 <= len(pred_tags) <= 5 else 0.5
        
        return relevance * 0.7 + count_score * 0.3
    
    # Just check if tags seem reasonable (1-5 tags)
    return 1.0 if 1 <= len(pred_tags) <= 5 else 0.5


def action_type_metric(example: dspy.Example, pred: Any, trace=None) -> float:
    """Check if action type is correctly identified."""
    action_type = _get_attr(pred, 'action_type')
    
    if not action_type:
        return 0.0 if hasattr(example, 'action_type') else 1.0
    
    if hasattr(example, 'action_type'):
        return 1.0 if action_type == example.action_type else 0.0
    
    # Check if action type is valid
    valid_types = ["встреча", "звонок", "документ", "решение", "проверка", "контакт", "работа"]
    return 1.0 if action_type in valid_types else 0.0


def entity_extraction_metric(example: dspy.Example, pred: Any, trace=None) -> float:
    """Check if entities are correctly extracted."""
    entities = _get_attr(pred, 'entities')
    
    if not entities:
        return 0.0 if hasattr(example, 'entities') and example.entities else 1.0
    
    if hasattr(example, 'entities') and example.entities:
        pred_entities = set(entities) if entities else set()
        expected_entities = set(example.entities)
        
        if not expected_entities:
            return 1.0
        
        # Calculate F1-like score
        if not pred_entities:
            return 0.0
        
        matches = pred_entities.intersection(expected_entities)
        precision = len(matches) / len(pred_entities) if pred_entities else 0
        recall = len(matches) / len(expected_entities) if expected_entities else 0
        
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * (precision * recall) / (precision + recall)
        return f1
    
    return 1.0


def combined_metric(example: dspy.Example, pred: Any, trace=None) -> float:
    """Combined metric with weights for different aspects."""
    weights = {
        'brevity': 0.15,
        'context': 0.20,
        'date': 0.25,
        'tags': 0.20,
        'action': 0.10,
        'entities': 0.10
    }
    
    scores = {
        'brevity': brevity_metric(example, pred, trace),
        'context': context_preservation_metric(example, pred, trace),
        'date': date_accuracy_metric(example, pred, trace),
        'tags': tag_quality_metric(example, pred, trace),
        'action': action_type_metric(example, pred, trace),
        'entities': entity_extraction_metric(example, pred, trace)
    }
    
    # Calculate weighted average
    total_score = sum(scores[metric] * weight for metric, weight in weights.items())
    
    # Log individual scores for debugging
    if trace:
        trace['metric_scores'] = scores
    
    return total_score