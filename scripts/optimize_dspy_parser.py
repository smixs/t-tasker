"""Optimize DSPy parser using MIPROv2."""

import os
import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import dspy
from dotenv import load_dotenv

from scripts.prepare_dspy_dataset import load_dataset
from src.services.dspy_metrics import combined_metric
from src.services.dspy_parser import RealWorldTodoistParser

# Load environment variables
load_dotenv()

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def optimize_parser():
    """Run MIPROv2 optimization on the parser."""
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment!")
        return
    
    logger.info(f"API Key found: {api_key[:10]}...{api_key[-5:]}")
    
    # Configure DSPy with models
    logger.info("Configuring teacher model (gpt-4o)...")
    teacher_model = dspy.LM(
        "openai/gpt-4o",
        api_key=api_key,
        max_tokens=1000
    )
    
    logger.info("Configuring prompt model (gpt-4o-mini)...")
    prompt_model = dspy.LM(
        "openai/gpt-4o-mini",
        api_key=api_key,
        max_tokens=500
    )
    
    # Set default LM for the parser
    logger.info("Setting default LM...")
    dspy.configure(lm=prompt_model)
    
    # Load training data
    print("Loading training dataset...")
    examples = load_dataset("data/dspy_training_data.json")
    print(f"Loaded {len(examples)} examples")
    
    # Split into train and dev sets
    split_idx = int(len(examples) * 0.8)
    trainset = examples[:split_idx]
    devset = examples[split_idx:]
    print(f"Train: {len(trainset)}, Dev: {len(devset)}")
    
    # Initialize parser
    parser = RealWorldTodoistParser()
    
    # Configure optimizer
    logger.info("\nConfiguring MIPROv2 optimizer...")
    
    # Enable verbose logging for DSPy
    import logging as dspy_logging
    dspy_logger = dspy_logging.getLogger("dspy")
    dspy_logger.setLevel(dspy_logging.INFO)
    
    # Add console handler to see logs
    console_handler = dspy_logging.StreamHandler()
    console_handler.setLevel(dspy_logging.INFO)
    dspy_logger.addHandler(console_handler)
    
    optimizer = dspy.MIPROv2(
        metric=combined_metric,
        auto="medium",  # Back to medium - 57 trials
        num_threads=8,  # Back to 8 threads
        teacher_settings=dict(lm=teacher_model),
        prompt_model=prompt_model,
        track_stats=True  # Enable statistics tracking
    )
    
    # Run optimization
    print("\nStarting optimization (this may take a while)...")
    try:
        optimized_parser = optimizer.compile(
            parser,
            trainset=trainset,
            max_bootstrapped_demos=4,
            max_labeled_demos=4,
            requires_permission_to_run=False,
            minibatch_size=25,
            minibatch_full_eval_steps=10
        )
        
        print("\nOptimization complete!")
        
        # Save optimized model
        model_path = "models/todoist_parser_v1.json"
        Path("models").mkdir(exist_ok=True)
        optimized_parser.save(model_path)
        print(f"Saved optimized model to {model_path}")
        
        # Evaluate on dev set
        print("\nEvaluating on dev set...")
        evaluate_parser(optimized_parser, devset)
        
        return optimized_parser
        
    except Exception as e:
        print(f"Optimization failed: {e}")
        raise


def evaluate_parser(parser, dataset):
    """Evaluate parser on a dataset."""
    total_score = 0
    metric_totals = {
        'brevity': 0,
        'context': 0,
        'date': 0,
        'tags': 0,
        'action': 0,
        'entities': 0
    }
    
    for i, example in enumerate(dataset):
        try:
            # Parse the message
            prediction = parser.parse_task(
                message=example.message,
                user_language="ru"
            )
            
            # Calculate metric
            trace = {}
            score = combined_metric(example, prediction, trace)
            total_score += score
            
            # Accumulate individual metrics
            if 'metric_scores' in trace:
                for metric, value in trace['metric_scores'].items():
                    metric_totals[metric] += value
            
            print(f"Example {i+1}: {score:.2f}")
            
        except Exception as e:
            print(f"Example {i+1}: Failed - {e}")
            total_score += 0
    
    # Print results
    avg_score = total_score / len(dataset)
    print(f"\nAverage score: {avg_score:.3f}")
    
    print("\nMetric breakdown:")
    for metric, total in metric_totals.items():
        avg = total / len(dataset)
        print(f"  {metric}: {avg:.3f}")


def test_optimized_parser():
    """Test the optimized parser with new examples."""
    # Load optimized parser
    parser = RealWorldTodoistParser()
    parser.load("models/todoist_parser_v1.json")
    
    # Configure DSPy
    dspy.configure(lm=dspy.LM(
        "openai/gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY")
    ))
    
    # Test examples
    test_messages = [
        """Позвонил Иванов из Альфа-банка. Хотят обсудить новую рекламную кампанию.
        Бюджет около 5 млн руб. Просил прислать предложение до пятницы.""",
        
        """Встреча отменилась. Перенесли на следующий вторник в 14:00 по Москве.
        Нужно предупредить всю команду и забронировать переговорку.""",
        
        """Получили ТЗ от клиента:
        1. Разработать дизайн landing page
        2. Интеграция с CRM
        3. A/B тестирование
        Дедлайн - конец месяца"""
    ]
    
    print("\nTesting optimized parser:\n")
    for i, message in enumerate(test_messages):
        print(f"Test {i+1}:")
        print(f"Message: {message[:100]}...")
        
        try:
            result = parser.parse_task(message, "ru")
            print(f"Task: {result.content}")
            print(f"Due: {result.due_string}")
            print(f"Tags: {result.labels}")
            print(f"Priority: {result.priority}")
            print()
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimize DSPy parser")
    parser.add_argument("--test", action="store_true", help="Test existing model")
    parser.add_argument("--threads", type=int, default=8, help="Number of threads")
    
    args = parser.parse_args()
    
    if args.test:
        test_optimized_parser()
    else:
        optimize_parser()