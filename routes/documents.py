import os
from flask import jsonify, request
from models import db, EnergyReport, EnergyContract
from utils import DEFAULT_USER_ID, UPLOAD_FOLDER, save_document_to_db, _fields_to_dict
from pdf_processor import extract_text_from_pdf
from pdf_extractor_ai import extract_energy_data


def register(app):
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
