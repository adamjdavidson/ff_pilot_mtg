# test_radical_expander.py
import asyncio
import logging
from claude_client import ClaudeClient
from agents.radical_expander import run_radical_expander

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

# Simulated broadcaster function
async def mock_broadcaster(message):
    logger.info(f"RECEIVED MESSAGE: {message}")
    print("\n--- Radical Expander Output ---")
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
    We should think about how to make our team meetings more efficient. 
    Right now, they take too long and not everyone is participating actively.
    Maybe we need a different format or structure?
    """
    
    logger.info("Running Radical Expander test...")
    await run_radical_expander(test_transcript, claude_client, mock_broadcaster)
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())