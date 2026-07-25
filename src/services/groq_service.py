import asyncio
from groq import Groq
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class GroqService:
    """Handles AI response generation via Groq API with multilingual support."""
    
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model = "mixtral-8x7b-32768"
    
    async def generate_response(
        self,
        context: str,
        creature_name: str = "Существо",
        language: str = "ru",
        target_style: Optional[dict] = None,
        conversation_history: Optional[List[dict]] = None
    ) -> str:
        """
        Generate response in specified language with style mimicry.
        
        Args:
            context: Recent comments or DM text to respond to
            creature_name: Name of the creature
            language: "ru" for Russian, "en" for English
            target_style: Style dict to mimic from target user
            conversation_history: Previous messages
        
        Returns:
            Generated response text
        """
        
        from .language_processor import LanguageProcessor
        lang_proc = LanguageProcessor(language=language)
        system_prompt = lang_proc.generate_system_prompt(language, creature_name)
        
        messages = []
        
        if conversation_history:
            messages.extend(conversation_history)
        
        # Build context with style guidance
        context_msg = f"Recent messages:\n{context}"
        if target_style:
            if target_style.get("uses_caps_words"):
                context_msg += "\n[Match their CAPS style]"
            if target_style.get("uses_ellipsis"):
                context_msg += "\n[They use ellipsis, you should too sometimes]"
            if target_style.get("uses_exclamation"):
                context_msg += "\n[They use exclamation marks, respond with energy]"
        
        messages.append({
            "role": "user",
            "content": context_msg
        })
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._call_groq,
                system_prompt,
                messages
            )
            
            # Apply target style if available
            if target_style:
                response = lang_proc.apply_style(response, target_style)
            
            logger.info(f"✓ Generated response ({language}): {response[:60]}...")
            return response
        except asyncio.CancelledError:
            logger.error("Response generation cancelled")
            return "..."
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return f"[error: {str(e)[:30]}]"
    
    def _call_groq(self, system_prompt: str, messages: List[dict]) -> str:
        """Blocking call to Groq API (runs in executor)."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}] + messages,
            temperature=0.85,
            max_tokens=200,
            top_p=0.9,
        )
        return response.choices[0].message.content.strip()
