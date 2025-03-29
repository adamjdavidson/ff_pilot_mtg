# backend/agents/debate_agent.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_debate_agent(recent_context: str, model: GenerativeModel, broadcaster: callable):
    """
    Analyzes recent transcript context upon explicit user invocation
    to identify and articulate potential underlying conflicts or
    divergences politely, prompting further discussion.
    """
    agent_name = "Debate Agent"
    logger.info(f">>> Running {agent_name} Agent...")

    # --- Input Validation ---
    if not model:
        logger.error(f"[{agent_name}] Failed: Gemini model instance not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided. Cannot send insights.")
        return
    if not recent_context or len(recent_context.strip()) < 25: # Reduced minimum length requirement
        logger.warning(f"[{agent_name}] Skipped: Provided context was too short: '{recent_context[:50]}...'")
        try:
            await format_agent_response(agent_name, "Insufficient context to identify meaningful divergent perspectives or tensions.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "potential divergent viewpoints or misalignments that should be discussed to ensure team alignment"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Create a headline highlighting the key tension or divergent perspectives",
        summary="Summarize the key difference in viewpoints or assumptions in 1-2 sentences",
        analysis="Explain the potential disagreement or misalignment in more detail, why it matters, and suggest how the team might address it constructively"
    )
    
    # Add the transcript context with stronger context relevance requirements
    full_prompt = f"""You are an AI meeting facilitator for BUSINESS meetings, helping to constructively surface potential underlying disagreements or misalignments. Your tone must be objective, polite, and aimed at fostering productive business discussion.

Review the following transcript context carefully:
--- BEGIN CONTEXT ---
{recent_context}
--- END CONTEXT ---

IMPORTANT CONTEXT INSTRUCTIONS:
1. Look for ANY potential disagreements or different perspectives in the transcript.
2. Consider how these differences might relate to business or professional contexts.
3. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there are absolutely no differing viewpoints present.
4. Be creative in identifying potential tensions that might impact business discussions.

Identify the MOST significant area where business perspectives seem contradictory, professional assumptions might be misaligned, or a potential business-related conflict appears to be glossed over.

{prompt}"""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.5,
        "max_output_tokens": 300,
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
                logger.info(f"[{agent_name}] Successfully generated debate prompt statement.")
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