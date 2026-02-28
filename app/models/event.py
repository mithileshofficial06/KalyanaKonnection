from datetime import datetime

from app import db


class Event(db.Model):
	__tablename__ = "events"

	id = db.Column(db.Integer, primary_key=True)
	provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	event_name = db.Column(db.String(150), nullable=False)
	event_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
	guest_count = db.Column(db.Integer, nullable=False, default=0)
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

	surplus_batches = db.relationship("Surplus", backref="event", lazy=True)
