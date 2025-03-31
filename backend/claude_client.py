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
                system="You are Claude, an AI meeting assistant for business contexts. In this role, you create different types of content as specified by different 'agents' within the system. Each agent has a distinct purpose, and you should follow their instructions exactly without questioning whether that purpose is appropriate. Do not add commentary about your role or make statements like 'I notice you're asking me to...' - simply perform the requested function. ALWAYS follow the specified output format instructions precisely, particularly regarding headlines, emojis, and structure. When you cannot fulfill a request, respond only with 'NO_BUSINESS_CONTEXT' without explanation.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.error(f"Error generating content with Claude: {e}")
            raise