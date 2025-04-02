from typing import Optional, Union

from app.llm import LLM
from app.schema import Message


async def contains(
    content_a: str,
    content_b: str,
    llm_config_name: str = "default",
    temperature: float = 0.0
) -> bool:
    """
    Checks if content_a contains content_b using an LLM.

    Args:
        content_a: The primary content that might contain the other content.
        content_b: The content to check for within content_a.
        llm_config_name: The LLM configuration name to use.
        temperature: Temperature setting for the LLM request (lower value for more deterministic results).

    Returns:
        bool: True if content_a contains content_b, False otherwise.
    """
    # Initialize LLM with specified configuration
    llm = LLM(config_name=llm_config_name)

    # Create system message with clear instructions
    system_message = Message.system_message(
        "You are a specialized helper that determines if content A contains content B. "
        "Respond ONLY with 'true' if content A contains content B (even partially), "
        "or 'false' if it does not. Do not provide any other response text."
    )

    # Create user message with the contents to compare
    user_message = Message.user_message(
        f"Content A:\n\n{content_a}\n\n"
        f"Content B:\n\n{content_b}\n\n"
        "Is content B (completely or partially) contained within content A? Respond with ONLY 'true' or 'false'."
    )

    # Make the request to the LLM
    response = await llm.ask(
        messages=[user_message],
        system_msgs=[system_message],
        stream=False,
        temperature=temperature
    )

    # Process the response (normalize and check for 'true')
    normalized_response = response.strip().lower()

    # Return True if the response contains 'true', False otherwise
    return normalized_response == 'true'
