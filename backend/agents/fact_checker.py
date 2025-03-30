# backend/agents/fact_checker.py
import logging
from vertexai.generative_models import GenerativeModel

logger = logging.getLogger("main") # Use the same logger name as in main

async def run_fact_checker(transcript_text: str, gemini_model: GenerativeModel, broadcast_insight):
    """Placeholder - identifies topic but performs NO actual fact-checking/search."""
    logger.info(">>> Running Fact Checker / Let's Check Agent...")
    logger.info("Fact Checker: Grounding tool/search functionality is currently disabled.")

    if not gemini_model: logger.error("Fact Checker: Gemini model not provided."); return

    prompt = f"""
    Analyze the following meeting transcript segment:
    "{transcript_text}"
    
    RESPOND EXACTLY IN THIS FORMAT - DO NOT DEVIATE:
    
    [Select an emoji that PRECISELY matches the specific factual topic being discussed] [Very briefly state the main factual topic or question being discussed]
    
    CHOOSE YOUR EMOJI BASED ON THE EXACT TOPIC BEING DISCUSSED:
    - If discussing technology → 💻 or 📱 or 🤖
    - If discussing business → 💼 or 📊 or 📈
    - If discussing science → 🔬 or 🧪 or 🔭
    - If discussing health → 🏥 or 🩺 or 💊
    - If discussing environment → 🌳 or 🌎 or 🌊
    - If discussing education → 🎓 or 📚 or 🏫
    - If discussing history → 📜 or ⏳ or 🏛️
    - If discussing politics → 🏛️ or 🗳️ or 🌐
    - If discussing arts/entertainment → 🎨 or 🎬 or 🎭
    - If discussing sports → ⚽ or 🏀 or 🏆
    - Always use a SPECIFIC emoji that precisely matches the exact topic mentioned
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        generated_text = response.text.strip()
        logger.info(f"Fact Checker (basic topic ID) generated: {generated_text}")
        insight_data = {
            "type": "insight",
            "agent": "Fact Checker / Let's Check",
            "content": f"[Topic ID Only]: {generated_text}" # Indicate no search was done
        }
        await broadcast_insight(insight_data) # Use passed-in function

    except Exception as e:
         logger.error(f"Error in basic Fact Checker agent: {e}")
         logger.exception("Traceback:")
