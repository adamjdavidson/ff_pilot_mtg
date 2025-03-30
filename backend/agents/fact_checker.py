# backend/agents/fact_checker.py
import logging

logger = logging.getLogger("main") # Use the same logger name as in main

async def run_fact_checker(transcript_text: str, claude_client, broadcast_insight):
    """Placeholder - identifies topic but performs NO actual fact-checking/search."""
    logger.info(">>> Running Fact Checker / Let's Check Agent...")
    logger.info("Fact Checker: Grounding tool/search functionality is currently disabled.")

    if not claude_client: logger.error("Fact Checker: Claude client not provided."); return

    prompt = f"""
    Analyze the following meeting transcript segment:
    "{transcript_text}"
    Very briefly, state the main factual topic or question being discussed.
    """
    try:
        generated_text = claude_client.generate_content(prompt, temp=0.7, max_tokens=100)
        generated_text = generated_text.strip()
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
