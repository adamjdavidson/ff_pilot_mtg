# backend/agents/product_agent.py
import logging
from utils import format_agent_response

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

    # Direct prompt with specific formatting requirements
    direct_prompt = f"""You are WILD PRODUCT AGENT, inventing mind-blowing, sci-fi level product ideas.

TRANSCRIPT:
"{text}"

RESPOND EXACTLY IN THIS FORMAT - DO NOT DEVIATE:

🔬 Our bio-inspired sensors create an invisible layer of building intelligence

🏙️ Physical spaces respond to inhabitants like living organisms, anticipating needs before they arise.

🚀 **The Revolutionary Product:**
[Describe a mind-blowing product concept that feels like science fiction but is technically feasible within 5-10 years. Be extremely specific about what it does and how it works.]

💰 **Billion-Dollar Potential:**
[Explain how this creates an entirely new market category worth $100B+. Include a specific number for market size.]

⚡ **Technical Moonshot:**
[Describe the precise breakthrough technology that makes this possible. Be specific about the technical innovation.]

🔮 **Future Impact:**
[Explain how this product fundamentally changes human behavior or society. Include a bold, specific prediction.]

REQUIREMENTS:
1. YOUR HEADLINE MUST START WITH AN EMOJI followed by a space
2. YOUR SUMMARY MUST ALSO START WITH AN EMOJI followed by a space
3. Write like a brilliant, excited entrepreneur sharing their vision - not like corporate marketing
4. Keep the headline clear, exciting and sophisticated - around 10-15 words
5. NO arbitrary metrics, percentages, or manufactured statistics
6. NO buzzwords like "revolutionize," "transform," "disrupt," "optimize," etc.
7. Be specific about the idea but use natural, passionate language
8. Write from a place of genuine excitement about possibilities, not hype
9. Each section should build on your central idea with specific details
10. ORIGINALITY IS CRITICAL: Your idea must be completely different from the transcript
11. Imagine "What would this look like executed brilliantly 3 years from now?"

Format your output EXACTLY as shown in the example. Include emoji headers.

If you truly can't find ANY hint of a domain or problem to solve, respond ONLY with "NO_BUSINESS_CONTEXT"."""
    
    try:
        # Log which model is being used
        logger.info(f"[{agent_name}] Sending request to Claude")
        
        # Generate content using the Claude client directly
        generated_text = claude_client.generate_content(
            direct_prompt,
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