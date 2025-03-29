# backend/agents/product_agent.py (Corrected insight_type)
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models

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
    if not text or len(text.strip()) < 10: logger.warning(f"[{agent_name}] Skipped: Input text too short."); return # Add check

    prompt = f"""
You are an AI 'Wild Product Inventor'. Your goal is to listen to meeting discussions about existing products/services, new product explorations, or unaddressed customer problems, and invent entirely new, potentially paradigm-shifting products or services enabled by advanced AI. Think far beyond incremental improvements and focus on how AI enables fundamentally new ways to create, deliver, or experience products/services.

Analyze the following meeting transcript segment (which the Traffic Cop has deemed relevant):
"{text}"

Based SOLELY on this segment and your general knowledge:

1.  **Invent:** Describe the SINGLE BEST (or at most two) 'wildly new' product or service concept enabled by AI, inspired by the transcript segment. Be creative, provocative, and focus on fundamental shifts.
2.  **Provide Estimates:** For the invented concept(s), provide the following as *very rough, speculative, casual estimates*:
    * **Market Potential:** (e.g., "Potentially a multi-million dollar niche," "Could be a multi-billion dollar market if successful," "High volume, low margin possibility," "Low volume, high price point")
    * **Realism:** ("Highly speculative," "Likely idea (with significant AI development)," or "Unlikely idea (major breakthroughs needed)")
    * **Timeframe:** (e.g., "Timeline: 1-3 years," "Timeline: 2-4 years, depending on AI progress," "Timeline: 3-5+ years")
3.  **Format Output:** Structure your response clearly, like the example below.

**--- BEGIN EXAMPLE OUTPUT FORMAT (Use this structure) ---**

**Wild Product Idea:** [Concise description of the wildly new product/service concept and how AI enables it.]
**Market Potential:** [Your casual estimate of market size/type, e.g., "Multi-billion dollar potential by disrupting X industry."]
**Realism:** [Your assessment, e.g., "Likely idea (with significant AI development)"]
**Timeframe:** [Your estimated range, e.g., "Timeline: 2-4 years, depending on AI progress"]

**(Optional: Add a second idea here if truly distinct and valuable, using the same format)**

**--- END EXAMPLE OUTPUT FORMAT ---**
"""
    try:
        generation_config={"temperature": 0.8, "max_output_tokens": 400}
        safety_settings={
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        logger.info(f"[{agent_name}] Sending request to Gemini model...")
        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.debug(f"[{agent_name}] Raw response: {response}")

        generated_content = ""
        insight_type = "insight" # CHANGED to "insight"

        if response.candidates and response.candidates[0].finish_reason == FinishReason.SAFETY:
            logger.warning(f"[{agent_name}] Generation blocked due to safety settings.")
            generated_content = "[Blocked due to safety settings]"
            insight_type = "error"
        elif response.text:
            generated_text = response.text.strip()
            if not generated_text:
                 logger.warning(f"[{agent_name}] Generation produced empty text content after stripping.")
                 generated_content = "[Empty response received]"
                 insight_type = "error"
            else:
                 logger.info(f"[{agent_name}] Successfully generated product idea.")
        else:
            finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
            logger.warning(f"[{agent_name}] Generation produced no text content. Finish Reason: {finish_reason}")
            generated_content = "[No content generated]"
            insight_type = "error"

        # --- Broadcast Result (Formatted) ---
        if insight_type == "error":
            # For errors, don't try to format generated_text which might not exist
            formatted_content = generated_content
        else:
            # For successful insights, properly format the content
            formatted_content = f"Wild Product Idea:\n\n{generated_text}"

        insight_data = {
            "type": insight_type,
            "agent": agent_name,
            "content": formatted_content
        }
        await broadcaster(insight_data)
        logger.info(f"[{agent_name}] Broadcast sent: Type={insight_type}")

    except Exception as e:
        logger.error(f"[{agent_name}] Error during generation or broadcasting: {e}")
        logger.exception("Traceback:")
        try:
            await broadcaster({
                "type": "error",
                "agent": agent_name,
                "message": f"{agent_name} failed: {e}"
            })
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast agent error message: {broadcast_err}")