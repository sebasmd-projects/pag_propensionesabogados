#  apps/project/api/platform/insolvency_form/functions/chatgpt_api.py

from django.conf import settings
from openai import OpenAI


class ChatGPTAPI:
    def __init__(self):
        self.client = OpenAI(api_key=settings.CHAT_GPT_API_KEY)

    def get_response(self, model, messages, temperature=0):
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        polished = response.choices[0].message.content.strip()
        return polished

    def get_response_json(self, model, messages, temperature=0):
        response = self.client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
            response_format={"type": "json_object"}
        )
        polished = response.choices[0].message.content.strip()
        return polished
