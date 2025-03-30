# backend/agents/disruptor_agent.py
import logging
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_disruptor_agent(text: str, claude_client, broadcaster: callable):
    """
    Analyzes transcript text and envisions how an AI-first startup 
    could completely redefine the industry being discussed and 
    outcompete established players.
    """
    agent_name = "Disruptor"
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
            await format_agent_response(agent_name, "Insufficient context to identify industry and generate disruption scenarios.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "a radical AI-first business model that will completely obliterate and replace the existing industry"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        analysis="🔥 **Industry Ripe for Disruption:** Identify the specific industry from the transcript\n\n💣 **The Extinction-Level Concept:** Explain how this AI-powered business model makes current approaches obsolete\n\n⚡ **Unfair Advantages:**\n• Technical superpower: The AI capability that makes this unstoppable\n• Economic revolution: How the business model creates 10X better economics\n• Blitzscaling strategy: How this captures 90% market share in under 2 years\n\n☠️ **Incumbent Death Spiral:** Why traditional players will collapse within 24 months"
    )
    
    # Add the transcript to the prompt with stronger context relevance requirements
    full_prompt = f"""You are DISRUPTOR, an AI meeting assistant whose specific job is to generate revolutionary AI business ideas based on industries mentioned in conversations.

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
8. Each section should build on your central idea with specific details
9. ORIGINALITY IS CRITICAL: Your idea must be completely different from the transcript
10. Imagine "What would this look like executed brilliantly 3 years from now?"
11. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely no business context

{prompt}"""

    # --- API Call and Response Handling ---
    try:
        # Log which model is being used
        logger.info(f"[{agent_name}] Sending request to Claude")
        
        # Generate content using the Claude client directly
        generated_text = claude_client.generate_content(
            full_prompt,
            temp=0.9,
            max_tokens=600
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
            logger.info(f"[{agent_name}] Successfully generated disruptor concept.")
            await format_agent_response(agent_name, generated_text, broadcaster, "insight")

    except Exception as e:
        logger.error(f"[{agent_name}] Error during Claude API call or processing: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return