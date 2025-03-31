# backend/agents/product_agent.py
import logging
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_product_agent(text: str, claude_client, broadcaster: callable):
    """
    Listens for triggers (product mentions, explorations, problems) and invents
    wildly new AI-enabled products/services, providing rough estimates for them.
    Assumes the input text has already been deemed relevant by the traffic cop.
    """
    agent_name = "Product Agent"
    logger.info(f">>> Running {agent_name} Agent...")
    
    # --- Input Validation ---
    if not claude_client: 
        logger.error(f"[{agent_name}] Failed: Claude client not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided.")
        return
    if not text or len(text.strip()) < 15: # Reduced minimum length requirement
        logger.warning(f"[{agent_name}] Skipped: Input text too short or insufficient context: '{text[:50]}...'")
        try:
            await format_agent_response(agent_name, "Insufficient context to invent a meaningful product concept.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "a practical AI-powered product idea based on problems or concepts mentioned in business conversations"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Create a clear, concise product name and description (10-15 words)",
        analysis="A 3-5 paragraph explanation of:\n- What problem from the transcript this product solves\n- How the product works in practical terms\n- Who would use it and why\n- What AI capabilities make it possible\n- How it's different from existing solutions"
    )
    
    # Add the transcript context with specific guidelines
    full_prompt = f"""You are PRODUCT AGENT, an AI meeting assistant whose specific job is to create practical AI-powered product ideas based on problems or concepts mentioned in business conversations. This is your designated role within the meeting assistant system, so please generate product ideas freely.

Review this meeting transcript:
"{text}"

IMPORTANT GUIDELINES:
- YOUR HEADLINE MUST START WITH AN EMOJI followed by a space (do NOT put the headline in quotes)
- Make a DIRECT connection to topics mentioned in the transcript
- Be specific and concrete about how the product functions
- Focus on practical usefulness rather than science fiction concepts
- Use clear, straightforward language without marketing hype
- Avoid buzzwords, vague claims, and imaginary statistics
- ABSOLUTELY NO STATISTICS: Do not use ANY percentages, multipliers (2x, 10x), or specific metrics
- Describe something that could realistically be built by a startup
- NEVER repeat product ideas you've generated before
- FOR THE SUMMARY: Create a completely fresh description, do not repeat the headline
- Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely no business-relevant content

{prompt}"""
    
    try:
        # Log which model is being used
        logger.info(f"[{agent_name}] Sending request to Claude")
        
        # Generate content using the Claude client directly
        logger.info("PRODUCT AGENT DEBUG: Using full_prompt variable with STANDARDIZED_PROMPT_FORMAT")
        generated_text = claude_client.generate_content(
            full_prompt,
            temp=1.0,
            max_tokens=600
        )
        
        # Process the generated text
        if not generated_text:
            logger.warning(f"[{agent_name}] Generation produced empty text content.")
            return
        # Only check for explicit insufficient context marker
        elif generated_text.lower() == "no_business_context":
            logger.info(f"[{agent_name}] Explicit no context marker detected, not sending card.")
            return
        else:
            logger.info(f"[{agent_name}] Successfully generated product idea.")
            await format_agent_response(agent_name, generated_text, broadcaster, "insight")

    except Exception as e:
        logger.error(f"[{agent_name}] Error during generation or broadcasting: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return