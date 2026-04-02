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