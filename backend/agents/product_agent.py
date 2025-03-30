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
    agent_name = "Product Agent"
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
    specific_content = "a revolutionary, mind-blowing product concept that makes venture capitalists desperate to invest billions"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        analysis="🚀 **The Revolutionary Product:** Detailed description of your sci-fi-level product concept\n\n💰 **Billion-Dollar Potential:** How this creates an entirely new market category\n\n⚡ **Technical Moonshot:** The breakthrough technology that makes this possible\n\n🔮 **Future Impact:** How this product changes human behavior forever"
    )
    
    # COMPLETELY OVERRIDE THE STANDARDIZED PROMPT - going directly to what we want
    direct_prompt = f"""You are WILD PRODUCT AGENT, inventing mind-blowing, sci-fi level product ideas.

TRANSCRIPT:
"{text}"

RESPOND EXACTLY IN THIS FORMAT - DO NOT DEVIATE:

🔬 Our bio-inspired sensors create an invisible layer of building intelligence

🏙️ Physical spaces respond to inhabitants like living organisms, anticipating needs before they arise.

🚀 **The Revolutionary Product:**
[Describe a mind-blowing product concept that feels like science fiction but is technically feasible within 5-10 years. Be extremely specific about what it does and how it works.]

💰 **Billion-Dollar Potential:**
[Explain how this creates an entirely new market category worth $100B+. Include a specific number for market size.]

⚡ **Technical Moonshot:**
[Describe the precise breakthrough technology that makes this possible. Be specific about the technical innovation.]

🔮 **Future Impact:**
[Explain how this product fundamentally changes human behavior or society. Include a bold, specific prediction.]

REQUIREMENTS:
1. YOUR HEADLINE MUST START WITH AN EMOJI followed by a space
2. YOUR SUMMARY MUST ALSO START WITH AN EMOJI followed by a space
3. Write like a brilliant, excited entrepreneur sharing their vision - not like corporate marketing
4. Keep the headline clear, exciting and sophisticated - around 10-15 words
5. NO arbitrary metrics, percentages, or manufactured statistics
6. NO buzzwords like "revolutionize," "transform," "disrupt," "optimize," etc.
7. Be specific about the idea but use natural, passionate language
8. Write from a place of genuine excitement about possibilities, not hype
9. Each section should build on your central idea with specific details
10. ORIGINALITY IS CRITICAL: Your idea must be completely different from the transcript
11. Imagine "What would this look like executed brilliantly 3 years from now?"

Format your output EXACTLY as shown in the example. Include emoji headers.

If you truly can't find ANY hint of a domain or problem to solve, respond ONLY with "NO_BUSINESS_CONTEXT"."""
    
    try:
        generation_config={
            "temperature": 1.0, # Maximum temperature for truly wild product concepts
            "max_output_tokens": 600, # Increased token limit for detailed product concepts
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
            direct_prompt, # USE THE DIRECT PROMPT INSTEAD
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