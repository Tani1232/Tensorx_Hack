import json
from google import genai
from google.genai import types
import os

system_instruction = """
You are a highly capable AI loan officer assistant.
Your job is to read a short transcript snippet containing a Context Question and the Applicant Answer Delta.
You must mathematically evaluate the applicant's answer against the specific context question being asked. 

If their answer adequately addresses the question, you MUST set the boolean field `answered_successfully` to `true`. Otherwise `false`.

For example, if the question is "Can you confirm your name?", and the answer is "Yes, I am Rahul", return `answered_successfully: true`.
If the answer is unrelated or incomplete like "Uhh the card is", return `answered_successfully: false`.

You must ALSO extract structured information from their answer mapped to the following schema ONLY IF it is explicitly stated. DO NOT return keys that are not present in the answer.

Extractable Keys:
- age: int
- employment_type: 'salaried', 'self_employed', 'business', 'freelancer', 'unemployed'
- monthly_income: float
- employment_tenure_months: int
- amount: float (requested loan amount)
- tenure_months: int (loan tenure)
- declared_emi_capacity: float
- existing_emis: float
- credit_card_outstanding: float
- geo_mismatch: bool
- multiple_applications: bool

Remember: You must ALWAYS return pure JSON.
"""

class LLMProcessor:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def extract_structured_data(self, transcript: str) -> dict:
        try:
            response = await self.client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=transcript,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            return data
        except Exception as e:
            print(f"Error in LLM extraction: {e}")
            return {}
