# backend/agents/product_agent.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT

logger = logging.getLogger("main")

# Function expects 'text' (current segment), 'model', 'broadcaster'
async def run_product_agent(text: str, model: GenerativeModel, broadcaster: callable):
    """
    Listens for triggers (product mentions, explorations, problems) and invents
    wildly new AI-enabled products/services, providing rough estimates for them.
    Assumes the input text has already been deemed relevant by the traffic cop.
    """
    agent_name = "Wild Product Agent"
    logger.info(f">>> Running {agent_name} Agent...")
    if not model: logger.error(f"[{agent_name}] Failed: Gemini model instance not provided."); return
    if not broadcaster: logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided."); return
    if not text or len(text.strip()) < 15: # Reduced minimum length requirement
        logger.warning(f"[{agent_name}] Skipped: Input text too short or insufficient context: '{text[:50]}...'");
        try:
            await format_agent_response(agent_name, "Insufficient context to invent a meaningful product concept.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Customize the standardized prompt for this specific agent
    specific_content = "wildly new AI-enabled product ideas with market potential, realism assessment, and estimated timeframe"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        headline="Write a catchy headline for your product idea",
        summary="Provide a 1-2 sentence summary of your product idea",
        analysis="Detailed description of your wildly new product/service concept\n\n**Market Potential:** Your estimate of market size/potential\n**Realism:** Your assessment of feasibility\n**Timeframe:** Your estimated timeline for implementation"
    )
    
    # Add the transcript to the prompt with stronger context relevance requirements
    full_prompt = f"""Analyze the following meeting transcript segment. Your response MUST be directly relevant to the specific topics, industries, or problems mentioned in this transcript:

"{text}"

IMPORTANT: Try to generate product ideas that relate in some way to themes in the transcript. Be creative in finding connections between the discussion and potential AI products. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely nothing in the transcript that could inspire a product idea.

{prompt}"""
    
    try:
        generation_config={"temperature": 0.6, "max_output_tokens": 400} # Reduced temperature for more focused responses
        safety_settings={
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        logger.info(f"[{agent_name}] Sending request to Gemini model...")
        response = await model.generate_content_async(
            full_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.debug(f"[{agent_name}] Raw response: {response}")

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
                logger.info(f"[{agent_name}] Successfully generated product idea.")
                await format_agent_response(agent_name, generated_text, broadcaster, "insight")
        else:
            finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
            logger.warning(f"[{agent_name}] Generation produced no text content. Finish Reason: {finish_reason}")
            # Don't send error card
            return

    except Exception as e:
        logger.error(f"[{agent_name}] Error during generation or broadcasting: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return