"""
Utility functions for the AI Meeting Assistant.
Contains shared functions for formatting and standardizing agent outputs.
"""
import logging

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def format_agent_response(agent_name: str, content: str, broadcaster: callable, type: str = "insight"):
    """
    Standardized formatting for all agent responses.
    
    Args:
        agent_name: Name of the agent generating the response
        content: The raw content generated by the agent
        broadcaster: Function to broadcast the response
        type: Type of response (insight or error)
    """
    try:
        if type == "error":
            # For errors, log them but don't send a card to the frontend
            logger.warning(f"[{agent_name}] Error occurred: {content}")
            # Instead of sending an error card, send a special message type that the frontend can handle differently
            # The frontend should not display this as a card
            silent_error_data = {
                "type": "silent_error",  # This type should be ignored by the frontend card rendering
                "agent": agent_name,
                "message": content
            }
            await broadcaster(silent_error_data)
            logger.info(f"[{agent_name}] Silent error notification sent")
        else:
            # For insights, use standardized format
            insight_data = {
                "type": "insight",
                "agent": agent_name,
                "content": content
            }
            # Broadcast the formatted insight
            await broadcaster(insight_data)
            logger.info(f"[{agent_name}] Insight broadcast sent")
        
    except Exception as e:
        logger.error(f"[{agent_name}] Error broadcasting formatted response: {e}")
        logger.exception("Traceback:")
        try:
            # Try to report the error silently
            await broadcaster({
                "type": "silent_error",
                "agent": agent_name,
                "message": f"Error formatting response: {e}"
            })
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast error notification: {broadcast_err}")

# Example standardized prompts that all agents can use
STANDARDIZED_PROMPT_FORMAT = """
Based on the transcript segment, provide:

1. A mind-blowing headline that MUST:
   - Be a complete, grammatically correct sentence with a strong subject and powerful verb
   - Convey a REVOLUTIONARY concept that challenges conventional thinking
   - Sound like a breaking news announcement about a paradigm shift
   - Use sharp, vivid language that captures attention
   - Be 5-10 words maximum

2. A crisp summary that MUST:
   - Expand on the headline with ONE specific, concrete detail
   - Include a surprising statistic or bold claim about impact
   - Be 10-15 words maximum
   - End with a period

3. Detailed analysis that includes {specific_content}

EXAMPLES OF EXCELLENT HEADLINES AND SUMMARIES:

🚀 "AI Twins Replace Middle Management Entirely"
Companies deploying digital replicas report 300% productivity boost and happier employees.

🔮 "Drone Hives Transform Last-Mile Delivery Forever"
Self-organizing swarms deliver packages 10x faster while eliminating 95% of urban congestion.

⚡ "Neural Implants Revolutionize Knowledge Work Training"
Skills downloaded directly to brain stem cut onboarding from months to minutes.

**Format your response like this:**

[Your headline here - IMPORTANT: Make it REVOLUTIONARY and mind-expanding]

[Your summary here - IMPORTANT: Include a SURPRISING detail or statistic]

**Detailed Analysis:**
[Your detailed analysis here - IMPORTANT: Provide the full mind-blowing vision]

CRITICAL REQUIREMENTS:
- Your headline MUST feel like science fiction that's just barely possible
- Absolutely NO corporate jargon or buzzwords
- Be concrete, specific, and crystal clear
- Make sure your idea is truly revolutionary, not an incremental improvement
- Prioritize ideas that would shock traditional executives
"""