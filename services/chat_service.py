import os
from openai import OpenAI
from models import db, EnergyReport, EnergyContract, Appliance, MeterReadings, Chatbot
from utils import DEFAULT_USER_ID

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def build_chat_context():
    """Render the user's stored energy data as plain text for the chatbot prompt."""
    lines = []

    def fmt_date(d):
        """Format a date as YYYY-MM-DD, or ``'N/A'`` when missing."""
        return d.strftime('%Y-%m-%d') if d else 'N/A'

    reports = EnergyReport.query.filter_by(user_id=DEFAULT_USER_ID).all()
    if reports:
        lines.append("Energy Reports")
        for report in reports:
            lines.append(
                f" {fmt_date(report.start_date)} - {fmt_date(report.end_date)}"
                f" {report.total_consumption_kwh} kWh, {report.total_cost} Euro."
            )

    contracts = EnergyContract.query.filter_by(user_id=DEFAULT_USER_ID).all()
    if contracts:
        lines.append("Energy Contracts")
        for contract in contracts:
            lines.append(
                f"{contract.provider_name or 'Unknown'} "
                f"{fmt_date(contract.start_date)} - {fmt_date(contract.end_date)} "
                f"{contract.price_per_kwh} Euro/kWh, base fee {contract.base_fee} Euro."
            )

    appliances = Appliance.query.filter_by(user_id=DEFAULT_USER_ID).all()
    if appliances:
        lines.append("Appliances")
        for appliance in appliances:
            lines.append(
                f"{appliance.appliance_name} ({appliance.appliance_type}): "
                f"{appliance.monthly_kwh_consumption} kWh/month."
            )

    readings = MeterReadings.query.filter_by(user_id=DEFAULT_USER_ID).order_by(MeterReadings.reading_date).all()
    if readings:
        lines.append("Meter Readings")
        for reading in readings:
            lines.append(
                f"{fmt_date(reading.reading_date)}: {reading.reading_value} kWh."
            )

    return "\n".join(lines)

def chat_with_ai(user_message):
    """Persist the user message, query OpenAI with recent history, and store the reply."""
    db.session.add(Chatbot(
        user_id=DEFAULT_USER_ID, role="user", message=user_message))
    db.session.commit()

    context = build_chat_context()
    history = (
        Chatbot.query.filter_by(user_id=DEFAULT_USER_ID).order_by(Chatbot.created_at.desc()).limit(20).all()
    )
    history.reverse()

    messages = [
        {
            "role": "system",
            "content": "You are a friendly and professional personal energy assistant. Help the user understand"
                       "their energy usage, suggest ways to save energy, and answer questions about their uploaded data."
                       f"Here is the data: {context}"
                       "when giving energy-saving tips, be specific and practical."
        }
    ]

    for msg in history:
        messages.append({"role": msg.role, "content": msg.message})

    response = client.chat.completions.create(model="gpt-4.1-mini", messages=messages, temperature=0.5)

    answer = response.choices[0].message.content

    db.session.add(Chatbot(
        user_id=DEFAULT_USER_ID, role="assistant", message=answer
    ))
    db.session.commit()

    return answer
