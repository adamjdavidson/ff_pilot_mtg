import os
import logging
import anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("main")

class ClaudeClient:
    def __init__(self):
        # Get API key from environment variables
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("Missing Anthropic API key")
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
        # Initialize the Claude client
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = "claude-3-7-sonnet-20250219"
        logger.info(f"Initialized Claude client with model: {self.model_name}")
    
    def generate_content(self, prompt, temp=0.7, max_tokens=1000):
        """Generate content using Claude (synchronous)"""
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temp,
                system="You are an AI meeting assistant providing insights during meetings.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.error(f"Error generating content with Claude: {e}")
            raise