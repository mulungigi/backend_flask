from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime

db = SQLAlchemy()

class Rates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    base = db.Column(db.String(10), nullable=False)
    rates = db.Column(JSON, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
