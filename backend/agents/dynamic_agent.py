# backend/agents/dynamic_agent.py
import logging
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT
import sys
import os

# Add parent directory to path to import llm_providers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_providers import llm_client, ModelConfig

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

async def run_dynamic_agent(text: str, model, broadcaster: callable, agent_config: dict):
    """
    A flexible agent that can be configured at runtime with custom goals and parameters.
    
    Args:
        text: The transcript text to analyze
        model: The Gemini model instance
        broadcaster: Function to broadcast responses
        agent_config: Dictionary with agent configuration including name, goal, etc.
    """
    agent_name = agent_config.get("name", "Custom Agent")
    agent_goal = agent_config.get("goal", "Analyze the transcript and provide insights")
    
    logger.info(f">>> Running dynamic agent: {agent_name}")
    
    # --- Input Validation ---
    if not model:
        logger.error(f"[{agent_name}] Failed: Gemini model instance not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided. Cannot send insights.")
        return
    if not text or len(text.strip()) < 15:
        logger.warning(f"[{agent_name}] Skipped: Input text too short or insufficient context: '{text[:50]}...'")
        try:
            await format_agent_response(agent_name, f"Insufficient context to generate insights for {agent_name}.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return
    
    # Customize the standardized prompt for this specific agent
    specific_content = f"insights related to: {agent_goal}"
    
    prompt = STANDARDIZED_PROMPT_FORMAT.format(
        specific_content=specific_content,
        analysis=f"Detailed analysis of how this relates to {agent_goal}. Provide specific, actionable insights."
    )
    
    # Check if a specific prompt template version is requested
    template = None
    if "version_name" in agent_config:
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from agent_versions import get_agent_versions
        
        version_name = agent_config.get("version_name")
        # Get all versions of this agent
        agent_versions = get_agent_versions(agent_name)
        
        # Find the specified version
        for version in agent_versions:
            if version.get("version_name") == version_name:
                template = version.get("prompt_text")
                logger.info(f"Using versioned prompt for {agent_name}: {version_name}")
                break
    
    # If no versioned prompt was found, use the provided prompt or default
    if not template:
        template = agent_config.get("prompt") or f"""You are {agent_name}, an AI agent that specializes in: {agent_goal}

TRANSCRIPT:
"{text}"

Your task is to analyze this transcript segment through the lens of your specialization.
Be creative in finding connections to your area of expertise, but be genuine and specific.
If there truly is no connection to your specialty, respond with "NO_RELEVANT_CONTEXT".

{prompt}

GUIDELINES:
1. Write like a brilliant, excited entrepreneur sharing their vision - not like corporate marketing
2. Keep your headline clear, exciting and sophisticated
3. NO arbitrary metrics, percentages, or manufactured statistics
4. NO buzzwords like "revolutionize," "transform," "disrupt," "optimize," etc.
5. Be specific about ideas but use natural, passionate language
6. Write from a place of genuine excitement about possibilities, not hype
7. ORIGINALITY IS CRITICAL: Your insights must go beyond what's directly stated in the transcript
8. If you find no connections to your specialty, just respond with "NO_RELEVANT_CONTEXT"
"""

    # Replace placeholders in template
    full_prompt = template.replace("{name}", agent_name)
    full_prompt = full_prompt.replace("{goal}", agent_goal)
    full_prompt = full_prompt.replace("{text}", text)
    
    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.7,  # Balanced creativity and coherence
        "max_output_tokens": 500, # Allow space for detailed response
    }
    
    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
    
    # --- API Call and Response Handling ---
    try:
        # Use the model parameter for backwards compatibility if it's a GenerativeModel
        # Otherwise, use the unified llm_client for maximum compatibility
        logger.info(f"[{agent_name}] Sending request to LLM...")
        
        if isinstance(model, GenerativeModel):
            # Legacy path - use directly provided Gemini model
            response = await model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Check safety blocks
            if response.candidates and response.candidates[0].finish_reason == FinishReason.SAFETY:
                logger.warning(f"[{agent_name}] Generation blocked due to safety settings.")
                # Don't send error card
                return
                
            generated_text = response.text if response.text else ""
            
        else:
            # Use unified client - preferred path
            model_config = ModelConfig(
                provider=llm_client.active_provider,
                model_name=llm_client.active_model_name,
                temperature=generation_config.get("temperature", 0.7),
                max_tokens=generation_config.get("max_output_tokens", 500)
            )
            
            model_response = await llm_client.generate_content(full_prompt, model_config)
            generated_text = model_response.text
            
            # Log the model provider that was used
            logger.info(f"[{agent_name}] Using {model_response.model_provider} model: {model_response.model_name}")
            
            # Check if the response was blocked for safety
            if model_response.finish_reason == "SAFETY" or model_response.finish_reason == "BLOCKED":
                logger.warning(f"[{agent_name}] Generation blocked due to safety settings.")
                # Don't send error card
                return
                
        # Process the response text
        generated_text = generated_text.strip()
        if not generated_text:
            logger.warning(f"[{agent_name}] Generation produced empty text content after stripping.")
            # Don't send error card
            return
            
        # Check for explicit insufficient context marker
        elif generated_text.lower() == "no_relevant_context":
            logger.info(f"[{agent_name}] Explicit no context marker detected, not sending card.")
            # Don't send any response card when explicitly marked as no context
            return
            
        else:
            logger.info(f"[{agent_name}] Successfully generated insight.")
            await format_agent_response(agent_name, generated_text, broadcaster, "insight")
            
    except Exception as e:
        logger.error(f"[{agent_name}] Error during Gemini API call or processing: {e}")
        logger.exception("Traceback:")
        # Don't broadcast errors to frontend
        if "429 Resource exhausted" in str(e):
            logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{agent_name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        return