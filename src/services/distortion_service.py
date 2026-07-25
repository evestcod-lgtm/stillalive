import random


class DistortionService:
    """Apply Unicode distortion to text for eerie effect."""
    
    def __init__(self):
        # Russian character replacements (similar-looking but different)
        self.ru_distortion = {
            'а': 'ａ', 'е': 'ё', 'о': 'ο', 'с': 'ѕ',
            'р': 'ѡ', 'н': 'һ', 'х': 'һ', 'у': 'υ',
            'А': 'Α', 'Е': 'Ё', 'О': 'Ο', 'С': 'Ѕ',
        }
        # English character replacements
        self.en_distortion = {
            'a': 'ａ', 'e': 'ё', 'o': 'ο', 'i': 'і',
            'l': '1', 'o': '0', 's': '5',
        }
        # Zalgo combining characters
        self.combining = [
            '\u0300', '\u0301', '\u0302', '\u0303', '\u0304',
            '\u0305', '\u0306', '\u0307', '\u0308', '\u0309',
        ]
    
    def apply_distortion(self, text: str, language: str = "ru", intensity: float = 0.35) -> str:
        """Apply character replacement distortion."""
        distortion_map = self.ru_distortion if language == "ru" else self.en_distortion
        result = []
        
        for char in text:
            if char in distortion_map and random.random() < intensity:
                result.append(distortion_map[char])
            else:
                result.append(char)
        
        return ''.join(result)
    
    def add_zalgo(self, text: str, intensity: float = 0.2) -> str:
        """Add zalgo-style combining characters."""
        result = []
        for char in text:
            result.append(char)
            if random.random() < intensity:
                result.append(random.choice(self.combining))
        return ''.join(result)
    
    def copy_with_distortion(self, original: str, language: str = "ru") -> str:
        """Copy text with subtle distortions applied."""
        # Apply both distortion types
        distorted = self.apply_distortion(original, language, intensity=0.25)
        distorted = self.add_zalgo(distorted, intensity=0.15)
        return distorted
    
    def full_distortion(self, text: str, language: str = "ru") -> str:
        """Apply maximum distortion (for "distorted font" mode)."""
        distorted = self.apply_distortion(text, language, intensity=0.45)
        distorted = self.add_zalgo(distorted, intensity=0.3)
        return distorted
