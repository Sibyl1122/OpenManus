from app.tool.base import BaseTool
from app.schema import Message


_REQUEST_USER_INPUT_DESCRIPTION = """Request additional information from the user when needed.
This tool will block execution until the user provides the requested input,
which will then be added to the conversation as a user message.
"""


class RequestUserInput(BaseTool):
    name: str = "request_user_input"
    description: str = _REQUEST_USER_INPUT_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The question or prompt to show to the user when requesting input.",
            },
            "reason": {
                "type": "string",
                "description": "The reason why additional input is needed from the user.",
            }
        },
        "required": ["prompt", "reason"],
    }

    async def execute(self, prompt: str, reason: str) -> Message:
        """
        Request input from the user using the built-in input() function and
        return it as a Message.user_message.

        Args:
            prompt: The question or prompt to show to the user.
            reason: The reason why additional input is needed.

        Returns:
            A Message object with the user's input in the role of 'user'.
        """
        # Display the reason and prompt to the user
        print(f"\nReason for requesting input: {reason}")
        # Use the input() function to block and wait for user input
        user_response = input(f"{prompt}: ")

        return user_response
