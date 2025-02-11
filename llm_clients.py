from openai import OpenAI


class BaseLLMClient:
    def chat_completion(self, model_name, messages, **kwargs):
        raise NotImplementedError(
            "Subclasses must implement chat_completion method")


class GeminiClient(BaseLLMClient):
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

    def chat_completion(self, model_name, messages, **kwargs):
        return self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            **kwargs
        )


class OpenRouterClient(BaseLLMClient):
    def __init__(self, api_key):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def chat_completion(self, model_name, messages, extra_headers=None, extra_body=None, **kwargs):
        headers = {}
        if extra_headers:
            headers.update(extra_headers)
        body = {}
        if extra_body:
            body.update(extra_body)

        return self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            extra_headers=headers,
            extra_body=body,
            **kwargs
        )
