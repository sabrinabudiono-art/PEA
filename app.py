import os
from datetime import date
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.sql.functions import current_user

from models import (db, User, EnergyReport, EnergyContract, Appliance, MeterReadings, Chatbot)

from pdf_processor import extract_text_from_pdf
from pdf_extractor_ai import extract_energy_data
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

DEFAULT_USER_ID = 1
DEFAULT_USER_NAME = 'admin'
DEFAULT_USER_EMAIL = 'admin@admin.com'

@app.route('/')
def index():
    return render_template('index.html')

def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None

def _safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _fields_to_dict(fields_list):
    result = {}
    for field in fields_list:
        name = field.get('field_name', '').lower().replace(' ', '_')
        result[name] = field.get('field_value')
    return result

def save_document_to_db(doc_type, fields_dict, filepath, markdown_text):
    if doc_type == 'contract':
        record = EnergyContract(
            user_id=DEFAULT_USER_ID,
            provider_name=fields_dict.get('provider_name'),
            start_date=_parse_date(fields_dict.get('start_date')),
            end_date=_parse_date(fields_dict.get('end_date')),
            price_per_kwh=_safe_float(fields_dict.get('price_per_kwh')),
            base_fee=_safe_float(fields_dict.get('base_fee')),
        )
    else:
        record = EnergyReport(
            user_id=DEFAULT_USER_ID,
            start_date=_parse_date(fields_dict.get('start_date')),
            end_date=_parse_date(fields_dict.get('end_date')),
            total_consumption_kwh=_safe_float(fields_dict.get('total_consumption_kwh')),
            total_cost=_safe_float(fields_dict.get('total_cost')),
        )

    db.session.add(record)
    db.session.flush()

    return record

