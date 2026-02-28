import os
import re

from werkzeug.security import generate_password_hash

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for

from app import db
from app import limiter
from app.models.user import User
from app.services.realtime_service import publish_platform_update
from app.utils.otp_generator import generate_otp, hash_otp, is_otp_expired, otp_expiry, send_otp_email, verify_hashed_otp

auth = Blueprint("auth", __name__)

REGISTER_OTP_SESSION_KEY = "register_otp_context"
FORGOT_OTP_SESSION_KEY = "forgot_otp_context"
OTP_MAX_ATTEMPTS = 5


def _mask_email(email: str) -> str:
    value = (email or "").strip()
    if "@" not in value:
        return value
    name, domain = value.split("@", 1)
    if len(name) <= 2:
        hidden = "*" * len(name)
    else:
        hidden = f"{name[0]}{'*' * (len(name) - 2)}{name[-1]}"
    return f"{hidden}@{domain}"


def _build_otp_context(email: str, **extra):
    otp = generate_otp(6)
    payload = {
        **extra,
        "email": (email or "").strip().lower(),
        "otp_hash": hash_otp(otp, email, current_app.config.get("SECRET_KEY", "")),
        "expires_at": otp_expiry(minutes=10),
        "attempts": 0,
    }
    return otp, payload


def _is_valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", (email or "").strip()))


