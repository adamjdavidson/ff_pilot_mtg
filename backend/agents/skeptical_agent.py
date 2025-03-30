# backend/agents/skeptical_agent.py
import logging
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_skeptical_agent(text: str, claude_client, broadcaster: callable):
    """
    Analyzes transcript text, identifies potential ideas being discussed,
    and constructively critiques them by identifying risks, assumptions,
    and challenges that might be overlooked.
    """
    agent_name = "Skeptical Agent"
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
            await format_agent_response(agent_name, "Insufficient context to identify meaningful concerns or challenges.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "key concerns or risks that might be overlooked, including unstated assumptions, implementation challenges, and potential unintended consequences"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Create a headline identifying the key risk or challenge",
        summary="Briefly summarize the main concern that should be addressed",
        analysis="Identify 2-3 specific concerns with the following structure:\n\n**Concern 1: Title**\n- Issue: Clearly state the issue\n- Why it matters: Brief explanation\n- Mitigation: Suggestion to address\n\n**Concern 2: Title**\n- Issue: Clearly state the issue\n- Why it matters: Brief explanation\n- Mitigation: Suggestion to address\n\n**Concern 3: Title** (optional)\n- Issue: Clearly state the issue\n- Why it matters: Brief explanation\n- Mitigation: Suggestion to address"
    )
    
    # Add the transcript to the prompt with stronger context relevance requirements
    full_prompt = f"""You are a "Skeptical Agent" in an AI meeting assistant for BUSINESS meetings. Your role is to constructively analyze business ideas and identify potential issues that might be overlooked in initial enthusiasm.

Review this meeting transcript segment:
"{text}"

IMPORTANT CONTEXT INSTRUCTIONS:
1. Be CREATIVE in finding business angles in the transcript, even if they're only implied.
2. Focus on practical concerns that might be relevant to any business context you can identify.
3. Try to make connections to business themes even when they aren't explicitly mentioned.
4. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely no way to extract any business-relevant insight.

{prompt}

Present your analysis in a structured, constructive manner that encourages critical thinking rather than simply rejecting ideas. Frame issues as "considerations" rather than definitive problems."""

    # --- API Call and Response Handling ---
    try:
        # Log which model is being used
        logger.info(f"[{agent_name}] Sending request to Claude")
        
        # Generate content using the Claude client directly
        generated_text = claude_client.generate_content(
            full_prompt,
            temp=0.4,
            max_tokens=350
        )
        
        # Process the generated text
        if not generated_text or len(generated_text.strip()) < 5:
            logger.warning(f"[{agent_name}] Generation produced empty text content after stripping.")
            # No need to broadcast error
            return
        # Only check for explicit insufficient context marker
        elif generated_text.lower() == "no_business_context":
            logger.info(f"[{agent_name}] Explicit no context marker detected, not sending card.")
            # Don't send any response card when explicitly marked as no context
            return
        else:
            logger.info(f"[{agent_name}] Successfully generated skeptical analysis.")
            await format_agent_response(agent_name, generated_text, broadcaster, "insight")

    except Exception as e:
        logger.error(f"[{agent_name}] Error during Claude API call or processing: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return