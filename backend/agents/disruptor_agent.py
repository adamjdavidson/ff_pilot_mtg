# backend/agents/disruptor_agent.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_disruptor_agent(text: str, model: GenerativeModel, broadcaster: callable):
    """
    Analyzes transcript text and envisions how an AI-first startup 
    could completely redefine the industry being discussed and 
    outcompete established players.
    """
    agent_name = "Disruptor"
    logger.info(f">>> Running {agent_name} Agent...")

    # --- Input Validation ---
    if not model:
        logger.error(f"[{agent_name}] Failed: Gemini model instance not provided.")
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
    
    # COMPLETELY OVERRIDE THE STANDARDIZED PROMPT - going directly to what we want
    direct_prompt = f"""You are DISRUPTOR, generating revolutionary AI business ideas.

TRANSCRIPT:
"{text}"

RESPOND EXACTLY IN THIS FORMAT - DO NOT DEVIATE:

Neural Implants Revolutionize Corporate Training Forever

Brain interfaces reduce onboarding from months to minutes, boosting productivity 500%.

🔥 **Industry Targeted:** [Identify specific industry from transcript]

💣 **The Extinction-Level Concept:**
[Explain a revolutionary AI business model that completely replaces current approaches. Be extremely specific and technical.]

⚡ **Unfair Advantages:**
• Technical superpower: [The specific AI capability that makes this unstoppable]
• Economic revolution: [How this creates 10X better economics]
• Blitzscaling strategy: [How this captures 90% market share in under 2 years]

☠️ **Incumbent Death Spiral:**
[Explain why traditional players will collapse within 24 months - be specific about their vulnerabilities]

REQUIREMENTS:
1. Your headline MUST be a complete sentence with a strong subject and powerful verb
2. Your summary MUST include a specific number/statistic (100X, 500%, etc.)
3. Your idea must be technically feasible with near-future tech (5-10 years)
4. Your disruption must completely replace an entire industry, not just improve it
5. NEVER use buzzwords like "revolutionize, transform, optimize" in your actual final answer
6. Each advantage must be shockingly specific, not generic platitudes
7. The death spiral must describe EXACTLY why incumbents cannot adapt
8. ORIGINALITY IS CRITICAL: Your idea must be COMPLETELY DIFFERENT from anything mentioned in the transcript - not just extending concepts from the transcript
9. Use clear, direct, engaging language throughout - NO corporate jargon, buzzwords, or fluffy marketing language
10. Every sentence must be grammatically perfect, clear, and direct - write like a top science journalist
11. ALL claims must be supported with specific details - no vague assertions

Format your output EXACTLY as shown in the example. Include emoji headers.

If you truly can't find ANY business context, respond ONLY with "NO_BUSINESS_CONTEXT"."""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.9,  # Higher temperature for more creative outputs
        "max_output_tokens": 600,  # Increased to avoid truncation
        "top_p": 0.9,        # More diverse outputs
    }

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

    # --- API Call and Response Handling ---
    try:
        logger.info(f"[{agent_name}] Sending request to Gemini model...")
        response = await model.generate_content_async(
            direct_prompt,  # USE THE DIRECT PROMPT INSTEAD OF STANDARDIZED ONE
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.debug(f"[{agent_name}] Raw response received: {response}")

        if response.candidates and response.candidates[0].finish_reason == FinishReason.SAFETY:
            logger.warning(f"[{agent_name}] Generation blocked due to safety settings.")
            # Don't send error card
            return
        elif response.text:
            generated_text = response.text.strip()
            if not generated_text:
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
        else:
            finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
            logger.warning(f"[{agent_name}] Generation produced no text content. Finish Reason: {finish_reason}")
            # Don't send error card
            return

    except Exception as e:
        logger.error(f"[{agent_name}] Error during Gemini API call or processing: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return