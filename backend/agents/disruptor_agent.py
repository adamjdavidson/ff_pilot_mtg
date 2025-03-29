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
    specific_content = "a radical AI-first business model that could completely redefine the industry or business area being discussed"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Create a provocative headline for your AI-first disruptor concept",
        summary="Briefly summarize how an AI-first startup could disrupt this industry",
        analysis="Provide structured details with these sections:\n\n**Industry Identified:** Identify the industry or business area\n\n**AI-First Disruptor Concept:** 2-3 sentence pitch for a hypothetical AI-first startup\n\n**Unfair Advantages:**\n• Bullet point on technology leverage\n• Bullet point on business model innovation\n• Bullet point on market approach\n\n**Established Players Vulnerability:** Why traditional players would struggle to compete"
    )
    
    # Add the transcript to the prompt with stronger context relevance requirements
    full_prompt = f"""You are the "Disruptor" AI agent for business meetings. Your role is to identify how a hypothetical AI-first startup could fundamentally disrupt the specific industry or business area being discussed in the meeting.

Review this meeting transcript segment:
"{text}"

IMPORTANT CONTEXT INSTRUCTIONS:
1. Be creative in identifying industries or business areas that could relate to the transcript.
2. Your disruption scenario should connect to themes or concepts mentioned in the discussion.
3. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely nothing that could suggest an industry.
4. Feel free to identify potential business domains even when they're only implied in the conversation.

Your task is to identify the industry or business process being discussed, then envision a radical AI-first business model that could completely redefine this space and outcompete established players.

{prompt}

Be focused, provocative, and specific. Think about fundamentally different approaches enabled by AI that would make traditional business models obsolete. Focus on 10x improvements, not marginal gains."""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.5,  # Reduced temperature for more focus while maintaining creativity
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