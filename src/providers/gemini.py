from src.providers.base import Provider


class Gemini(Provider):
    name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
