from datetime import datetime

from app import db


class Complaint(db.Model):
	__tablename__ = "complaints"

	id = db.Column(db.Integer, primary_key=True)
	ngo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
	issue_type = db.Column(db.String(80), nullable=False)
	description = db.Column(db.Text, nullable=False)
	status = db.Column(db.String(30), nullable=False, default="Under Review")
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

	ngo_user = db.relationship("User", foreign_keys=[ngo_id], lazy="joined")
	provider_user = db.relationship("User", foreign_keys=[provider_id], lazy="joined")
