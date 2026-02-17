"""
Internationalization (i18n) utilities for the application.
Provides translation support using Babel and gettext.
"""

import os
import gettext
from pathlib import Path
from typing import Optional
from contextvars import ContextVar
from functools import lru_cache

from babel import Locale
from babel.support import Translations

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger()

# Context variable to store current language for async operations
current_language: ContextVar[str] = ContextVar(
    "current_language", default=settings.DEFAULT_LANGUAGE
)

# Base directory for translations
LOCALES_DIR = Path(__file__).parent.parent / "locales"


@lru_cache(maxsize=len(settings.SUPPORTED_LANGUAGES))
def get_translations(language: str) -> Optional[Translations]:
    """
    Get translations for a specific language.
    Uses LRU cache to avoid loading the same translation files multiple times.

    Args:
        language: Language code (e.g., 'en', 'ar', 'fr')

    Returns:
        Translations object or None if not found
    """
    try:
        if language not in settings.SUPPORTED_LANGUAGES:
            logger.warning(
                f"Unsupported language: {language}, falling back to {settings.DEFAULT_LANGUAGE}"
            )
            language = settings.DEFAULT_LANGUAGE

        translations = Translations.load(
            dirname=str(LOCALES_DIR), locales=[language], domain="messages"
        )
        return translations
    except FileNotFoundError:
        logger.warning(f"Translation file not found for language: {language}")
        return None
    except Exception as e:
        logger.error(f"Error loading translations for {language}: {e}")
        return None


def _(message: str, **kwargs) -> str:
    """
    Translate a message to the current language.
    This is the main translation function to use throughout the application.

    Args:
        message: The message to translate (in English)
        **kwargs: Format arguments for the message

    Returns:
        Translated and formatted message

    Example:
        >>> _("Hello, {name}!", name="John")
        "Hello, John!"
        >>> # In Arabic context:
        >>> _("Hello, {name}!", name="أحمد")
        "مرحباً، أحمد!"
    """
    lang = current_language.get()
    translations = get_translations(lang)

    if translations:
        translated = translations.gettext(message)
    else:
        translated = message

    # Format the message with kwargs if provided
    if kwargs:
        try:
            translated = translated.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key in translation: {e}")
            translated = message.format(**kwargs)

    return translated


def set_language(language: str) -> None:
    """
    Set the current language for translations.

    Args:
        language: Language code (e.g., 'en', 'ar', 'fr')
    """
    if language in settings.SUPPORTED_LANGUAGES:
        current_language.set(language)
    else:
        logger.warning(f"Attempted to set unsupported language: {language}")
        current_language.set(settings.DEFAULT_LANGUAGE)


def get_current_language() -> str:
    """
    Get the current language code.

    Returns:
        Current language code
    """
    return current_language.get()


def get_locale(language: Optional[str] = None) -> Locale:
    """
    Get Babel Locale object for the given language.

    Args:
        language: Language code, if None uses current language

    Returns:
        Babel Locale object
    """
    lang = language or current_language.get()
    try:
        return Locale.parse(lang)
    except Exception as e:
        logger.error(f"Error parsing locale {lang}: {e}")
        return Locale.parse(settings.DEFAULT_LANGUAGE)


def parse_accept_language(accept_language: Optional[str]) -> str:
    """
    Parse the Accept-Language header and return the best match.

    Args:
        accept_language: Accept-Language header value

    Returns:
        Best matching language code from supported languages

    Example:
        >>> parse_accept_language("fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7")
        "fr"
    """
    if not accept_language:
        return settings.DEFAULT_LANGUAGE

    # Parse the Accept-Language header
    # Format: "en-US,en;q=0.9,fr;q=0.8"
    languages = []
    for lang_entry in accept_language.split(","):
        parts = lang_entry.strip().split(";")
        lang = parts[0].split("-")[0].lower()  # Get base language code

        # Get quality value (default to 1.0)
        quality = 1.0
        if len(parts) > 1:
            try:
                quality = float(parts[1].split("=")[1])
            except (IndexError, ValueError):
                pass

        languages.append((lang, quality))

    # Sort by quality (highest first)
    languages.sort(key=lambda x: x[1], reverse=True)

    # Find first supported language
    for lang, _ in languages:
        if lang in settings.SUPPORTED_LANGUAGES:
            return lang

    return settings.DEFAULT_LANGUAGE


def ngettext(singular: str, plural: str, n: int, **kwargs) -> str:
    """
    Translate a message with plural forms.

    Args:
        singular: Singular form of the message
        plural: Plural form of the message
        n: Number to determine which form to use
        **kwargs: Format arguments for the message

    Returns:
        Translated and formatted message

    Example:
        >>> ngettext("You have {n} message", "You have {n} messages", count, n=count)
    """
    lang = current_language.get()
    translations = get_translations(lang)

    if translations:
        translated = translations.ngettext(singular, plural, n)
    else:
        translated = singular if n == 1 else plural

    # Format the message with kwargs if provided
    if kwargs:
        translated = translated.format(**kwargs)

    return translated
