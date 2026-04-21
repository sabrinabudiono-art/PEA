from flask import jsonify, request
from models import db, Appliance
from utils import DEFAULT_USER_ID, _safe_float
from services.chat_service import client


def register(app):
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
