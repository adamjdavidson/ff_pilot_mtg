# test_product_agent.py
import asyncio
import logging
from claude_client import ClaudeClient
from agents.product_agent import run_product_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

# Simulated broadcaster function
async def mock_broadcaster(message):
    logger.info(f"RECEIVED MESSAGE: {message}")
    print("\n--- Product Agent Output ---")
    print(f"Type: {message['type']}")
    print(f"Agent: {message['agent']}")
    print(f"Content: {message['content']}")
    print("------------------------\n")

async def main():
    # Initialize Claude client
    claude_client = ClaudeClient()
    logger.info(f"Claude client initialized with model: {claude_client.model_name}")
    
    # Test transcript
    test_transcript = """
    We need to find a way to help our marketing team analyze all the social media data we're collecting.
    They're overwhelmed with the volume of comments, tweets, and posts about our product.
    It's impossible to manually go through everything and identify the key trends and customer sentiment.
    """
    
    logger.info("Running Product Agent test...")
    await run_product_agent(test_transcript, claude_client, mock_broadcaster)
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())