@app.route('/api/upload', methods=['POST'])
def upload():
    if "file" not in request.files["file"]:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files["file"]
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not(file.filename.endswith('.pdf')):
        return jsonify({'error': 'Only pdf filename are allowed'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        markdown_text = extract_text_from_pdf(filepath)

        if not markdown_text.strip():
            os.remove(filepath)
            return jsonify({'error': 'Could not extract text'}), 400

        result = extract_energy_data(markdown_text)
        doc_type = result.get('doc_type', 'report')
        fields_list = result.get('fields', [])
        fields_dict = _fields_to_dict(fields_list)

        record = save_document_to_db(doc_type, fields_dict, filepath, markdown_text)

        return jsonify({
            "message": "Document successfully uploaded",
            "doc_type": doc_type,
            "extracted": fields_dict,
            "fields": fields_list,
            "id": record.id,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def build_chat_context():
    lines = []

    reports = EnergyReport.query.filter_by(user_id=DEFAULT_USER_ID).all()
    if reports:
        lines.append("Energy Reports")
        for report in reports:
            lines.append(
                f" {report.start_date.strftime('%Y-%m-%d')} - {report.end_date.strftime('%Y-%m-%d')}"
                f" {report.total_consumption_kwh} kWh, {report.total_cost} Euro."
            )

    contracts = EnergyContract.query.filter_by(user_id=DEFAULT_USER_ID).all()
    if contracts:
        lines.append("Energy Contracts")
        for contract in contracts:
            lines.append(
                f"{contract.provider_name}"
                f"{contract.start_date.strftime('%Y-%m-%d')} - {contract.end_date.strftime('%Y-%m-%d')}"
                f"{contract.price_per_kwh}Euro/kWh, base fee {contract.base_fee_kwh} Euro."
            )

    appliances = Appliance.query.filter_by(user_id=DEFAULT_USER_ID).all()
    if appliances:
        lines.append("Appliances")
        for appliance in appliances:
            lines.append(
                f"{appliance.appliance.provider_name} ({appliance.appliance_type}):"
                f"{appliance.monthly_kwh_consumption} kWh/month."
            )

    readings = MeterReadings.query.filter_by(user_id=DEFAULT_USER_ID).order_by(MeterReadings.reading_date).all()
    if readings:
        lines.append("Meter Readings")
        for reading in readings:
            lines.append(
                f"{reading.reading_date.strftime('%Y-%m-%d')}: {reading.reading_value} kWh.."
            )

def chat_with_ai(user_message):
    db.session.add(Chatbot(
        user_id=DEFAULT_USER_ID, role="user", message=user_message))
    db.session.commit()

    context = build_chat_context()
    history = (
        Chatbot.query.filter_by(user_id=DEFAULT_USER_ID).order_by(Chatbot.created_at).desc().limit(20).all()
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

@app.route('/api/chat', methods=['POST'])
def chat():
    body = request.get_json(silent=True) or {}
    question = body.get("question", "").strip()

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    try:
        answer = chat_with_ai(question)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/chatbot/clear', methods=['DELETE'])
def chatbot_clear():
    Chatbot.query.filter_by(user_id=DEFAULT_USER_ID).delete()
    db.session.commit()
    return jsonify({'message': 'Successfully cleared chatbot'}), 200

@app.route('/api/appliances', methods=['POST'])
def list_appliances():
    appliances = Appliance.query.filter_by(user_id=DEFAULT_USER_ID).all()
    return jsonify({'appliances': [
        {
            "id": appliance.appliance_id,
            "appliance_name": appliance.appliance_name,
            "appliance_type": appliance.appliance_type,
            "monthly_kwh_consumption": appliance.monthly_kwh_consumption,
        }
        for appliance in appliances]
    })

def add_appliance():
    body = request.get_json(silent=True) or {}
    name = body.get("appliance_name", "").strip()
    if not name:
        return jsonify({'error': 'No appliance provided'}), 400

    appliance = Appliance(
        user_id=DEFAULT_USER_ID,
        appliance_name=name,
        appliance_type=body.get("appliance_type", "").strip() or None,
        monthly_kwh_consumption=_safe_float(body.get("C")),
    )
    db.session.add(appliance)
    db.session.commit()

    return jsonify({
        "message": "Appliance added",
        "appliance": {
        "id": appliance.appliance_id,
        "appliance_name": appliance.appliance_name,
        "appliance_type": appliance.appliance_type,
        "monthly_kwh_consumption": appliance.monthly_kwh_consumption,
        },
    })

@app.route('/api/appliances/<int:appliance_id>', methods=['PUT'])
def update_appliance(appliance_id):
    appliance = db.session.get(Appliance, appliance_id)
    if not appliance:
        return jsonify({'error': 'Appliance not found'}), 404

    body = request.get_json(silent=True) or {}
    name = body.get("appliance_name", "").strip()
    if not name:
        return jsonify({'error': 'No appliance name provided'}), 400

    appliance.appliance_name = name
    appliance.appliance_type = body.get("appliance_type", "").strip() or None
    appliance.monthly_kwh_consumption = _safe_float(body.get("monthly_kwh_consumption"))
    db.session.commit()

    return jsonify({
        "message": "Appliance updated",
        "appliance": {
            "id": appliance.appliance_id,
            "appliance_name": appliance.appliance_name,
            "appliance_type": appliance.appliance_type,
            "monthly_kwh_consumption": appliance.monthly_kwh_consumption,
        },
    })

@app.route('/api/appliances/<int:appliance_id>', methods=['DELETE'])
def delete_appliance(appliance_id):
    appliance = db.session.get(Appliance, appliance_id)
    if not appliance:
        return jsonify({'error': 'Appliance not found'}), 404
    db.session.delete(appliance)
    db.session.commit()
    return jsonify({'message': 'Appliance deleted'}), 200

@app.route('/api/appliances/chat', methods=['POST'])
def chat_with_ai():
    body = request.get_json(silent=True) or {}
    question = body.get("question", "").strip()
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system",
                 "content": (
                     "You are an energy consumption advisor. Users will ask you about a specific household appliance"
                     "(often by brand or model) and their usage patterns. Your job is to estimate the monthly "
                     "electricity consumption in kWh. Always provide a single estimated number in kWh/month along with"
                     "a brief explanation of how you arrived at that number. If you dont know the exact specs, use"
                     "reasonable estimates based on similar appliance and tell this to the user. Round to one decimal place."
                    ),
                 },
                {"role": "user", "content": question},
            ],
            temperature=0.5,
        )
        answer = response.choices[0].message.content
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('api/meter-readings', methods=['POST'])
def read_meter_readings():
    readings = (
        MeterReadings.query.filter_by(user_id=DEFAULT_USER_ID).order_by(MeterReadings.reading_date.asc()).all()
    )

    return jsonify({
        "readings": [
            {
                "id": reading.id,
                "reading_date": reading.reading_date,
                "reading_value": reading.reading_value,
            }
            for reading in readings
        ]
    })

def add_meter_reading():
    body = request.get_json(silent=True) or {}
    reading_date = _parse_date(body.get("reading_date"))
    reading_value = _safe_float(body.get("reading_value"))

    if not reading_date:
        return jsonify({'error': 'Valid date required'}), 400
    if not reading_value:
        return jsonify({'error': 'Valid value required'}), 400

    reading = MeterReadings(
        user_id=DEFAULT_USER_ID,
        reading_date=reading_date,
        reading_value=reading_value,
    )
    db.session.add(reading)
    db.session.commit()

    return jsonify({
        "message": "Meter reading added",
        "reading": {
            "id": reading.id,
            "reading_date": reading.reading_date,
            "reading_value": reading.reading_value,
        },
    })

@app.route('/api/meter-readings/<int:reading_id>', methods=['DELETE'])
def delete_meter_reading(reading_id):
    reading = db.session.get(MeterReadings, reading_id)
    if not reading:
        return jsonify({'error': 'Meter reading not found'}), 404
    db.session.delete(reading)
    db.session.commit()
    return jsonify({'message': 'Meter reading deleted'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
