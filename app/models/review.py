from datetime import datetime

from app import db


class Review(db.Model):
	__tablename__ = "reviews"

	id = db.Column(db.Integer, primary_key=True)
	ngo_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	provider_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	rating = db.Column(db.Integer, nullable=False)
	comment = db.Column(db.Text, nullable=False)
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
