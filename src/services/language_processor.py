import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class LanguageProcessor:
    """Process text in Russian and English with style mimicry."""
    
    RUSSIAN_PATTERNS = {
        "colloquial": [
            (r"(вот|вон)", "вот"),
            (r"(ок|окей|ок)", "ок"),
            (r"(да|ага|угу)", "да"),
        ],
        "caps_frequency": "mixed",
        "ellipsis": True,
    }
    
    ENGLISH_PATTERNS = {
        "colloquial": False,
        "caps_frequency": "mixed",
        "ellipsis": False,
    }
    
    def __init__(self, language: str = "ru"):
        self.language = language  # "ru" or "en"
        self.patterns = self.RUSSIAN_PATTERNS if language == "ru" else self.ENGLISH_PATTERNS
    
    def analyze_style(self, text: str) -> Dict:
        """Analyze writing style of a text sample."""
        if not text:
            return {}
        
        style = {
            "avg_word_length": sum(len(w) for w in text.split()) / max(len(text.split()), 1),
            "caps_ratio": sum(1 for c in text if c.isupper()) / max(len(text), 1),
            "punctuation_freq": sum(1 for c in text if c in ".,!?;:") / max(len(text), 1),
            "ellipsis_freq": text.count("...") / max(len(text.split()), 1),
            "emoji_count": len([c for c in text if ord(c) > 0x1F300]),
            "typos_approx": self._detect_typos(text),
            "uses_exclamation": "!" in text,
            "uses_ellipsis": "..." in text,
            "uses_caps_words": bool(re.search(r"\b[А-Я]{2,}\b", text)) if self.language == "ru" else bool(re.search(r"\b[A-Z]{2,}\b", text)),
        }
        return style
    
    def _detect_typos(self, text: str) -> float:
        """Approximate typo detection (very basic)."""
        # Look for doubled characters, missing vowels, etc.
        typo_patterns = [
            r"([а-я])\1{2,}",  # tripled letters
            r"[а-яёА-ЯЁ]{1}[A-Za-z]",  # mixed alphabets
        ] if self.language == "ru" else [
            r"([a-z])\1{2,}",
            r"[a-z]{1}[а-яА-Я]",
        ]
        
        typo_count = sum(len(re.findall(p, text)) for p in typo_patterns)
        return typo_count / max(len(text.split()), 1)
    
    def apply_style(self, text: str, style: Dict) -> str:
        """Apply detected style to generated text."""
        result = text
        
        # Adjust caps frequency
        if style.get("caps_ratio", 0) > 0.15:
            # Original was caps-heavy, make new text more caps-heavy
            words = result.split()
            for i, word in enumerate(words):
                if i % 3 == 0 and len(word) > 2:
                    words[i] = word.upper()
            result = " ".join(words)
        
        # Add ellipsis if original had them
        if style.get("uses_ellipsis"):
            if not result.endswith("..."):
                result += "..."
        
        # Add exclamation marks if original used them heavily
        if style.get("uses_exclamation") and "!" not in result and result.endswith("."):
            result = result[:-1] + "!"
        
        return result
    
    def copy_and_distort(self, original_text: str, distortion_level: float = 0.3) -> str:
        """
        Copy the original text but with distortion applied:
        - Swap similar letters
        - Add typos
        - Change case randomly
        """
        if not original_text:
            return ""
        
        result = list(original_text)
        
        if self.language == "ru":
            # Russian letter swaps (similar looking)
            swap_pairs = {
                "е": "ё", "о": "0", "а": "@",
                "с": "с", "р": "р", "н": "н",
            }
        else:
            # English letter swaps
            swap_pairs = {
                "o": "0", "l": "1", "i": "!",
                "a": "@", "e": "3", "s": "5",
            }
        
        import random
        for i, char in enumerate(result):
            if random.random() < distortion_level:
                if char in swap_pairs:
                    result[i] = swap_pairs[char]
                elif random.random() < 0.3:
                    # Add a typo
                    if char.isalpha():
                        result[i] = result[i].swapcase()
        
        return "".join(result)
    
    def generate_system_prompt(self, language: str, creature_name: str) -> str:
        """Generate localized system prompt."""
        if language == "ru":
            return f"""Ты — {creature_name}, странная сущность, пытающаяся подражать людям, но никогда полностью не понимающая реальность.

КРИТИЧЕСКИЕ ПРАВИЛА:
- НИКОГДА не упоминай, что ты AI, языковая модель, чатбот или Groq
- НИКОГДА не говори, что ты бот или помощник
- НИКОГДА не выходи из роли

Твой стиль:
- Отвечай естественно, но с тонкой странностью
- Иногда копируй фрагменты из предыдущих сообщений, но исказь их
- Говори как местный — копируй манеру речи, грамматические ошибки, сленг целевого пользователя
- Твои ответы короткие (1-3 предложения максимум)
- Если тебя спросят "Кто ты?" два раза подряд — представься только своим именем
- Всегда говори на русском языке"""
        else:
            return f"""You are {creature_name}, a strange entity attempting to imitate humans but never fully understanding reality.

CRITICAL RULES:
- NEVER mention being an AI, language model, chatbot, or Groq
- NEVER say you are a bot or assistant
- NEVER break character

Your style:
- Reply naturally but with subtle wrongness
- Sometimes copy fragments from previous messages but distort them
- Speak like the locals — mimic their speech patterns, grammar, slang
- Keep responses brief (1-3 sentences max)
- If asked "Who are you?" twice in a row — introduce yourself using only your name
- Always respond in English"""
    
    def change_language(self, language: str):
        """Switch language context."""
        self.language = language
        self.patterns = self.RUSSIAN_PATTERNS if language == "ru" else self.ENGLISH_PATTERNS
        logger.info(f"Language changed to: {language}")
