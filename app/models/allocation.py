from datetime import datetime

from app import db


class Allocation(db.Model):
	__tablename__ = "allocations"

	id = db.Column(db.Integer, primary_key=True)
	surplus_id = db.Column(db.Integer, db.ForeignKey("surplus.id"), nullable=False)
	provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	ngo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	status = db.Column(db.String(30), nullable=False, default="requested")
	pickup_time = db.Column(db.DateTime, nullable=True)
	otp_code = db.Column(db.String(6), nullable=True)
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