def _is_valid_password(password: str) -> bool:
    value = password or ""
    if len(value) < 8:
        return False
    has_letter = any(ch.isalpha() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    return has_letter and has_digit


def _is_valid_phone(phone_number: str) -> bool:
    value = (phone_number or "").strip()
    return bool(re.fullmatch(r"[0-9]{10}", value))


@auth.route("/")
def landing():
    return render_template("landing.html")


@auth.route("/register", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def register():
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone_number = (request.form.get("phone_number") or "").strip()
        password = request.form.get("password")
        role = request.form.get("role")

        if role not in {"provider", "ngo"}:
            flash("Invalid role selected.", "error")
            return redirect(url_for("auth.register"))

        if not full_name or not email or not password or not phone_number:
            flash("Please fill all required fields.", "warning")
            return redirect(url_for("auth.register"))

        if not _is_valid_email(email):
            flash("Enter a valid email address.", "warning")
            return redirect(url_for("auth.register"))

        if not _is_valid_password(password):
            flash("Password must be at least 8 characters and contain letters and numbers.", "warning")
            return redirect(url_for("auth.register"))

        if not _is_valid_phone(phone_number):
            flash("Enter a valid 10-digit phone number.", "warning")
            return redirect(url_for("auth.register"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered.", "warning")
            return redirect(url_for("auth.register"))

        existing_phone = User.query.filter_by(phone_number=phone_number).first()
        if existing_phone:
            flash("Phone number already registered.", "warning")
            return redirect(url_for("auth.register"))

        otp, otp_context = _build_otp_context(
            email=email,
            full_name=full_name,
            phone_number=phone_number,
            role=role,
            password_hash=generate_password_hash(password),
        )

        sent = send_otp_email(current_app, email, otp, "registration")
        if not sent:
            flash("Unable to send OTP email right now. Please check SMTP settings and try again.", "error")
            return redirect(url_for("auth.register"))

        session[REGISTER_OTP_SESSION_KEY] = otp_context
        flash("OTP sent to your email. Enter it to complete registration.", "success")
        return redirect(url_for("auth.register_verify_otp"))

    return render_template("register.html")


@auth.route("/register/verify-otp", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def register_verify_otp():
    context = session.get(REGISTER_OTP_SESSION_KEY)
    if not context:
        flash("Registration session not found. Please register again.", "warning")
        return redirect(url_for("auth.register"))

    email = context.get("email", "")

    if request.method == "POST":
        action = (request.form.get("action") or "verify").strip().lower()

        if action == "resend":
            otp, next_context = _build_otp_context(
                email=email,
                full_name=context.get("full_name"),
                phone_number=context.get("phone_number"),
                role=context.get("role"),
                password_hash=context.get("password_hash"),
            )
            sent = send_otp_email(current_app, email, otp, "registration")
            if not sent:
                flash("Unable to resend OTP email right now.", "error")
                return redirect(url_for("auth.register_verify_otp"))

            session[REGISTER_OTP_SESSION_KEY] = next_context
            flash("A new OTP has been sent to your email.", "info")
            return redirect(url_for("auth.register_verify_otp"))

        entered_otp = (request.form.get("otp") or "").strip()
        if not entered_otp:
            flash("Please enter the OTP.", "warning")
            return redirect(url_for("auth.register_verify_otp"))

        if is_otp_expired(context.get("expires_at")):
            session.pop(REGISTER_OTP_SESSION_KEY, None)
            flash("OTP expired. Please register again.", "warning")
            return redirect(url_for("auth.register"))

        if not verify_hashed_otp(context.get("otp_hash"), entered_otp, email, current_app.config.get("SECRET_KEY", "")):
            attempts = int(context.get("attempts", 0)) + 1
            context["attempts"] = attempts
            session[REGISTER_OTP_SESSION_KEY] = context

            if attempts >= OTP_MAX_ATTEMPTS:
                session.pop(REGISTER_OTP_SESSION_KEY, None)
                flash("Too many invalid OTP attempts. Please register again.", "error")
                return redirect(url_for("auth.register"))

            remaining = OTP_MAX_ATTEMPTS - attempts
            flash(f"Invalid OTP. {remaining} attempt(s) remaining.", "error")
            return redirect(url_for("auth.register_verify_otp"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            session.pop(REGISTER_OTP_SESSION_KEY, None)
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("auth.login"))

        phone_number = (context.get("phone_number") or "").strip()
        if not _is_valid_phone(phone_number):
            session.pop(REGISTER_OTP_SESSION_KEY, None)
            flash("Invalid phone number in registration session. Please register again.", "error")
            return redirect(url_for("auth.register"))

        existing_phone = User.query.filter_by(phone_number=phone_number).first()
        if existing_phone:
            session.pop(REGISTER_OTP_SESSION_KEY, None)
            flash("Phone number already registered. Please login.", "warning")
            return redirect(url_for("auth.login"))

        user = User(
            full_name=context.get("full_name") or "",
            email=email,
            phone_number=phone_number,
            phone_verified=True,
            role=context.get("role") or "ngo",
        )
        user.password_hash = context.get("password_hash")
        db.session.add(user)
        db.session.commit()
        publish_platform_update(scope="user", action="created", actor_role=user.role)

        session.pop(REGISTER_OTP_SESSION_KEY, None)
        flash("Registration verified successfully. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("verify_otp.html", purpose="register", masked_email=_mask_email(email))


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier") or request.form.get("email")
        password = request.form.get("password")
        identifier = (identifier or "").strip().lower()

        user = User.query.filter_by(email=identifier).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["role"] = user.role

            if user.role == "provider":
                return redirect(url_for("provider.provider_dashboard"))
            if user.role == "ngo":
                return redirect(url_for("ngo.ngo_dashboard"))
            if user.role == "admin":
                return redirect(url_for("admin.admin_dashboard"))

            flash("Invalid account role.", "error")
            return redirect(url_for("auth.login"))

        flash("Username or password is wrong.", "error")

    return render_template("login.html")


@auth.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Email not found.", "error")
            return redirect(url_for("auth.forgot_password"))

        otp, context = _build_otp_context(email=email, user_id=user.id)
        sent = send_otp_email(current_app, email, otp, "password reset")
        if not sent:
            flash("Unable to send OTP email right now. Please try again later.", "error")
            return redirect(url_for("auth.forgot_password"))

        session.pop("reset_user_id", None)
        session.pop("reset_verified", None)
        session[FORGOT_OTP_SESSION_KEY] = context

        flash("OTP sent to your email. Verify it to continue password reset.", "success")
        return redirect(url_for("auth.forgot_password_verify_otp"))

    return render_template("forgot_password.html")


@auth.route("/forgot-password/verify-otp", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def forgot_password_verify_otp():
    context = session.get(FORGOT_OTP_SESSION_KEY)
    if not context:
        flash("Password reset session not found. Start again.", "warning")
        return redirect(url_for("auth.forgot_password"))

    email = context.get("email", "")

    if request.method == "POST":
        action = (request.form.get("action") or "verify").strip().lower()

        if action == "resend":
            otp, next_context = _build_otp_context(email=email, user_id=context.get("user_id"))
            sent = send_otp_email(current_app, email, otp, "password reset")
            if not sent:
                flash("Unable to resend OTP email right now.", "error")
                return redirect(url_for("auth.forgot_password_verify_otp"))

            session[FORGOT_OTP_SESSION_KEY] = next_context
            flash("A new OTP has been sent to your email.", "info")
            return redirect(url_for("auth.forgot_password_verify_otp"))

        entered_otp = (request.form.get("otp") or "").strip()
        if not entered_otp:
            flash("Please enter the OTP.", "warning")
            return redirect(url_for("auth.forgot_password_verify_otp"))

        if is_otp_expired(context.get("expires_at")):
            session.pop(FORGOT_OTP_SESSION_KEY, None)
            flash("OTP expired. Please restart forgot password.", "warning")
            return redirect(url_for("auth.forgot_password"))

        if not verify_hashed_otp(context.get("otp_hash"), entered_otp, email, current_app.config.get("SECRET_KEY", "")):
            attempts = int(context.get("attempts", 0)) + 1
            context["attempts"] = attempts
            session[FORGOT_OTP_SESSION_KEY] = context

            if attempts >= OTP_MAX_ATTEMPTS:
                session.pop(FORGOT_OTP_SESSION_KEY, None)
                flash("Too many invalid OTP attempts. Please restart forgot password.", "error")
                return redirect(url_for("auth.forgot_password"))

            remaining = OTP_MAX_ATTEMPTS - attempts
            flash(f"Invalid OTP. {remaining} attempt(s) remaining.", "error")
            return redirect(url_for("auth.forgot_password_verify_otp"))

        session["reset_user_id"] = context.get("user_id")
        session["reset_verified"] = True
        session.pop(FORGOT_OTP_SESSION_KEY, None)
        flash("OTP verified. You can now reset your password.", "success")
        return redirect(url_for("auth.reset_password"))

    return render_template("verify_otp.html", purpose="forgot", masked_email=_mask_email(email))


@auth.route("/reset-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def reset_password():
    if not session.get("reset_user_id") or not session.get("reset_verified"):
        flash("Unauthorized reset attempt.", "error")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.get(session["reset_user_id"])
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not new_password or new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.reset_password"))

        if not _is_valid_password(new_password):
            flash("Password must be at least 8 characters and contain letters and numbers.", "warning")
            return redirect(url_for("auth.reset_password"))

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        session.pop("reset_user_id", None)
        session.pop("reset_verified", None)

        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")


@auth.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))


@auth.route("/media/<path:filename>")
def media_file(filename):
    normalized = (filename or "").replace("\\", "/").lstrip("/")

    primary_root = current_app.static_folder
    if os.path.exists(os.path.join(primary_root, normalized)):
        return send_from_directory(primary_root, normalized)

    legacy_root = os.path.join(current_app.root_path, "routes", "static")
    if os.path.exists(os.path.join(legacy_root, normalized)):
        return send_from_directory(legacy_root, normalized)

    return abort(404)