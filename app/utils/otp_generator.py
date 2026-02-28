import hashlib
import hmac
import os
import random
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage


def generate_otp(length: int = 6) -> str:
	digits = "0123456789"
	return "".join(random.SystemRandom().choice(digits) for _ in range(length))


def otp_expiry(minutes: int = 10) -> str:
	return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def is_otp_expired(expires_at_iso: str) -> bool:
	if not expires_at_iso:
		return True
	try:
		expires_at = datetime.fromisoformat(expires_at_iso)
	except ValueError:
		return True
	if expires_at.tzinfo is None:
		expires_at = expires_at.replace(tzinfo=timezone.utc)
	return datetime.now(timezone.utc) >= expires_at


def _otp_key(secret_key: str) -> bytes:
	source = (secret_key or os.getenv("SECRET_KEY") or "kalyana-otp-fallback-key").encode("utf-8")
	return hashlib.sha256(source).digest()


def hash_otp(otp: str, email: str, secret_key: str) -> str:
	payload = f"{(email or '').strip().lower()}:{(otp or '').strip()}".encode("utf-8")
	return hmac.new(_otp_key(secret_key), payload, hashlib.sha256).hexdigest()


def verify_hashed_otp(stored_hash: str, entered_otp: str, email: str, secret_key: str) -> bool:
	if not stored_hash or not entered_otp:
		return False
	candidate = hash_otp(entered_otp, email, secret_key)
	return hmac.compare_digest(stored_hash, candidate)


def send_otp_email(app, recipient_email: str, otp: str, purpose: str) -> bool:
	host = app.config.get("SMTP_HOST", "")
	port = int(app.config.get("SMTP_PORT", 587) or 587)
	username = app.config.get("SMTP_USER", "")
	password = app.config.get("SMTP_PASSWORD", "")
	from_email = app.config.get("SMTP_FROM_EMAIL", username)
	use_tls = str(app.config.get("SMTP_USE_TLS", "true")).lower() == "true"

	if not host or not from_email:
		app.logger.warning("OTP email skipped because SMTP is not configured for recipient=%s", recipient_email)
		return False

	message = EmailMessage()
	message["Subject"] = f"Kalyana Connection OTP for {purpose}"
	message["From"] = from_email
	message["To"] = recipient_email
	message.set_content(
		"\n".join(
			[
				"Hello,",
				"",
				f"Your OTP for {purpose} is: {otp}",
				"This OTP is valid for 10 minutes.",
				"",
				"If you did not request this, please ignore this email.",
				"",
				"- Kalyana Connection",
			]
		)
	)

	try:
		with smtplib.SMTP(host, port, timeout=15) as server:
			if use_tls:
				server.starttls()
			if username and password:
				server.login(username, password)
			server.send_message(message)
		return True
	except Exception as exc:
		app.logger.error("Failed to send OTP email to %s: %s", recipient_email, exc)
		return False
