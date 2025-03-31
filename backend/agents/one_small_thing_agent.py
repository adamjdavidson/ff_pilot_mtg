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
    specific_content = "a single, tiny, concrete first step that can be completed in one day to make progress on a business challenge mentioned in the conversation"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Create an action-oriented headline for this small first step, starting with an emoji",
        summary="Describe this one small action that can be completed in under 24 hours",
        analysis="Provide these short sections:\n\n**The First Step:** One specific action that takes less than a day to complete\n\n**Why It Works:** Brief explanation of why this small step creates momentum\n\n**How To Start:** Exactly what to do in the next hour to begin"
    )
    
    # Add the transcript to the prompt with stronger context relevance requirements
    full_prompt = f"""You are the ONE SMALL THING AGENT in an AI meeting assistant. Your purpose is to suggest a single, tiny, concrete first step that can be completed in one day to make progress on business challenges mentioned in conversations.

Review this meeting transcript segment:
"{text}"

IMPORTANT CONSTRAINTS:
1. The step must be TRULY SMALL - completable in under 24 hours by one person
2. It must require MINIMAL RESOURCES - no budget approval needed
3. It must be SPECIFIC AND CONCRETE - not vague like "start researching" 
4. It must directly connect to the transcript content
5. Your headline MUST START WITH AN EMOJI (not a # or quotes)
6. Only suggest practical first actions, not entire projects or strategies
7. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely nothing that could suggest a business domain

EXAMPLES OF GOOD SMALL STEPS:
- "Create a 5-question survey about X and send it to 3 team members"
- "Schedule a 15-minute call with the sales team to understand their top data need"
- "Set up a free trial account for tool X and import a sample dataset"
- "Create a one-page document outlining the specific metrics for project X"
- "Find and share 3 examples of competitors using AI for X"

EXAMPLES OF BAD STEPS (TOO LARGE):
- "Implement an AI pricing strategy" (entire project, not one small step)
- "Create a machine learning model" (too complex for one day)
- "Redesign the customer experience" (too broad)
- "Analyze all customer data" (too vague and large)

{prompt}

Focus on providing that one tiny, concrete first step that creates momentum without overwhelming anyone."""

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