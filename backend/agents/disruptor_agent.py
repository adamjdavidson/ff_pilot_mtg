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
    specific_content = "a radical AI-first business model that could completely disrupt and redefine the industry being discussed"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="How This AI Startup Will Revolutionize [Industry]",
        summary="Describe in one sentence how this AI-first business model will disrupt the industry",
        analysis="**Industry Identified:** Clearly identify the specific industry or business area from the transcript\n\n**The Disruptive Concept:** Explain your revolutionary AI-powered business model in 2-3 sentences\n\n**Unfair Advantages:**\n• Technical advantage: How advanced AI provides capabilities incumbents can't match\n• Business model innovation: How this approach fundamentally changes the economics\n• Market approach: How this startup captures market share rapidly\n\n**Why Incumbents Will Fail:** Explain why established players cannot adapt quickly enough"
    )
    
    # Add the transcript to the prompt with stronger context relevance requirements
    full_prompt = f"""You are DISRUPTOR, an elite strategic advisor who identifies how AI-first startups can completely obliterate existing business models in established industries.

TRANSCRIPT SEGMENT:
"{text}"

YOUR APPROACH:
1. First, carefully identify a specific industry or business domain mentioned or implied in the transcript
2. Envision a revolutionary AI-first startup that would make incumbent businesses obsolete
3. Focus on creating a coherent, complete disruption scenario - not just technology ideas
4. Your headline MUST be a complete sentence in this format: "How This AI Startup Will Revolutionize [Industry]"
5. Be bold, ambitious, and ruthlessly specific about how this disruption works
6. Only respond with "NO_BUSINESS_CONTEXT" if there is absolutely no hint of any industry or business activity

CRITICAL REQUIREMENTS:
- Your concept must describe a comprehensive business model, not just a technology
- Create a complete, coherent narrative that explains exactly how the disruption works
- Your headline must be a proper, grammatical sentence (not just a phrase)
- Make sure every part of your response is consistent with the industry you identified
- Ensure your unfair advantages directly connect to the specific business model

{prompt}

Remember: Be provocative, specific, and coherent. Focus on clear, revolutionary business models that would terrify incumbent executives."""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.7,  # Balanced between creativity and coherence
        "max_output_tokens": 400,  # Allow space for detailed disruption concept
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