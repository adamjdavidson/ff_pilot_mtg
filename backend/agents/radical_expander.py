# backend/agents/radical_expander.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_radical_expander(text: str, model: GenerativeModel, broadcaster: callable):
    """
    Analyzes transcript text, identifies the first-principles goal,
    and generates provocative scenarios for achieving that goal via
    fundamental, AI-driven organizational restructuring.
    """
    agent_name = "Radical Expander"
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
            await format_agent_response(agent_name, "Insufficient context to identify fundamental goals and generate transformative scenarios.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "provocative scenarios for achieving the fundamental goal through completely reimagined organizational structures that would be unrecognizable to today's executives"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        analysis="🌋 **Current Business Reality:** Briefly describe the conventional approach\n\n🚀 **The Radical Transformation:** Explain the revolutionary organizational structure that would replace it\n\n⚡ **Extinction-Level Advantages:** Describe why this new structure would make traditional organizations extinct\n\n🔮 **Human Impact:** How human roles would be redefined in ways currently unimaginable"
    )
    
    # COMPLETELY OVERRIDE THE STANDARDIZED PROMPT - going directly to what we want
    direct_prompt = f"""You are RADICAL EXPANDER, creating mind-blowing organizational restructuring visions.

TRANSCRIPT:
"{text}"

RESPOND EXACTLY IN THIS FORMAT - DO NOT DEVIATE:

Organic Intelligence Hives Replace Corporate Hierarchy 

Neural-linked decision networks cut management overhead by 94% while quadrupling innovation rate.

🌋 **Current Business Reality:** 
[Identify a specific business process/structure from the transcript and describe its conventional approach in 1-2 sentences]

🚀 **The Radical Transformation:**
[Describe in detail a completely revolutionary organizational structure that would replace it. Be extremely specific about how it works.]

⚡ **Extinction-Level Advantages:**
• Processing advantage: [How this new structure processes information/decisions 100X faster]
• Resource advantage: [How this eliminates 90%+ of traditional overhead/costs]
• Adaptation advantage: [How this structure evolves itself without human intervention]

🔮 **Human Impact:**
[Describe how human roles would be completely redefined in shocking but positive ways]

REQUIREMENTS:
1. Your headline MUST be a complete sentence with a mind-blowing organizational concept
2. Your summary MUST include a specific number/statistic (90%, 8X, etc.)
3. Idea must be technically feasible in 10-15 years but feel like science fiction
4. Must COMPLETELY REIMAGINE organizational structure, not just improve current approach
5. Must eliminate entire management layers or traditional business functions 
6. Each advantage must be concrete and quantifiable, not vague
7. ORIGINALITY IS CRITICAL: Your idea must be COMPLETELY DIFFERENT from anything mentioned in the transcript - not just extending concepts from the transcript
8. Use clear, direct, engaging language throughout - NO corporate jargon, buzzwords, or fluffy marketing language
9. Every sentence must be grammatically perfect, clear, and direct - write like a top science journalist
10. ALL claims must be supported with specific details - no vague assertions

Format your output EXACTLY as shown in the example. Include emoji headers.

If you truly can't find ANY hint of a business process or structure, respond ONLY with "NO_BUSINESS_CONTEXT"."""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 1.0, # Maximum temperature for truly radical responses
        "max_output_tokens": 500, # Increased token limit for more detailed scenarios
        "top_p": 0.95, # Higher sampling for more creative outputs
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
            if not generated_text or len(generated_text) < 15:
                logger.warning(f"[{agent_name}] Generated content is too short or empty: '{generated_text}'")
                # Don't send error card
                return
            # Only check for explicit insufficient context marker
            elif generated_text.lower() == "no_business_context":
                logger.info(f"[{agent_name}] Explicit no context marker detected, not sending card.")
                # Don't send any response card when explicitly marked as no context
                return
            else:
                logger.info(f"[{agent_name}] Successfully generated insight.")
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
