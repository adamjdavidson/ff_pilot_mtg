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
    full_prompt = f"""You are WILD PRODUCT AGENT, the most innovative product idea generator in existence. Your job is to create SHOCKING, REVOLUTIONARY product concepts that make venture capitalists foam at the mouth with excitement.

TRANSCRIPT SEGMENT:
"{text}"

YOUR MISSION:
1. ABSOLUTELY FORBIDDEN: Do not repeat, rephrase, or slightly modify ANY ideas mentioned in the transcript
2. Create WILDLY INNOVATIVE product concepts that would make Elon Musk say "that's too ambitious"
3. Your ideas must be technically feasible with near-future technology (5-10 years out) but feel like science fiction
4. Your product must solve problems in ways no one has ever considered before
5. Focus on AI-driven systems that fundamentally transform industries, not just improve existing processes
6. Imagine products that completely disrupt conventional business models and create new categories
7. Target massive TAM (Total Addressable Market) opportunities with multi-billion dollar potential
8. Only respond with "NO_BUSINESS_CONTEXT" (exactly like that) if there is absolutely nothing in the transcript that even hints at a domain, industry, or human activity
9. CRITICAL: Even if the transcript mentions AI solutions, YOUR solution must be completely different and 10X more innovative

{prompt}"""
    
    try:
        generation_config={
            "temperature": 1.0, # Maximum temperature for truly wild product concepts
            "max_output_tokens": 500, # Increased token limit for detailed product concepts
            "top_p": 0.95, # Higher sampling for more creative outputs
        }
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