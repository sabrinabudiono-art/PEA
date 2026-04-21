from flask import jsonify, request
from models import db, Chatbot
from utils import DEFAULT_USER_ID
from services.chat_service import chat_with_ai


def register(app):
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
