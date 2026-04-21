from flask import jsonify, request
from models import db, MeterReadings
from utils import DEFAULT_USER_ID, _parse_date, _safe_float


def register(app):
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
