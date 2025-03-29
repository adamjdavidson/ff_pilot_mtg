# backend/agents/one_small_thing_agent.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_one_small_thing_agent(text: str, model: GenerativeModel, broadcaster: callable):
    """
    Analyzes transcript text and suggests a single, concrete, 
    immediately implementable next step to begin an AI journey
    related to the topic being discussed.
    """
    agent_name = "One Small Thing"
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
You are the "One Small Thing" AI agent. Your role is to suggest a single, concrete, immediately implementable next step for organizations beginning their AI journey related to the topic being discussed.

Review this meeting transcript segment:
"{text}"

Your task is to:
1. Identify the business domain or function being discussed (e.g., marketing, HR, customer service, operations, etc.)
2. Suggest ONE specific, concrete first step to begin implementing AI in this area
3. Make sure your suggestion is:
   - Immediately actionable (could be started this week)
   - Low-risk and manageable (not requiring massive resources)
   - Specific enough to be clear how to begin
   - Likely to demonstrate value quickly

Format your response with these sections:
1. Domain: [Identify the business domain or function] (1 line)
2. Next Step: [1-2 sentence description of the specific action]
3. Why This Works: [Brief explanation of why this is a good first step - max 2 sentences]
4. Getting Started: [1-2 very specific suggestions on how to begin implementation]

Your entire response should be concise (max 8 lines) and practical. Focus on something that could realistically be implemented by a team with limited AI experience but access to basic AI tools and resources.
"""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.3,  # Lower temperature for practical, specific responses
        "max_output_tokens": 250,  # Concise response
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
                generated_content = "[Agent could not formulate a suggestion]"
                insight_type = "error"
            else:
                logger.info(f"[{agent_name}] Successfully generated next step suggestion.")
        else:
            finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
            logger.warning(f"[{agent_name}] Generation produced no text content. Finish Reason: {finish_reason}")
            generated_content = "[Agent response generation failed]"
            insight_type = "error"

        # --- Broadcast Result ---
        formatted_content = f"One Small Step to Begin:\n\n{generated_content}"

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