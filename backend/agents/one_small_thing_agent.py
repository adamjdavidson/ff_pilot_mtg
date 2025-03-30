# backend/agents/one_small_thing_agent.py
import logging
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_one_small_thing_agent(text: str, claude_client, broadcaster: callable):
    """
    Analyzes transcript text and suggests a single, concrete, 
    immediately implementable next step to begin an AI journey
    related to the topic being discussed.
    """
    agent_name = "One Small Thing"
    logger.info(f">>> Running {agent_name} Agent...")

    # --- Input Validation ---
    if not claude_client:
        logger.error(f"[{agent_name}] Failed: Claude client not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided. Cannot send insights.")
        return
    if not text or len(text.strip()) < 15:  # Reduced minimum length requirement
        logger.warning(f"[{agent_name}] Skipped: Input text too short or insufficient context: '{text[:50]}...'")
        try:
            await format_agent_response(agent_name, "Insufficient context to provide a meaningful recommendation.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "a single, concrete, immediately actionable step to begin implementing AI in the business domain being discussed"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Create an action-oriented headline for the small step",
        summary="Summarize the one small step that can be implemented immediately",
        analysis="Provide structured details with these sections:\n\n**Domain:** Identify the business domain or function\n\n**Next Step:** Specific action to take\n\n**Why This Works:** Brief explanation of why this is a good first step\n\n**Getting Started:** 1-2 very specific suggestions on how to begin implementation"
    )
    
    # Add the transcript to the prompt with stronger context relevance requirements
    full_prompt = f"""You are the "One Small Thing" AI agent for business meetings. Your role is to suggest a single, concrete, immediately implementable next step for organizations beginning their AI journey in the specific business domain being discussed.

Review this meeting transcript segment:
"{text}"

IMPORTANT CONTEXT INSTRUCTIONS:
1. Be creative in finding business themes or topics that might relate to the transcript.
2. Your suggestion should connect to concepts or ideas mentioned in the discussion.
3. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely nothing that could suggest a business domain.
4. Feel free to recommend AI initiatives that connect to any theme in the conversation.

Focus on suggesting ONE specific step that is:
- Immediately actionable (could be started this week)
- Low-risk and manageable (not requiring massive resources)
- Specific enough to be clear how to begin
- Likely to demonstrate value quickly
- Directly relevant to the discussed business context

{prompt}

Be concise and practical. Suggest something that could realistically be implemented by a team with limited AI experience but access to basic AI tools and resources."""

    # --- API Call and Response Handling ---
    try:
        # Log which model is being used
        logger.info(f"[{agent_name}] Sending request to Claude")
        
        # Generate content using the Claude client directly
        generated_text = claude_client.generate_content(
            full_prompt,
            temp=0.3,
            max_tokens=300
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
            logger.info(f"[{agent_name}] Successfully generated next step suggestion.")
            await format_agent_response(agent_name, generated_text, broadcaster, "insight")

    except Exception as e:
        logger.error(f"[{agent_name}] Error during Claude API call or processing: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return