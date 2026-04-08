from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(80), nullable=False)


class EnergyReport(db.Model):
    __tablename__ = 'energy_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_consumption_kwh = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)


class EnergyContract(db.Model):
    __tablename__ = 'energy_contracts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_name = db.Column(db.String(200))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    price_per_kwh = db.Column(db.Float)
    base_fee = db.Column(db.Float)


class Appliance(db.Model):
    __tablename__ = 'appliances'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appliance_name = db.Column(db.String(200), nullable=False)
    appliance_type = db.Column(db.String(100))
    monthly_kwh_consumption = db.Column(db.Float, nullable=False)


class MeterReadings(db.Model):
    __tablename__ = 'meter_readings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reading_date = db.Column(db.Date, nullable=False)
    reading_value = db.Column(db.Float, nullable=False)


class Chatbot(db.Model):
    __tablename__ = 'chatbot'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
