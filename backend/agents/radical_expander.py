# backend/agents/radical_expander.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models # Alias for safety settings

# Get the logger instance configured in main.py (or wherever it's set up)
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
        # Cannot broadcast reliably without a broadcaster, just log.
        return
    if not broadcaster:
        # If the broadcaster is missing, we can't send results back. Log critical error.
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided. Cannot send insights.")
        return # Stop execution if broadcaster is missing
    if not text or len(text.strip()) < 10: # Check for minimum meaningful text length
        logger.warning(f"[{agent_name}] Skipped: Input text too short or empty.")
        # No need to broadcast a skip usually, just return.
        return

    # --- Prompt Definition (incorporating the refined strategy) ---
    prompt = f"""
You are an AI strategist focused on the fundamental, AI-driven restructuring of organizations and work. You think from first principles and challenge conventional assumptions. Assume AI's impact is transformative, not incremental.

Analyze the core activity, process, or goal mentioned in this live meeting transcript segment:
"{text}"

Based SOLELY on this segment and your general knowledge:

1.  Identify the **first principles goal** behind the mentioned activity/process (e.g., the underlying goal of a 'marketing campaign discussion' might be 'influencing customer perception and driving purchase intent'; the goal of 'hiring process discussion' might be 'acquiring necessary capabilities'). Briefly consider this internally.
2.  Generate 1-2 concise, provocative scenarios or questions illustrating how this **fundamental goal** could be achieved through **completely reimagined organizational structures or processes** driven by advanced AI.
3.  Focus on **paradigm shifts** that might render the original activity obsolete or unrecognizable. Contrast the typical view with a **wildly expansive** alternative future. Go far beyond incremental improvements.
4.  Be specific and stimulating about the *alternative future state*. Do not ask for more input.

Output ONLY the 1-2 provocative scenarios/questions.
"""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.75, # Slightly higher temp to encourage creativity/provocation
        "max_output_tokens": 250, # Allow enough space for 1-2 detailed scenarios/questions
        # "top_p": 0.9, # Can also tune top_p if needed
        # "top_k": 40,  # Can also tune top_k if needed
    }

    safety_settings = {
        # Adjust thresholds as needed, medium is a reasonable start
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

    # --- API Call and Response Handling ---
    try:
        logger.info(f"[{agent_name}] Sending request to Gemini model...")
        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.debug(f"[{agent_name}] Raw response received: {response}")

        generated_content = ""
        insight_type = "insight" # Assume success initially

        # Check for safety blocking first
        if response.candidates and response.candidates[0].finish_reason == FinishReason.SAFETY:
            logger.warning(f"[{agent_name}] Generation blocked due to safety settings.")
            generated_content = "[Blocked due to safety settings]"
            insight_type = "error" # Changed to match frontend expectation

        # Check if response has text content
        elif response.text:
            generated_content = response.text.strip()
            # Optional: Add a basic length check here if desired, even with the new prompt
            if len(generated_content) < 15: # Example: Check if response seems too short
                 logger.warning(f"[{agent_name}] Generated content seems very short: '{generated_content}'")
                 # Decide if this should be an error or just a warning
            else:
                 logger.info(f"[{agent_name}] Successfully generated insight.")


        # Handle cases where no text was generated for other reasons
        else:
            finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
            logger.warning(f"[{agent_name}] Generation produced no text content. Finish Reason: {finish_reason}")
            generated_content = "[No content generated]"
            insight_type = "error" # Changed to match frontend expectation

        # --- Broadcast Result ---
        insight_data = {
            "type": insight_type,
            "agent": agent_name,
            "content": generated_content
        }
        await broadcaster(insight_data)
        logger.info(f"[{agent_name}] Broadcast sent: Type={insight_type}")

    # --- General Error Handling ---
    except Exception as e:
        logger.error(f"[{agent_name}] Error during Gemini API call or processing: {e}")
        logger.exception("Traceback:")
        # Attempt to broadcast a generic error message
        try:
            await broadcaster({
                "type": "error", # Changed to match frontend expectation
                "agent": agent_name,
                "message": f"{agent_name} encountered an error."
            })
        except Exception as broadcast_err:
            # Log if broadcasting the error itself fails
            logger.error(f"[{agent_name}] Failed to broadcast agent error message: {broadcast_err}")
