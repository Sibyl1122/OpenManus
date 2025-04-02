import asyncio
import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.agent.utils.equals import contains


async def test_contains():
    """
    Test the contains function with various examples.
    """
    test_cases = [
        {
            "content_a": "The quick brown fox jumps over the lazy dog.",
            "content_b": "brown fox",
            "expected": True,
            "description": "Simple substring match"
        },
        {
            "content_a": "The quick brown fox jumps over the lazy dog.",
            "content_b": "black cat",
            "expected": False,
            "description": "No match at all"
        },
        {
            "content_a": "Python is a high-level, general-purpose programming language.",
            "content_b": "programming language",
            "expected": True,
            "description": "Exact phrase match"
        },
        {
            "content_a": """
为了帮助您规划这次特别的旅程，我将首先为您制定一个详细的行程计划，然后生成一个简单的HTML旅行手册。在开始之前，我需要确认一些细节，以确保行程符合您的预算和兴趣。

1. **预算分配**：您希望如何分配这20000人民币的预算？例如，交通、住宿、餐饮、门票、活动等。
2. **交通方式**：您计划如何从北京到上海？是飞机还是火车？
3. **住宿选择**：您希望住在什么样的酒店或民宿？是否有特定的区域偏好？
4. **特别求婚地点**：您有特定的求婚地点想法吗？如果没有，我可以推荐一些适合求婚的地点。

            """,
            "content_b": "寻求用户输入",
            "expected": True,
            "description": "Overlapping concepts but not contained"
        },
        {
            "content_a": """
为了帮助您规划这次特别的旅程，我将首先为您制定一个详细的行程计划，然后生成一个简单的HTML旅行手册。在开始之前，我需要确认一些细节，以确保行程符合您的预算和兴趣。

1. **预算分配**：您希望如何分配这20000人民币的预算？例如，交通、住宿、餐饮、门票、活动等。
2. **交通方式**：您计划如何从北京到上海？是飞机还是火车？
3. **住宿选择**：您希望住在什么样的酒店或民宿？是否有特定的区域偏好？
4. **特别求婚地点**：您有特定的求婚地点想法吗？如果没有，我可以推荐一些适合求婚的地点。

请告诉我，以便我能够更准确地为您规划行程。
            """,
            "content_b": "寻求用户输入",
            "expected": True,
            "description": "Semantic matching (concepts present but not exact wording)"
        },
        {
            "content_a": """为了帮助您规划这次特别的旅程，我将首先为您制定一个详细的行程计划，然后生成一个简单的HTML旅行手册。在开始之前，我需要确认一些细节，以确保行程符合您的预算和兴趣。

1. **预算分配**：您希望如何分配这20000人民币的预算？例如，交通、住宿、餐饮、门票、活动等。
2. **交通方式**：您计划如何从北京到上海？是飞机还是火车？
3. **住宿选择**：您希望住在什么样的酒店或民宿？是否有特定的区域偏好？
4. **特别求婚地点**：您有特定的求婚地点想法吗？如果没有，我可以推荐一些适合求婚的地点。

请提供这些信息，以便我能够更准确地为您规划行程。""",
            "content_b": "寻求用户输入",
            "expected": True,
            "description": "Exact phrase match"
        }
    ]

    for idx, test_case in enumerate(test_cases):
        print(f"Running test case {idx+1}: {test_case['description']}")
        result = await contains(
            content_a=test_case["content_a"],
            content_b=test_case["content_b"]
        )

        print(f"  Content A: {test_case['content_a']}")
        print(f"  Content B: {test_case['content_b']}")
        print(f"  Expected: {test_case['expected']}, Got: {result}")
        print(f"  {'✅ PASS' if result == test_case['expected'] else '❌ FAIL'}")
        print()


if __name__ == "__main__":
    asyncio.run(test_contains())
