# backend/agents/debate_agent.py (Corrected insight_type)
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models

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
    if not recent_context or len(recent_context.strip()) < 20:
        logger.warning(f"[{agent_name}] Skipped: Provided context was too short or empty.")
        try:
            await broadcaster({
                "type": "error",
                "agent": agent_name,
                "message": f"{agent_name} received insufficient context."
            })
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # --- Prompt Definition (Explicit Trigger Version) ---
    prompt = f"""
You are an AI meeting facilitator, invoked to help constructively surface potential underlying disagreements or misalignments based on the recent discussion. Your tone should be objective, polite, and aimed at fostering productive discussion, not assigning blame.

You have been explicitly asked to analyze the following recent transcript context:
--- BEGIN CONTEXT ---
{recent_context}
--- END CONTEXT ---

Review this context carefully to identify the MOST significant area within this text where:
- Different stated perspectives seem contradictory or significantly divergent.
- Underlying assumptions might be misaligned.
- A potential conflict or important difference in viewpoint appears to be glossed over or avoided.

Now, formulate a concise response (typically 2-3 sentences) intended for the meeting participants that achieves the following:

1.  **Introduction:** Gently introduce your observation (e.g., "It might be useful to explore a potential difference in perspective here...", "I noticed two interesting viewpoints that might diverge...", "To ensure alignment, perhaps we can clarify...").
2.  **Articulate Tension:** Clearly and neutrally state the core tension or the differing viewpoints you observed based *specifically* on the provided context. Quote or paraphrase concisely if helpful.
3.  **Optional Implication:** If appropriate and obvious from the context, *briefly* mention why clarifying this might be important (e.g., "...as it could affect strategy.", "...to ensure we're aligned on customer impact.").
4.  **Prompt Discussion:** Politely encourage the participants to discuss the point (e.g., "Perhaps we could spend a moment clarifying this?", "What are the team's thoughts on navigating this difference?", "Is this a tension worth exploring further?").

Focus on articulating the single most important tension you find in the provided text. Avoid generic statements. Deliver ONLY the facilitator statement you want the participants to hear.
"""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.5, # Moderate temperature for analysis and formulation
        "max_output_tokens": 150, # Enough for a concise 2-3 sentence output
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
        insight_type = "insight" # CHANGED to "insight"

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
                logger.info(f"[{agent_name}] Successfully generated debate prompt statement.")

        else:
            finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
            logger.warning(f"[{agent_name}] Generation produced no text content. Finish Reason: {finish_reason}")
            generated_content = "[Agent response generation failed]"
            insight_type = "error"

        # --- Broadcast Result ---
        formatted_content = f"Debate Agent Suggestion:\n\n{generated_content}"  # Simple title + text

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
        # Attempt to broadcast a generic error message
        try:
            await broadcaster({
                "type": "error",
                "agent": agent_name,
                "message": f"{agent_name} encountered an error."
            })
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast agent error message: {broadcast_err}")