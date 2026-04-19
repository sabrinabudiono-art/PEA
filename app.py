"""Flask application exposing the personal energy assistant REST API and UI."""
import os
from datetime import date
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from openai import OpenAI

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
    """Render the single-page dashboard."""
    return render_template('index.html')

def _parse_date(value):
    """Parse an ISO date string, returning ``None`` on missing or invalid input."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None

def _safe_float(value):
    """Coerce a value to float, returning ``None`` if conversion fails."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _fields_to_dict(fields_list):
    """Flatten the ``[{field_name, field_value}, ...]`` AI response into a dict."""
    result = {}
    for field in fields_list:
        name = field.get('field_name', '').lower().replace(' ', '_')
        result[name] = field.get('field_value')
    return result

def save_document_to_db(doc_type, fields_dict, filepath, markdown_text):
    """Persist extracted contract or report fields as the matching ORM record."""
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
    db.session.commit()

    return record

@app.route('/api/reports', methods=['GET'])
def list_reports():
    """Return all energy reports for the default user, newest first."""
    reports = EnergyReport.query.filter_by(user_id=DEFAULT_USER_ID).order_by(EnergyReport.start_date.desc()).all()
    return jsonify({'reports': [
        {
            "id": r.id,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "total_consumption_kwh": r.total_consumption_kwh,
            "total_cost": r.total_cost,
        }
        for r in reports
    ]})

@app.route('/api/reports/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Delete an energy report by id, or return 404 if it does not exist."""
    report = db.session.get(EnergyReport, report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    db.session.delete(report)
    db.session.commit()
    return jsonify({'message': 'Report deleted'}), 200

@app.route('/api/contracts', methods=['GET'])
def list_contracts():
    """Return all energy contracts for the default user, newest first."""
    contracts = EnergyContract.query.filter_by(user_id=DEFAULT_USER_ID).order_by(EnergyContract.start_date.desc()).all()
    return jsonify({'contracts': [
        {
            "id": c.id,
            "provider_name": c.provider_name,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "price_per_kwh": c.price_per_kwh,
            "base_fee": c.base_fee,
        }
        for c in contracts
    ]})

@app.route('/api/contracts/<int:contract_id>', methods=['DELETE'])
def delete_contract(contract_id):
    """Delete an energy contract by id, or return 404 if it does not exist."""
    contract = db.session.get(EnergyContract, contract_id)
    if not contract:
        return jsonify({'error': 'Contract not found'}), 404
    db.session.delete(contract)
    db.session.commit()
    return jsonify({'message': 'Contract deleted'}), 200

@app.route('/api/upload', methods=['POST'])
def upload():
    """Upload a PDF, extract energy fields via AI, and persist the result."""
    if "file" not in request.files:
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

@app.route('/api/chat', methods=['POST'])
def chat():
    """Answer a chatbot question using the user's stored energy context."""
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
    """Delete the full chatbot conversation history for the default user."""
    Chatbot.query.filter_by(user_id=DEFAULT_USER_ID).delete()
    db.session.commit()
    return jsonify({'message': 'Successfully cleared chatbot'}), 200

@app.route('/api/appliances', methods=['GET'])
def list_appliances():
    """Return all appliances registered for the default user."""
    appliances = Appliance.query.filter_by(user_id=DEFAULT_USER_ID).all()
    return jsonify({'appliances': [
        {
            "id": appliance.id,
            "appliance_name": appliance.appliance_name,
            "appliance_type": appliance.appliance_type,
            "monthly_kwh_consumption": appliance.monthly_kwh_consumption,
        }
        for appliance in appliances]
    })

@app.route('/api/appliances', methods=['POST'])
def add_appliance():
    """Create a new appliance record from the JSON request body."""
    body = request.get_json(silent=True) or {}
    name = body.get("appliance_name", "").strip()
    if not name:
        return jsonify({'error': 'No appliance provided'}), 400

    appliance = Appliance(
        user_id=DEFAULT_USER_ID,
        appliance_name=name,
        appliance_type=body.get("appliance_type", "").strip() or None,
        monthly_kwh_consumption=_safe_float(body.get("monthly_kwh_consumption")),
    )
    db.session.add(appliance)
    db.session.commit()

    return jsonify({
        "message": "Appliance added",
        "appliance": {
        "id": appliance.id,
        "appliance_name": appliance.appliance_name,
        "appliance_type": appliance.appliance_type,
        "monthly_kwh_consumption": appliance.monthly_kwh_consumption,
        },
    })

@app.route('/api/appliances/<int:appliance_id>', methods=['PUT'])
def update_appliance(appliance_id):
    """Update an existing appliance's name, type, and monthly consumption."""
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
            "id": appliance.id,
            "appliance_name": appliance.appliance_name,
            "appliance_type": appliance.appliance_type,
            "monthly_kwh_consumption": appliance.monthly_kwh_consumption,
        },
    })

@app.route('/api/appliances/<int:appliance_id>', methods=['DELETE'])
def delete_appliance(appliance_id):
    """Delete an appliance by id, or return 404 if it does not exist."""
    appliance = db.session.get(Appliance, appliance_id)
    if not appliance:
        return jsonify({'error': 'Appliance not found'}), 404
    db.session.delete(appliance)
    db.session.commit()
    return jsonify({'message': 'Appliance deleted'}), 200

@app.route('/api/appliances/chat', methods=['POST'])
def appliance_chat():
    """Ask OpenAI to estimate an appliance's monthly kWh consumption."""
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


@app.route('/api/meter-readings', methods=['GET'])
def read_meter_readings():
    """Return all meter readings for the default user, oldest first."""
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

@app.route('/api/meter-readings', methods=['POST'])
def add_meter_reading():
    """Create a new meter reading from the JSON request body."""
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

@app.route('/api/meter-readings/<int:reading_id>', methods=['PUT'])
def update_meter_reading(reading_id):
    """Update the date and value of an existing meter reading."""
    reading = db.session.get(MeterReadings, reading_id)
    if not reading:
        return jsonify({'error': 'Meter reading not found'}), 404

    body = request.get_json(silent=True) or {}
    new_date = _parse_date(body.get("reading_date"))
    new_value = _safe_float(body.get("reading_value"))

    if not new_date:
        return jsonify({'error': 'Valid date required'}), 400
    if new_value is None:
        return jsonify({'error': 'Valid value required'}), 400

    reading.reading_date = new_date
    reading.reading_value = new_value
    db.session.commit()

    return jsonify({
        "message": "Meter reading updated",
        "reading": {
            "id": reading.id,
            "reading_date": reading.reading_date.isoformat(),
            "reading_value": reading.reading_value,
        },
    })

@app.route('/api/meter-readings/<int:reading_id>', methods=['DELETE'])
def delete_meter_reading(reading_id):
    """Delete a meter reading by id, or return 404 if it does not exist."""
    reading = db.session.get(MeterReadings, reading_id)
    if not reading:
        return jsonify({'error': 'Meter reading not found'}), 404
    db.session.delete(reading)
    db.session.commit()
    return jsonify({'message': 'Meter reading deleted'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)