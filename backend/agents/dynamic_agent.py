# backend/agents/dynamic_agent.py
import logging
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_dynamic_agent(text: str, claude_client, broadcaster: callable, agent_config: dict):
    """
    A flexible agent that can be configured at runtime with custom goals and parameters.
    
    Args:
        text: The transcript text to analyze
        claude_client: The Claude client 
        broadcaster: Function to broadcast responses
        agent_config: Dictionary with agent configuration including name, goal, etc.
    """
    agent_name = agent_config.get("name", "Custom Agent")
    agent_goal = agent_config.get("goal", "Analyze the transcript and provide insights")
    
    logger.info(f">>> Running dynamic agent: {agent_name}")
    
    # --- Input Validation ---
    if not claude_client:
        logger.error(f"[{agent_name}] Failed: Claude client not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided. Cannot send insights.")
        return
    if not text or len(text.strip()) < 15:
        logger.warning(f"[{agent_name}] Skipped: Input text too short or insufficient context: '{text[:50]}...'")
        try:
            await format_agent_response(agent_name, f"Insufficient context to generate insights for {agent_name}.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return
    
    # Customize the standardized prompt for this specific agent
    specific_content = f"insights related to: {agent_goal}"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        analysis=f"Detailed analysis of how this relates to {agent_goal}. Provide specific, actionable insights."
    )
    
    # Get custom prompt template if provided or use default
    template = agent_config.get("prompt") or f"""You are {agent_name}, an AI agent that specializes in: {agent_goal}

TRANSCRIPT:
"{text}"

Your task is to analyze this transcript segment through the lens of your specialization.
Be creative in finding connections to your area of expertise, but be genuine and specific.
If there truly is no connection to your specialty, respond with "NO_RELEVANT_CONTEXT".

{prompt}

GUIDELINES:
1. Write like a brilliant, excited entrepreneur sharing their vision - not like corporate marketing
2. Keep your headline clear, exciting and sophisticated
3. NO arbitrary metrics, percentages, or manufactured statistics
4. NO buzzwords like "revolutionize," "transform," "disrupt," "optimize," etc.
5. Be specific about ideas but use natural, passionate language
6. Write from a place of genuine excitement about possibilities, not hype
7. ORIGINALITY IS CRITICAL: Your insights must go beyond what's directly stated in the transcript
8. If you find no connections to your specialty, just respond with "NO_RELEVANT_CONTEXT"
"""

    # Replace placeholders in template
    full_prompt = template.replace("{name}", agent_name)
    full_prompt = full_prompt.replace("{goal}", agent_goal)
    full_prompt = full_prompt.replace("{text}", text)
    
    # --- API Call and Response Handling ---
    try:
        # Log which model is being used
        logger.info(f"[{agent_name}] Sending request to Claude")
        
        # Generate content using the Claude client directly
        generated_text = claude_client.generate_content(
            full_prompt,
            temp=0.7,
            max_tokens=500
        )
        
        # Process the response text
        generated_text = generated_text.strip()
        if not generated_text:
            logger.warning(f"[{agent_name}] Generation produced empty text content after stripping.")
            # Don't send error card
            return
            
        # Check for explicit insufficient context marker
        elif generated_text.lower() == "no_relevant_context":
            logger.info(f"[{agent_name}] Explicit no context marker detected, not sending card.")
            # Don't send any response card when explicitly marked as no context
            return
            
        else:
            logger.info(f"[{agent_name}] Successfully generated insight.")
            await format_agent_response(agent_name, generated_text, broadcaster, "insight")
            
    except Exception as e:
        logger.error(f"[{agent_name}] Error during Claude API call or processing: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return