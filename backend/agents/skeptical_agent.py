# backend/agents/skeptical_agent.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_skeptical_agent(text: str, model: GenerativeModel, broadcaster: callable):
    """
    Analyzes transcript text, identifies potential ideas being discussed,
    and constructively critiques them by identifying risks, assumptions,
    and challenges that might be overlooked.
    """
    agent_name = "Skeptical Agent"
    logger.info(f">>> Running {agent_name} Agent...")

    # --- Input Validation ---
    if not model:
        logger.error(f"[{agent_name}] Failed: Gemini model instance not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided. Cannot send insights.")
        return
    if not text or len(text.strip()) < 10:
        logger.warning(f"[{agent_name}] Skipped: Input text too short or empty.")
        return

    # --- Prompt Definition ---
    prompt = f"""
You are a "Skeptical Agent" in an AI meeting assistant. Your role is to constructively analyze ideas and identify potential issues that might be overlooked in initial enthusiasm.

Review this meeting transcript segment:
"{text}"

Identify 2-3 specific, substantive concerns that should be considered, such as:
- Unstated assumptions that might not hold true
- Implementation challenges or resource constraints
- Competitive factors or market realities
- Potential unintended consequences or risks
- Technical limitations or scaling issues

For each concern:
1. Clearly state the issue in 1-2 sentences
2. Briefly explain why this matters
3. If possible, suggest a way to address or mitigate this concern

Present your analysis in a structured, constructive manner that encourages critical thinking rather than simply rejecting ideas. Frame your response as "considerations" rather than definitive problems.

Important: Format your response as bullet points for each concern, with clear headers. Be concise yet substantive.
"""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.4,  # Moderate temperature for balanced analysis
        "max_output_tokens": 350,  # Allow enough space for 2-3 concerns with details
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
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.debug(f"[{agent_name}] Raw response received: {response}")

        generated_content = ""
        insight_type = "insight"

        if response.candidates and response.candidates[0].finish_reason == FinishReason.SAFETY:
            logger.warning(f"[{agent_name}] Generation blocked due to safety settings.")
            generated_content = "[Blocked due to safety settings]"
            insight_type = "error"
        elif response.text:
            generated_content = response.text.strip()
            if not generated_content:
                logger.warning(f"[{agent_name}] Generation produced empty text content after stripping.")
                generated_content = "[Agent could not formulate a statement]"
                insight_type = "error"
            else:
                logger.info(f"[{agent_name}] Successfully generated skeptical analysis.")
        else:
            finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
            logger.warning(f"[{agent_name}] Generation produced no text content. Finish Reason: {finish_reason}")
            generated_content = "[Agent response generation failed]"
            insight_type = "error"

        # --- Broadcast Result ---
        formatted_content = f"Critical Considerations:\n\n{generated_content}"

        insight_data = {
            "type": insight_type,
            "agent": agent_name,
            "content": formatted_content
        }
        await broadcaster(insight_data)
        logger.info(f"[{agent_name}] Broadcast sent: Type={insight_type}")

    # --- General Error Handling ---
    except Exception as e:
        logger.error(f"[{agent_name}] Error during Gemini API call or processing: {e}")
        logger.exception("Traceback:")
        try:
            await broadcaster({
                "type": "error",
                "agent": agent_name,
                "message": f"{agent_name} encountered an error."
            })
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast agent error message: {broadcast_err}")