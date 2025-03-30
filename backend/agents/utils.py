# backend/agents/utils.py
import logging
import json
import re

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

# Standardized prompt format used across agents
STANDARDIZED_PROMPT_FORMAT = """
I need you to generate {specific_content} based on the provided transcript.

FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:

🚀 [HEADLINE - Make it punchy, interesting, with an emoji at the start]

[SUMMARY - 1-2 sentence summary of your key insight]

Detailed Analysis:
{analysis}

REQUIREMENTS:
1. YOUR HEADLINE MUST START WITH AN EMOJI followed by a space
2. Write like a brilliant, excited entrepreneur sharing their vision - not like a corporate marketer
3. Provide specific, valuable insights that go beyond what's directly stated in the transcript
4. Your insight should be truly ORIGINAL and CREATIVE, not just rephrasing what was said
5. Focus on opportunities, unexpected connections, and forward-thinking ideas
6. Use authentic, enthusiastic language that avoids corporate jargon
"""

async def format_agent_response(agent_name, content, broadcaster, message_type="insight"):
    """
    Format and broadcast agent responses consistently across agents.
    
    Args:
        agent_name: Name of the agent
        content: The response content
        broadcaster: Function to broadcast the response
        message_type: Type of message (insight, error, etc.)
    """
    try:
        # Clean up content if needed
        clean_content = content.strip()
        
        # Check if the response seems like an error or non-insight
        if (
            "sorry" in clean_content.lower() or
            "i apologize" in clean_content.lower() or
            "not enough context" in clean_content.lower() or
            "insufficient context" in clean_content.lower() or
            "doesn't provide enough" in clean_content.lower() or
            "limited information" in clean_content.lower()
        ):
            logger.warning(f"[{agent_name}] Response appears to be an apology or error. Not sending.")
            return

        # For non-error responses
        if message_type == "insight":
            logger.info(f"[{agent_name}] Broadcasting insight: {clean_content[:100]}...")
            message = {
                "type": "insight",
                "agent": agent_name,
                "content": clean_content
            }
        # Handle explicit errors
        elif message_type == "error":
            logger.info(f"[{agent_name}] Broadcasting error: {clean_content[:100]}...")
            message = {
                "type": "error",
                "agent": agent_name,
                "message": clean_content
            }
        # Default case
        else:
            logger.info(f"[{agent_name}] Broadcasting message of type {message_type}")
            message = {
                "type": message_type,
                "agent": agent_name,
                "content": clean_content
            }
            
        # Broadcast the message
        await broadcaster(message)
        
    except Exception as e:
        logger.error(f"Error formatting/broadcasting {agent_name} response: {e}")
        logger.exception("Traceback:")