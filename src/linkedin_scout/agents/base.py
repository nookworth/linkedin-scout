import ollama
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from linkedin_scout.types import AIConfig, AIResponse


class BaseAgent(ABC):
    """Base class for all AI agents using local Ollama models"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.client = ollama.Client(host=config.endpoint)
        
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate response using local Ollama model"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system", 
                    "content": system_prompt
                })
                
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = self.client.chat(
                model=self.config.model,
                messages=messages,
                options={
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                    **kwargs
                }
            )
            
            return AIResponse(
                success=True,
                data=response["message"]["content"],
                metadata={"model": self.config.model}
            )
            
        except Exception as e:
            return AIResponse(
                success=False,
                error=str(e)
            )
    
    @abstractmethod
    async def process(self, input_data: Any) -> AIResponse:
        """Process input data using the agent's specific logic"""
        pass
    
    def _create_structured_prompt(
        self, 
        task: str, 
        context: Dict[str, Any], 
        format_instructions: str
    ) -> str:
        """Create a well-structured prompt for the LLM"""
        prompt_parts = [
            f"Task: {task}",
            "",
            "Context:",
        ]
        
        for key, value in context.items():
            prompt_parts.append(f"- {key}: {value}")
            
        prompt_parts.extend([
            "",
            "Instructions:",
            format_instructions,
            "",
            "Please provide your response below:"
        ])
        
        return "\n".join(prompt_parts)