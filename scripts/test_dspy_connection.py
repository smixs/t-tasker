"""Test DSPy connection and basic functionality."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import dspy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test OpenAI connection through DSPy."""
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment!")
        return
    
    print(f"API Key found: {api_key[:20]}...{api_key[-10:]}")
    
    # Try to configure DSPy
    print("\nConfiguring DSPy with OpenAI...")
    try:
        lm = dspy.LM(
            "openai/gpt-4o-mini",
            api_key=api_key,
            max_tokens=100
        )
        dspy.configure(lm=lm)
        print("✓ DSPy configured successfully")
    except Exception as e:
        print(f"✗ Failed to configure DSPy: {e}")
        return
    
    # Test simple generation
    print("\nTesting simple generation...")
    try:
        # Create a simple signature
        class SimpleTask(dspy.Signature):
            """Extract task from message."""
            message: str = dspy.InputField()
            task: str = dspy.OutputField(desc="short task description")
        
        # Create predictor
        predictor = dspy.Predict(SimpleTask)
        
        # Test it
        result = predictor(message="Встретиться с директором завтра в 15:00")
        print(f"✓ Generation successful!")
        print(f"  Input: Встретиться с директором завтра в 15:00")
        print(f"  Output: {result.task}")
        
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test our parser
    print("\nTesting our parser...")
    try:
        from src.services.dspy_parser import RealWorldTodoistParser
        
        parser = RealWorldTodoistParser()
        result = parser.forward(message="Позвонить в банк по поводу кредита")
        print(f"✓ Parser test successful!")
        print(f"  Result: {result}")
        
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_connection()