"""
Translation module.
Handles text translation and language detection.
"""
import logging
from typing import Optional

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0  # Consistent results
except ImportError:
    detect = None

logger = logging.getLogger(__name__)


class Translator:
    """Handle text translation and language detection."""
    
    def __init__(self):
        """Initialize translator."""
        if GoogleTranslator is None:
            logger.warning("deep-translator not installed. Translation unavailable.")
        
        if detect is None:
            logger.warning("langdetect not installed. Language detection unavailable.")
    
    def detect_language(self, text: Optional[str]) -> Optional[str]:
        """Detect language of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code (e.g., 'en', 'fa', 'ar') or None
        """
        if not text or detect is None:
            return None
        
        try:
            # Ensure text has enough content for detection
            if len(text.strip()) < 10:
                return None
            
            lang_code = detect(text)
            logger.debug(f"Detected language: {lang_code}")
            return lang_code
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return None
    
    def translate_to_persian(
        self, 
        text: str, 
        source_lang: Optional[str] = None
    ) -> Optional[str]:
        """Translate text to Persian (Farsi).
        
        Args:
            text: Text to translate
            source_lang: Source language code (auto-detect if None)
            
        Returns:
            Translated text or None if translation fails
        """
        if not text or GoogleTranslator is None:
            return None
        
        try:
            # Auto-detect source language if not provided
            if not source_lang:
                source_lang = self.detect_language(text)
            
            # Don't translate if already Persian
            if source_lang and source_lang.startswith("fa"):
                logger.debug("Text already in Persian")
                return text
            
            # Translate
            translator = GoogleTranslator(source='auto', target='fa')
            translated = translator.translate(text)
            
            logger.debug(f"Translated from {source_lang or 'auto'} to Persian")
            return translated
            
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return None
    
    def translate(
        self,
        text: str,
        target_lang: str = 'fa',
        source_lang: Optional[str] = None
    ) -> Optional[str]:
        """Translate text to target language.
        
        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Source language code (auto-detect if None)
            
        Returns:
            Translated text or None
        """
        if not text or GoogleTranslator is None:
            return None
        
        try:
            # Auto-detect if needed
            if not source_lang:
                source_lang = self.detect_language(text) or 'auto'
            
            # Don't translate if source and target are the same
            if source_lang.startswith(target_lang):
                return text
            
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated = translator.translate(text)
            
            logger.debug(f"Translated from {source_lang} to {target_lang}")
            return translated
            
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return None
    
    def translate_batch(
        self,
        texts: list[str],
        target_lang: str = 'fa',
        source_lang: Optional[str] = None
    ) -> list[Optional[str]]:
        """Translate multiple texts.
        
        Args:
            texts: List of texts to translate
            target_lang: Target language code
            source_lang: Source language code
            
        Returns:
            List of translated texts (None for failed translations)
        """
        results = []
        
        for text in texts:
            translated = self.translate(text, target_lang, source_lang)
            results.append(translated)
        
        return results
    
    def is_persian(self, text: Optional[str]) -> bool:
        """Check if text is in Persian.
        
        Args:
            text: Text to check
            
        Returns:
            True if Persian, False otherwise
        """
        if not text:
            return False
        
        lang = self.detect_language(text)
        return lang is not None and lang.startswith('fa')
    
    def is_english(self, text: Optional[str]) -> bool:
        """Check if text is in English.
        
        Args:
            text: Text to check
            
        Returns:
            True if English, False otherwise
        """
        if not text:
            return False
        
        lang = self.detect_language(text)
        return lang is not None and lang.startswith('en')
    
    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes.
        
        Returns:
            List of language codes supported by GoogleTranslator
        """
        if GoogleTranslator is None:
            return []
        
        try:
            return list(GoogleTranslator().get_supported_languages())
        except Exception:
            return []