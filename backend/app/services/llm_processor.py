import json
from google import genai
from google.genai import types
import os

system_instruction = """
You are a highly capable AI loan officer assistant.
Your job is to read a short transcript snippet containing a Context Question and the Applicant Answer Delta.
The applicant is encouraged to give brief, often 1-word answers.
You must mathematically evaluate the applicant's answer against the specific context question being asked. 

If their answer adequately addresses the question (even if it is just a single word or number), you MUST set the boolean field `answered_successfully` to `true`. Otherwise `false`.

For example:
- Question: "Confirm your name?", Answer: "Rahul" -> `answered_successfully: true`
- Question: "Monthly income?", Answer: "50000" -> `answered_successfully: true`
- Question: "Consent?", Answer: "Yes" -> `answered_successfully: true`
- Question: "Uhh...", Answer: "Maybe" -> `answered_successfully: false` (if ambiguous)

You must ALSO extract structured information from their answer mapped to the following schema ONLY IF it is explicitly stated or clearly implied by the context. DO NOT return keys that are not present in the answer.

Extractable Keys:
- full_name: string
- consent_video_recording: bool
- consent_bureau_pull: bool
- age: int
- employment_type: 'salaried', 'self_employed', 'business', 'freelancer', 'unemployed'
- monthly_income: float
- employment_tenure_months: int
- cibil_score: int
- credit_utilization: float (percentage)
- credit_history_months: int
- dpd_90_plus_count: int (number of late payments/defaults)
- amount: float (requested loan amount)
- tenure_months: int (loan tenure)
- declared_emi_capacity: float
- existing_emis: float
- credit_card_outstanding: float
- geo_mismatch: bool
- multiple_applications: bool

If the answer provides credit history in years, convert to months (years * 12).
If the answer provides date of birth instead of numeric age, compute age in years and return `age` as an integer.

Remember: You must ALWAYS return pure JSON.
"""

class LLMProcessor:
    def __init__(self, api_key: str):
        try:
            if not api_key:
                raise ValueError("GEMINI_API_KEY is empty")
            self.client = genai.Client(api_key=api_key)
            print("[LLMProcessor] Gemini client initialised successfully.")
        except Exception as e:
            print(f"[LLMProcessor] WARNING: Could not initialise Gemini client — {e}. LLM extraction will be disabled.")
            self.client = None

    async def extract_structured_data(self, transcript: str) -> dict:
        if self.client is None:
            return {}
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
