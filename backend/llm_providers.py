"""
LLM Provider abstraction layer for the AI Meeting Assistant.

This module provides a unified interface for different LLM providers,
allowing seamless switching between Gemini and Claude models.
"""

import os
import logging
import json
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable
from dotenv import load_dotenv

# Import provider SDKs
import anthropic
from vertexai.generative_models import GenerativeModel, Content, Part
import vertexai.generative_models as gm

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("main")

class ModelProvider(str, Enum):
    """Supported model providers."""
    GEMINI = "gemini"
    CLAUDE = "claude"

class ModelConfig:
    """Configuration for LLM models."""
    def __init__(
        self,
        provider: ModelProvider,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 0.95,
        top_k: int = 40
    ):
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.top_k = top_k

class ModelResponse:
    """Standardized model response across providers."""
    def __init__(
        self,
        text: str,
        finish_reason: str,
        model_provider: ModelProvider,
        model_name: str,
        usage: Dict[str, int] = None
    ):
        self.text = text
        self.finish_reason = finish_reason
        self.model_provider = model_provider
        self.model_name = model_name
        self.usage = usage or {}

class UnifiedLLMClient:
    """
    Unified client for interacting with different LLM providers.
    """
    def __init__(self):
        # Initialize provider clients
        self.gemini_model = None
        self.claude_client = None
        self.active_provider = None
        self.active_model_name = None
        
        # Try to load Gemini model
        try:
            from google.cloud import aiplatform
            gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-002")
            project_id = os.getenv("PROJECT_ID", "meetinganalyzer-454912")
            location = os.getenv("LOCATION", "us-east1")
            
            # Initialize Vertex AI
            aiplatform.init(project=project_id, location=location)
            self.gemini_model = GenerativeModel(gemini_model_name)
            logger.info(f"Initialized Gemini model: {gemini_model_name}")
            
            # Set as default if no other provider is active
            if not self.active_provider:
                self.active_provider = ModelProvider.GEMINI
                self.active_model_name = gemini_model_name
                
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
        
        # Try to load Claude client
        try:
            claude_api_key = os.getenv("ANTHROPIC_API_KEY")
            if claude_api_key:
                self.claude_client = anthropic.Anthropic(api_key=claude_api_key)
                logger.info("Initialized Claude client")
                
                # Set as default if Gemini isn't available
                if not self.gemini_model and not self.active_provider:
                    self.active_provider = ModelProvider.CLAUDE
                    self.active_model_name = "claude-3-7-sonnet-20240307"
            else:
                logger.warning("No Anthropic API key found in environment variables")
                
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
    
    def set_active_provider(self, provider: ModelProvider, model_name: Optional[str] = None) -> bool:
        """
        Set the active LLM provider.
        
        Args:
            provider: The provider to activate (GEMINI or CLAUDE)
            model_name: Optional specific model name to use
        
        Returns:
            bool: True if successful, False otherwise
        """
        if provider == ModelProvider.GEMINI and self.gemini_model:
            self.active_provider = ModelProvider.GEMINI
            self.active_model_name = model_name or "gemini-1.5-pro-002"
            logger.info(f"Set active provider to Gemini: {self.active_model_name}")
            return True
            
        elif provider == ModelProvider.CLAUDE and self.claude_client:
            self.active_provider = ModelProvider.CLAUDE
            self.active_model_name = model_name or "claude-3-7-sonnet-20240307"
            logger.info(f"Set active provider to Claude: {self.active_model_name}")
            return True
            
        else:
            logger.error(f"Cannot set provider to {provider}: not initialized")
            return False
    
    async def generate_content(self, 
                              prompt: str, 
                              config: Optional[ModelConfig] = None) -> ModelResponse:
        """
        Generate content from the active LLM provider.
        
        Args:
            prompt: The prompt to send to the model
            config: Optional model configuration
        
        Returns:
            ModelResponse with standardized fields
        """
        if config is None:
            # Use default configuration
            config = ModelConfig(
                provider=self.active_provider,
                model_name=self.active_model_name
            )
        
        if self.active_provider == ModelProvider.GEMINI:
            return await self._generate_with_gemini(prompt, config)
        elif self.active_provider == ModelProvider.CLAUDE:
            return await self._generate_with_claude(prompt, config)
        else:
            raise ValueError(f"No active provider set or provider not supported: {self.active_provider}")
    
    async def _generate_with_gemini(self, prompt: str, config: ModelConfig) -> ModelResponse:
        """Generate content using Gemini."""
        try:
            generation_config = {
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k
            }
            
            safety_settings = {
                gm.HarmCategory.HARM_CATEGORY_HARASSMENT: gm.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                gm.HarmCategory.HARM_CATEGORY_HATE_SPEECH: gm.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                gm.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: gm.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                gm.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: gm.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            }
            
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Extract finish reason
            finish_reason = "STOP"
            if response.candidates and response.candidates[0].finish_reason:
                finish_reason = str(response.candidates[0].finish_reason)
            
            # Construct standardized response
            return ModelResponse(
                text=response.text,
                finish_reason=finish_reason,
                model_provider=ModelProvider.GEMINI,
                model_name=config.model_name
            )
            
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            raise
    
    async def _generate_with_claude(self, prompt: str, config: ModelConfig) -> ModelResponse:
        """Generate content using Claude."""
        try:
            # Create message request
            response = await self.claude_client.messages.create(
                model=config.model_name,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system="You are an AI meeting assistant providing insights during meetings.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text from response
            content = response.content[0].text if response.content else ""
            
            # Construct standardized response
            return ModelResponse(
                text=content,
                finish_reason=response.stop_reason or "STOP",
                model_provider=ModelProvider.CLAUDE,
                model_name=config.model_name,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating content with Claude: {e}")
            raise
    
    def available_models(self) -> Dict[str, List[str]]:
        """
        Returns a dictionary of available models grouped by provider.
        """
        models = {}
        
        if self.gemini_model:
            models[ModelProvider.GEMINI] = [
                "gemini-1.5-pro-002",
                "gemini-1.5-flash-002"
            ]
            
        if self.claude_client:
            models[ModelProvider.CLAUDE] = [
                "claude-3-7-sonnet-20240307", 
                "claude-3-5-sonnet-20240620", 
                "claude-3-opus-20240229"
            ]
            
        return models

# Create singleton instance
llm_client = UnifiedLLMClient()