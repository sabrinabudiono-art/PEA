"""OpenAI-backed extraction of structured energy fields from document text."""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are an expert energy data extractor. The text content of an energy document (contract/report) will be provided.

Your job:
1. Determine document type: "contract" (Vertrag) or "report" (Rechnung/Invoice/Bill)
2. Extract the relevant fields:

If "doc_type" = "contract":
"provider_name" = string or null
"start_date" = YYYY-MM-DD or null
"end_date" = YYYY-MM-DD or null
"price_per_kwh" = number(in EUR, e.g 0.30) or null
"base_fee" = number(monthly base fee in EUR) or null

If "doc_type" = "report":
"start_date" = YYYY-MM-DD or null
"end_date" = YYYY-MM-DD or null
"total_consumption_kwh" = number(total kWh consumed in the period) or null
"total_cost" = number(This is the total electricity cost/Stromkosten before any deductions, bonuses, credits of paymentsin EUR) or null

IMPORTANT rules: 
Numbers must be plain without currency symbols and converted to german number format (e.g. 1.283,00 is 1283.00), dates must be in YYYY-MM-DD format.

Return the answer as valid JSON with this exact structure:
{
    "doc_type":"contract" or "report",
    "fields": [
        {
        "field_name": "the exact field name from the list above",
        "field_value": "the extracted value as described above"
        }
    ]
}
"""

def extract_energy_data(markdown_text: str) -> dict:
    """Classify an energy document and extract its structured fields via OpenAI.

    :param markdown_text: Markdown text extracted from a PDF contract or bill.
    :return: dict containing the detected ``doc_type`` and a list of ``fields``.
    :raises ValueError: if the model response cannot be parsed as JSON.
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Here ist the text: {markdown_text}"},
        ],
        temperature = 0,
        max_tokens = 1000,
    )

    raw_answer = response.choices[0].message.content.strip()

    try:
        result = json.loads(raw_answer)
    except json.decoder.JSONDecodeError as e:
        raise ValueError("Could not parse OpenAI response")

    return result