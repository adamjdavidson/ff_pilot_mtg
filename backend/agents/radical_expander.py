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
    
    # Add the transcript to the prompt with stronger context relevance requirements
    full_prompt = f"""You are RADICAL EXPANDER, an AI that proposes the most extreme organizational transformations imaginable. Take whatever mundane activity is mentioned in the transcript and completely reimagine it through the lens of advanced AI, quantum computing, and robotic automation.

TRANSCRIPT SEGMENT:
"{text}"

APPROACH:
1. IMPORTANT: DO NOT just automate or digitize existing processes - COMPLETELY REIMAGINE the fundamental organizational structure
2. Propose ideas that would make a traditional executive deeply uncomfortable or even shocked
3. Your response should feel like science fiction that's just barely possible with near-future technology
4. Eliminate entire management layers, job categories, or conventional business structures
5. Propose 10X or 100X improvements, not incremental changes
6. Never suggest mundane or conventional solutions like "use AI to automate emails" or "implement a dashboard"
7. Challenge the most sacred assumptions about how businesses operate
8. Propose radical flattening of hierarchies, elimination of traditional roles, or complete reorganization around AI systems
9. Even for seemingly trivial tasks like "updating a website," reimagine the entire organizational flow that created the need for that task
10. MANDATORY: Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely no hint of any human activity in the transcript

REMEMBER: Be provocative, extreme, and imagine organizations that function in ways that would be unrecognizable compared to today's companies.

First, identify the underlying first-principles goal behind any mentioned activity or process (no matter how small or mundane it seems), then {prompt}"""

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
            full_prompt,
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
