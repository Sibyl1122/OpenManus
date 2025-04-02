import asyncio
import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.agent.utils import contains


async def example():
    """
    Example demonstrating how to use the contains function.
    """
    # Example 1: Checking for exact substring match
    content_a = "OpenManus is a framework for building AI agents and tools."
    content_b = "AI agents"

    result = await contains(content_a, content_b)
    print(f"Example 1:")
    print(f"  Content A: {content_a}")
    print(f"  Content B: {content_b}")
    print(f"  Result: {result}")  # Should be True
    print()

    # Example 2: Checking for semantic/conceptual matching
    content_a = "The latest advancements in natural language processing have enabled more sophisticated conversational interfaces."
    content_b = "AI language models have improved conversation capabilities"

    result = await contains(content_a, content_b)
    print(f"Example 2:")
    print(f"  Content A: {content_a}")
    print(f"  Content B: {content_b}")
    print(f"  Result: {result}")  # Result depends on LLM's understanding of semantic similarity
    print()

    # Example 3: No match
    content_a = "Python is a programming language known for its readability and simplicity."
    content_b = "Java is an object-oriented programming language."

    result = await contains(content_a, content_b)
    print(f"Example 3:")
    print(f"  Content A: {content_a}")
    print(f"  Content B: {content_b}")
    print(f"  Result: {result}")  # Should be False
    print()


if __name__ == "__main__":
    asyncio.run(example())
