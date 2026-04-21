"""Flask application exposing the personal energy assistant REST API and UI."""
import os
from flask import Flask, render_template
from dotenv import load_dotenv

from models import db

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Render the single-page dashboard."""
    return render_template('index.html')

from routes import documents, appliances, meter_readings, chat
documents.register(app)
appliances.register(app)
meter_readings.register(app)
chat.register(app)

if __name__ == '__main__':
    app.run(debug=True, port=5000)