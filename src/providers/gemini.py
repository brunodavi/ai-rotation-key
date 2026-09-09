from src.sanitizer import Sanitizer


BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
NAME = "gemini"


class GeminiSanitizer(Sanitizer):
    """Herda o comportamento genérico; customizações do Gemini vêm aqui."""
