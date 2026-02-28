from app import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    phone_verified = db.Column(db.Boolean, nullable=False, default=False)

    provided_events = db.relationship("Event", backref="provider", lazy=True)
    provided_surplus = db.relationship("Surplus", foreign_keys="Surplus.provider_id", backref="provider", lazy=True)
    ngo_allocations = db.relationship("Allocation", foreign_keys="Allocation.ngo_id", backref="ngo", lazy=True)
    provider_allocations = db.relationship("Allocation", foreign_keys="Allocation.provider_id", backref="allocation_provider", lazy=True)
    given_reviews = db.relationship("Review", foreign_keys="Review.ngo_id", backref="ngo_reviewer", lazy=True)
    received_reviews = db.relationship("Review", foreign_keys="Review.provider_id", backref="reviewed_provider", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)