# backend/agents/fact_checker.py
import logging
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_fact_checker(transcript_text: str, claude_client, broadcaster: callable):
    """
    Analyzes transcript text to identify the main factual topic being discussed.
    Does NOT perform actual fact-checking/search, just topic identification.
    """
    agent_name = "Fact Checker"
    logger.info(f">>> Running {agent_name} Agent...")
    logger.info(f"{agent_name}: Grounding tool/search functionality is currently disabled.")

    # --- Input Validation ---
    if not claude_client:
        logger.error(f"[{agent_name}] Failed: Claude client not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided.")
        return
    if not transcript_text or len(transcript_text.strip()) < 15: # Reduced minimum length requirement
        logger.warning(f"[{agent_name}] Skipped: Input text too short or insufficient context: '{transcript_text[:50]}...'")
        try:
            await format_agent_response(agent_name, "Insufficient context to identify factual topics.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "the main factual topic or question being discussed in the business conversation"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Create a headline identifying the key factual topic",
        analysis="Briefly identify the main factual topic without any detailed analysis as fact-checking functionality is currently disabled."
    )
    
    # Add the transcript context
    full_prompt = f"""You are the FACT CHECKER in an AI meeting assistant. Your purpose is to identify the main factual topics or questions being discussed in business conversations.

Review this meeting transcript:
"{transcript_text}"

IMPORTANT CONTEXT INSTRUCTIONS:
1. Only identify the factual topic being discussed - DO NOT perform any fact checking
2. Keep your response very brief and focused
3. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely no factual topic to identify

{prompt}"""

    # --- API Call and Response Handling ---
    try:
        # Log which model is being used
        logger.info(f"[{agent_name}] Sending request to Claude")
        
        # Generate content using the Claude client directly
        generated_text = claude_client.generate_content(
            full_prompt,
            temp=0.7,
            max_tokens=100
        )
        
        # Process the generated text
        if not generated_text or len(generated_text.strip()) < 5:
            logger.warning(f"[{agent_name}] Generation produced empty text content after stripping.")
            # Don't send error card
            return
        # Only check for explicit insufficient context marker
        elif generated_text.lower() == "no_business_context":
            logger.info(f"[{agent_name}] Explicit no context marker detected, not sending card.")
            # Don't send any response card when explicitly marked as no context
            return
        else:
            logger.info(f"[{agent_name}] Successfully identified factual topic.")
            await format_agent_response(agent_name, generated_text, broadcaster, "insight")

    except Exception as e:
        logger.error(f"[{agent_name}] Error during Claude API call or processing: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return
