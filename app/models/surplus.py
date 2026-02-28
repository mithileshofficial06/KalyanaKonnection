from datetime import datetime

from app import db


class Surplus(db.Model):
	__tablename__ = "surplus"

	id = db.Column(db.Integer, primary_key=True)
	provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=True)
	event_name = db.Column(db.String(150), nullable=False)
	provider_name = db.Column(db.String(120), nullable=False)
	food_type = db.Column(db.String(150), nullable=False)
	quantity = db.Column(db.Float, nullable=False)
	quantity_kg = db.Column(db.Float, nullable=False, default=0)
	estimated_expiry = db.Column(db.String(80), nullable=True)
	distance_km = db.Column(db.Float, nullable=True)
	provider_location = db.Column(db.String(180), nullable=True)
	provider_latitude = db.Column(db.Float, nullable=True)
	provider_longitude = db.Column(db.Float, nullable=True)
	photo_path = db.Column(db.String(255), nullable=True)
	status = db.Column(db.String(30), nullable=False, default="available")
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

	allocations = db.relationship("Allocation", backref="surplus", lazy=True)
