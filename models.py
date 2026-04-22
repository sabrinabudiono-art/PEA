"""SQLAlchemy ORM models for the personal energy assistant application."""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """Application user with credentials for authentication."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(80), nullable=False)


class EnergyReport(db.Model):
    """Energy consumption report (bill/invoice) for a billing period."""
    __tablename__ = 'energy_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_consumption_kwh = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)


class EnergyContract(db.Model):
    """Energy supply contract with provider pricing details."""
    __tablename__ = 'energy_contracts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_name = db.Column(db.String(200))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    price_per_kwh = db.Column(db.Float)
    base_fee = db.Column(db.Float)


class Appliance(db.Model):
    """Household appliance with estimated monthly kWh consumption."""
    __tablename__ = 'appliances'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appliance_name = db.Column(db.String(200), nullable=False)
    appliance_type = db.Column(db.String(100))
    monthly_kwh_consumption = db.Column(db.Float, nullable=False)


class MeterReadings(db.Model):
    """Point-in-time meter reading recorded by the user."""
    __tablename__ = 'meter_readings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reading_date = db.Column(db.Date, nullable=False)
    reading_value = db.Column(db.Float, nullable=False)


class DocumentChunk(db.Model):
    """Chunk of document text with its embedding vector for RAG retrieval."""
    __tablename__ = 'document_chunks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    source_type = db.Column(db.String(20), nullable=False)
    source_id = db.Column(db.Integer, nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Chatbot(db.Model):
    """Persisted chat message exchanged between the user and the assistant."""
    __tablename__ = 'chatbot'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
