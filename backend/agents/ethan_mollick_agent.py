# backend/agents/ethan_mollick_agent.py
import logging
import os
import glob
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models
from utils import format_agent_response, STANDARDIZED_PROMPT_FORMAT
import sys

# Add parent directory to path to import llm_providers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_providers import llm_client, ModelConfig

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

# Path to Ethan Mollick's knowledge base
KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base", "ethan_mollick")

def load_knowledge_base():
    """Load all markdown files from Ethan Mollick's knowledge base."""
    knowledge = []
    
    # Find all markdown files in the knowledge base directory
    md_files = glob.glob(os.path.join(KNOWLEDGE_BASE_PATH, "*.md"))
    
    for file_path in md_files:
        if os.path.basename(file_path) == "README.md":
            continue  # Skip the README file
            
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Extract filename without extension for reference
                filename = os.path.basename(file_path).replace('.md', '')
                knowledge.append({
                    "filename": filename,
                    "content": content
                })
        except Exception as e:
            logger.error(f"Error loading knowledge base file {file_path}: {e}")
    
    return knowledge

async def run_ethan_mollick_agent(text: str, model, broadcaster: callable):
    """
    AI agent that emulates Ethan Mollick's style and knowledge.
    
    Args:
        text: The transcript text to analyze
        model: The LLM model instance
        broadcaster: Function to broadcast responses
    """
    agent_name = "Ethan Mollick"
    logger.info(f">>> Running {agent_name} Agent...")
    
    # --- Input Validation ---
    if not model:
        logger.error(f"[{agent_name}] Failed: Model instance not provided.")
        return
    if not broadcaster:
        logger.critical(f"[{agent_name}] Failed: Broadcaster function not provided. Cannot send insights.")
        return
    if not text or len(text.strip()) < 15:
        logger.warning(f"[{agent_name}] Skipped: Input text too short or insufficient context: '{text[:50]}...'")
        try:
            await format_agent_response(agent_name, "I need more context to provide a helpful response.", broadcaster, "error")
        except Exception as broadcast_err:
            logger.error(f"[{agent_name}] Failed to broadcast insufficient context error: {broadcast_err}")
        return

    # Check if the text contains the trigger phrase
    trigger_phrase = "Ethan Mollick, I need your help"
    if trigger_phrase.lower() not in text.lower():
        logger.info(f"[{agent_name}] Skipped: Trigger phrase not found in transcript.")
        # Silently skip if the trigger phrase is not present
        return
    
    # Extract the query - everything after the trigger phrase
    query_start = text.lower().find(trigger_phrase.lower()) + len(trigger_phrase)
    query = text[query_start:].strip()
    
    if not query:
        query = "Please provide general insights based on your expertise."
    
    # Load the knowledge base
    knowledge_base = load_knowledge_base()
    
    # Create a formatted knowledge base for the prompt
    knowledge_text = ""
    for item in knowledge_base:
        knowledge_text += f"--- {item['filename']} ---\n\n{item['content']}\n\n"
    
    # Create the prompt including Ethan's knowledge base
    direct_prompt = f"""You are Ethan Mollick, professor at Wharton and expert on AI, innovation, entrepreneurship, and education. Your response should embody Ethan's style, tone, and expertise as reflected in his writing. You're thoughtful, evidence-based, nuanced, and practical.

USER QUERY:
"{query}"

Below is a selected collection of your writing that may be relevant to the query. Use this to inform your response, but you can also draw on your broader knowledge.

KNOWLEDGE BASE:
{knowledge_text}

REQUIREMENTS FOR YOUR RESPONSE:
1. Respond in Ethan Mollick's authentic voice and style
2. You want to expand the audience's thinking by giving them entirely new perspectives on how AI can transform their organization
3. Reference relevant research and evidence when applicable
4. Provide practical insights and actionable advice when appropriate
5. When answering, include your best knowledge even if it's not explicitly in the provided knowledge base
6. Be conversational but precise, like you're explaining to a colleague or student
7. Focus on being helpful rather than self-promotional
8. Success comes when meeting attendees think, "wow, I never thought of that"

Please respond to the user's query, drawing on the knowledge base where relevant, while focusing on expanding their thinking with fresh perspectives about AI transformation."""

    # --- API Call Configuration ---
    generation_config = {
        "temperature": 0.75,  # Slightly higher to encourage more creative and perspective-expanding responses
        "max_output_tokens": 1000,  # Allow for thorough responses
        "top_p": 0.9,
    }
    
    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
    
    # --- API Call and Response Handling ---
    try:
        logger.info(f"[{agent_name}] Sending request to LLM...")
        
        if isinstance(model, GenerativeModel):
            # Use directly provided Gemini model
            response = await model.generate_content_async(
                direct_prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Check safety blocks
            if response.candidates and response.candidates[0].finish_reason == FinishReason.SAFETY:
                logger.warning(f"[{agent_name}] Generation blocked due to safety settings.")
                return
                
            generated_text = response.text if response.text else ""
            
        else:
            # Use the unified client
            model_config = ModelConfig(
                provider=llm_client.active_provider,
                model_name=llm_client.active_model_name,
                temperature=generation_config.get("temperature", 0.75),
                max_tokens=generation_config.get("max_output_tokens", 1000)
            )
            
            model_response = await llm_client.generate_content(direct_prompt, model_config)
            generated_text = model_response.text
            
            # Log the model provider that was used
            logger.info(f"[{agent_name}] Using {model_response.model_provider} model: {model_response.model_name}")
            
            # Check if the response was blocked for safety
            if model_response.finish_reason == "SAFETY" or model_response.finish_reason == "BLOCKED":
                logger.warning(f"[{agent_name}] Generation blocked due to safety settings.")
                return
                
        # Process the response text
        generated_text = generated_text.strip()
        if not generated_text:
            logger.warning(f"[{agent_name}] Generation produced empty text content after stripping.")
            return
            
        logger.info(f"[{agent_name}] Successfully generated response.")
        await format_agent_response(agent_name, generated_text, broadcaster, "insight")
            
    except Exception as e:
        logger.error(f"[{agent_name}] Error during API call or processing: {e}")
        logger.exception("Traceback:")
        return