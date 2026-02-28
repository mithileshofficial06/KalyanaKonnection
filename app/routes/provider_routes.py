import os
from datetime import datetime
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app import db
from app.models.allocation import Allocation
from app.models.complaint import Complaint
from app.models.event import Event
from app.models.review import Review
from app.models.surplus import Surplus
from app.models.user import User
from app.services.maps_service import geocode_place
from app.services.realtime_service import publish_platform_update
from app.utils.decorators import role_required

provider = Blueprint("provider", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def _is_allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _provider_id_from_session():
    try:
        return int(session.get("user_id"))
    except (TypeError, ValueError):
        return None


@provider.route("/provider/dashboard")
@role_required("provider")
def provider_dashboard():
    provider_id = _provider_id_from_session()

    total_events = Event.query.filter_by(provider_id=provider_id).count()
    total_food_donated = db.session.query(func.coalesce(func.sum(func.coalesce(Surplus.quantity, Surplus.quantity_kg)), 0.0)).filter_by(provider_id=provider_id).scalar()
    active_allocations = Allocation.query.filter(
        Allocation.provider_id == provider_id,
        Allocation.status.in_(["requested", "allocated"]),
    ).count()
    average_rating = db.session.query(func.avg(Review.rating)).filter_by(provider_id=provider_id).scalar() or 0

    recent_allocations = (
        Allocation.query.filter_by(provider_id=provider_id)
        .order_by(Allocation.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "provider/dashboard.html",
        total_events=total_events,
        total_food_donated=round(float(total_food_donated or 0), 1),
        active_allocations=active_allocations,
        average_rating=round(float(average_rating), 2),
        recent_allocations=recent_allocations,
    )


@provider.route("/provider/add-surplus", methods=["GET", "POST"])
@role_required("provider")
def provider_add_surplus():
    provider_id = _provider_id_from_session()
    current_provider = User.query.get(provider_id)

    if request.method == "POST":
        event_name = request.form.get("event_name", "").strip()
        mahal_name = request.form.get("mahal_name", "").strip()
        provider_name = request.form.get("provider_name", "").strip() or (current_provider.full_name if current_provider else "Provider")
        food_type = request.form.get("food_type", "").strip()
        estimated_expiry = request.form.get("estimated_expiry", "").strip()
        quantity_text = request.form.get("quantity_kg", "").strip()
        distance_text = request.form.get("distance_km", "").strip()
        mahal_location = request.form.get("mahal_location", "").strip()
        photo_file = request.files.get("food_photo")

        if not event_name or not mahal_name or not food_type or not quantity_text or not mahal_location:
            flash("Please fill event name, mahal name, food type, quantity, and mahal location.", "warning")
            return redirect(url_for("provider.provider_add_surplus"))

        geo = geocode_place(mahal_location)
        if not geo:
            flash("Unable to detect this mahal location. Please use a valid place name.", "error")
            return redirect(url_for("provider.provider_add_surplus"))

        try:
            quantity_kg = float(quantity_text)
        except ValueError:
            flash("Quantity must be a valid number.", "error")
            return redirect(url_for("provider.provider_add_surplus"))

        distance_km = None
        if distance_text:
            try:
                distance_km = float(distance_text)
            except ValueError:
                flash("Distance must be a valid number.", "error")
                return redirect(url_for("provider.provider_add_surplus"))

        saved_photo_path = None
        if photo_file and photo_file.filename:
            if not _is_allowed_image(photo_file.filename):
                flash("Only PNG, JPG, JPEG, WEBP images are allowed.", "error")
                return redirect(url_for("provider.provider_add_surplus"))

            original_name = secure_filename(photo_file.filename)
            extension = original_name.rsplit(".", 1)[1].lower()
            new_filename = f"surplus_{uuid4().hex}.{extension}"

            upload_dir = os.path.join(current_app.static_folder, "uploads", "food_images")
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, new_filename)
            photo_file.save(file_path)

            saved_photo_path = f"uploads/food_images/{new_filename}"

        event = Event.query.filter_by(provider_id=provider_id, event_name=event_name).first()
        if not event:
            event = Event(provider_id=provider_id, event_name=event_name, event_date=datetime.utcnow())
            db.session.add(event)
            db.session.flush()

        surplus = Surplus(
            provider_id=provider_id,
            event_id=event.id,
            event_name=event_name,
            mahal_name=mahal_name,
            provider_name=provider_name,
            food_type=food_type,
            quantity=quantity_kg,
            quantity_kg=quantity_kg,
            estimated_expiry=estimated_expiry,
            distance_km=distance_km,
            provider_location=geo["display_name"],
            provider_latitude=geo["lat"],
            provider_longitude=geo["lon"],
            photo_path=saved_photo_path,
            status="pending",
        )

        db.session.add(surplus)
        db.session.commit()
        publish_platform_update(scope="surplus", action="created", actor_role="provider")
        flash("Surplus added. Mark it as Ready to allow receiver pickup requests.", "success")
        return redirect(url_for("provider.provider_add_surplus"))

    recent_surplus = (
        Surplus.query.filter_by(provider_id=provider_id)
        .order_by(Surplus.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template("provider/add_surplus.html", recent_surplus=recent_surplus)


@provider.route("/provider/surplus/<int:surplus_id>/mark-ready", methods=["POST"])
@role_required("provider")
def provider_mark_surplus_ready(surplus_id):
    provider_id = _provider_id_from_session()
    surplus = Surplus.query.get_or_404(surplus_id)

    if surplus.provider_id != provider_id:
        flash("You are not authorized to update this surplus batch.", "error")
        return redirect(url_for("provider.provider_add_surplus"))

    if surplus.status != "pending":
        flash("This surplus batch is already open or completed.", "info")
        return redirect(url_for("provider.provider_add_surplus"))

    surplus.status = "available"
    db.session.commit()
    publish_platform_update(scope="surplus", action="ready", actor_role="provider")
    flash("Batch marked as ready. Receivers can now request pickup.", "success")
    return redirect(url_for("provider.provider_add_surplus"))


@provider.route("/provider/events")
@role_required("provider")
def provider_events():
    provider_id = _provider_id_from_session()
    events = Event.query.filter_by(provider_id=provider_id).order_by(Event.event_date.desc()).all()
    return render_template("provider/events.html", events=events)


@provider.route("/provider/allocations")
@role_required("provider")
def provider_allocations():
    provider_id = _provider_id_from_session()
    allocations = (
        Allocation.query.filter_by(provider_id=provider_id)
        .order_by(Allocation.created_at.desc())
        .all()
    )
    completed_count = sum(1 for item in allocations if item.status == "completed")
    pending_count = len(allocations) - completed_count
    total_meals_served = sum((((item.surplus.quantity if item.surplus and item.surplus.quantity is not None else (item.surplus.quantity_kg if item.surplus else 0))) * 2.5) for item in allocations)

    return render_template(
        "provider/allocations.html",
        allocations=allocations,
        completed_count=completed_count,
        pending_count=pending_count,
        total_meals_served=int(total_meals_served),
    )


@provider.route("/provider/allocations/<int:allocation_id>/verify-pickup", methods=["POST"])
@role_required("provider")
def provider_verify_pickup(allocation_id):
    provider_id = _provider_id_from_session()
    entered_code = (request.form.get("pickup_code") or "").strip()

    allocation = Allocation.query.get_or_404(allocation_id)

    if allocation.provider_id != provider_id:
        flash("You are not authorized to verify this pickup.", "error")
        return redirect(url_for("provider.provider_allocations"))

    if allocation.status == "completed":
        flash("This pickup is already verified and completed.", "info")
        return redirect(url_for("provider.provider_allocations"))

    if not entered_code or entered_code != (allocation.otp_code or ""):
        flash("Invalid receiver code. Pickup remains On the way.", "error")
        return redirect(url_for("provider.provider_allocations"))

    allocation.status = "completed"
    if allocation.surplus:
        allocation.surplus.status = "completed"

    db.session.commit()
    publish_platform_update(scope="allocation", action="completed", actor_role="provider")

    flash("Receiver code verified. Provider marked Completed and receiver marked Received.", "success")
    return redirect(url_for("provider.provider_allocations"))


@provider.route("/provider/reviews")
@role_required("provider")
def provider_reviews():
    provider_id = _provider_id_from_session()
    reviews = Review.query.filter_by(provider_id=provider_id).order_by(Review.created_at.desc()).all()
    complaints = Complaint.query.filter_by(provider_id=provider_id).order_by(Complaint.created_at.desc()).all()

    avg_rating = db.session.query(func.avg(Review.rating)).filter_by(provider_id=provider_id).scalar() or 0

    return render_template(
        "provider/reviews.html",
        reviews=reviews,
        complaints=complaints,
        avg_rating=round(float(avg_rating), 2),
    )