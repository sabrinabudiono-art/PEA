import os
from datetime import date
from models import db, EnergyContract, EnergyReport

DEFAULT_USER_ID = 1
DEFAULT_USER_NAME = 'admin'
DEFAULT_USER_EMAIL = 'admin@admin.com'

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
