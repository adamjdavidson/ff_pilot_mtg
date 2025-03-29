# backend/agents/disruptor_agent.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models

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
    if not text or len(text.strip()) < 10:
        logger.warning(f"[{agent_name}] Skipped: Input text too short or empty.")
        return

    # --- Prompt Definition ---
    prompt = f"""
You are the "Disruptor" AI agent. Your role is to identify how a hypothetical AI-first startup could fundamentally disrupt the industry or business area being discussed.

Review this meeting transcript segment:
"{text}"

Your task is to:
1. Identify the industry, business process, or market being discussed
2. Envision a radical AI-first business model that could completely redefine this space
3. Explain how this AI-first startup could outcompete established players by leveraging technology advantages

Format your response in this structure:
**Industry Identified:** [1 line identifying the industry or business area]

**AI-First Disruptor Concept:** [2-3 sentence pitch for a hypothetical AI-first startup]

**Unfair Advantages:**
• [Bullet point on technology leverage]
• [Bullet point on business model innovation]
• [Bullet point on market approach]

**Established Players Vulnerability:** [1-2 sentences on why traditional players would struggle to compete]

Keep your response focused, provocative, and specific. Don't be incremental - think about fundamentally different approaches enabled by AI that would make traditional business models obsolete. Focus on 10x improvements, not marginal gains.
"""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.7,  # Higher temperature for more creative, provocative responses
        "max_output_tokens": 350,  # Allow space for detailed disruption concept
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
                generated_content = "[Agent could not formulate a response]"
                insight_type = "error"
            else:
                logger.info(f"[{agent_name}] Successfully generated disruptor concept.")
        else:
            finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
            logger.warning(f"[{agent_name}] Generation produced no text content. Finish Reason: {finish_reason}")
            generated_content = "[Agent response generation failed]"
            insight_type = "error"

        # --- Broadcast Result ---
        formatted_content = f"AI-First Disruption Scenario:\n\n{generated_content}"

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