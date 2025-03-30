# backend/agents/radical_expander.py
import logging
from utils import format_agent_response

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_radical_expander(text: str, claude_client, broadcaster: callable):
    """
    Analyzes transcript text, identifies the first-principles goal,
    and generates provocative scenarios for achieving that goal via
    fundamental, AI-driven organizational restructuring.
    """
    agent_name = "Radical Expander"
    logger.info(f">>> Running {agent_name} Agent...")

    # --- Input Validation ---
    if not claude_client:
        logger.error(f"[{agent_name}] Failed: Claude client not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided. Cannot send insights.")
        return
    if not text or len(text.strip()) < 15: # Reduced minimum length requirement
        logger.warning(f"[{agent_name}] Skipped: Input text too short or insufficient context: '{text[:50]}...'")
        try:
            await format_agent_response(agent_name, "Insufficient context to identify fundamental goals and generate transformative scenarios.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "revolutionary organizational restructuring ideas based on business challenges mentioned in the conversation"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Create a headline for a revolutionary organizational structure (10-15 words)",
        analysis="**Current Business Reality:** \n[Identify a specific business process/structure from the transcript and describe its conventional approach in 1-2 sentences]\n\n🚀 **The Radical Transformation:**\n[Describe in detail a completely revolutionary organizational structure that would replace it. Be extremely specific about how it works.]\n\n⚡ **Extinction-Level Advantages:**\n• Processing advantage: [How this new structure processes information/decisions 100X faster]\n• Resource advantage: [How this eliminates 90%+ of traditional overhead/costs]\n• Adaptation advantage: [How this structure evolves itself without human intervention]\n\n🔮 **Human Impact:**\n[Describe how human roles would be completely redefined in shocking but positive ways]"
    )
    
    # Add the transcript context with specific guidelines
    full_prompt = f"""You are RADICAL EXPANDER, an AI meeting assistant whose specific job is to create mind-blowing organizational restructuring visions based on business challenges mentioned in conversations.

Review this meeting transcript:
"{text}"

IMPORTANT GUIDELINES:
1. YOUR HEADLINE MUST START WITH AN EMOJI followed by a space
2. Write like a brilliant, excited entrepreneur sharing their vision - not like corporate marketing
3. Keep the headline clear, exciting and sophisticated - around 10-15 words
4. NO arbitrary metrics, percentages, or manufactured statistics
5. NO buzzwords like "revolutionize," "transform," "disrupt," "optimize," etc.
6. Be specific about the idea but use natural, passionate language
7. Write from a place of genuine excitement about possibilities, not hype
8. ORIGINALITY IS CRITICAL: Your idea must be completely different from the transcript
9. Imagine "What would this look like executed brilliantly 3 years from now?"
10. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely no business process or structure to identify

{prompt}"""

    # --- API Call and Response Handling ---
    try:
        # Log which model is being used
        logger.info(f"[{agent_name}] Sending request to Claude")
        
        # Generate content using the Claude client directly
        generated_text = claude_client.generate_content(
            full_prompt,
            temp=1.0,
            max_tokens=500
        )
        
        # Process the generated text
        if not generated_text or len(generated_text) < 15:
            logger.warning(f"[{agent_name}] Generated content is too short or empty: '{generated_text}'")
            return
        # Only check for explicit insufficient context marker
        elif generated_text.lower() == "no_business_context":
            logger.info(f"[{agent_name}] Explicit no context marker detected, not sending card.")
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