"""Test DSPy parser in detail."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import dspy
from dotenv import load_dotenv
from src.services.dspy_parser import RealWorldTodoistParser, RealTaskExtraction, StandardTagGenerator

# Load environment variables
load_dotenv()

def test_parser_steps():
    """Test each step of the parser."""
    
    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key, max_tokens=500)
    dspy.configure(lm=lm)
    
    message = "Позвонить в банк Сбербанк по поводу кредита для компании ООО Ромашка"
    
    print("=== Testing RealTaskExtraction ===")
    extractor = dspy.ChainOfThought(RealTaskExtraction)
    extraction = extractor(message=message, user_language="ru")
    
    print(f"Content: {extraction.content}")
    print(f"Description: {extraction.description}")
    print(f"Due string: {extraction.due_string}")
    print(f"Entities: {extraction.entities}")
    print(f"Action type: {extraction.action_type}")
    
    print("\n=== Testing StandardTagGenerator ===")
    tag_gen = dspy.Predict(StandardTagGenerator)
    tags = tag_gen(
        content=extraction.content,
        entities=extraction.entities,
        action_type=extraction.action_type
    )
    print(f"Generated tags: {tags.tags}")
    
    print("\n=== Testing Full Parser ===")
    parser = RealWorldTodoistParser()
    result = parser.forward(message)
    print(f"Final result: {result}")
    
    # Test with more complex message
    print("\n=== Testing Complex Message ===")
    complex_message = """Звонила Островской из IBT. Новости подтвердились. 
    Она в сентябре уходит и будет новый директор. Обещала поделиться контактами, 
    чтобы мы могли встретиться"""
    
    result2 = parser.forward(complex_message)
    print(f"Complex result: {result2}")


if __name__ == "__main__":
    test_parser_steps()