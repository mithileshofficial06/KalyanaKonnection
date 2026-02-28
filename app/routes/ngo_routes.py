from datetime import datetime, timedelta
import secrets

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func

from app import db
from app.models.allocation import Allocation
from app.models.complaint import Complaint
from app.models.review import Review
from app.models.surplus import Surplus
from app.models.user import User
from app.services.matching_service import filter_surplus_by_location
from app.services.realtime_service import publish_platform_update
from app.utils.decorators import role_required


ngo = Blueprint("ngo", __name__)


def _ngo_id_from_session():
	try:
		return int(session.get("user_id"))
	except (TypeError, ValueError):
		return None


def _generate_unique_pickup_code() -> str:
	while True:
		code = f"{secrets.randbelow(1_000_000):06d}"
		exists = Allocation.query.filter(
			Allocation.otp_code == code,
			Allocation.status.in_(["requested", "allocated"]),
		).first()
		if not exists:
			return code


@ngo.route("/ngo/dashboard")
@role_required("ngo")
def ngo_dashboard():
	ngo_id = _ngo_id_from_session()
	available_surplus_count = Surplus.query.filter_by(status="available").count()
	active_pickups_count = Allocation.query.filter(
		Allocation.ngo_id == ngo_id,
		Allocation.status.in_(["requested", "allocated"]),
	).count()
	completed_pickups_count = Allocation.query.filter_by(ngo_id=ngo_id, status="completed").count()
	trust_score = db.session.query(func.avg(Review.rating)).filter_by(ngo_id=ngo_id).scalar() or 0

	recent_surplus = (
		Surplus.query.filter_by(status="available")
		.order_by(Surplus.created_at.desc())
		.limit(8)
		.all()
	)

	return render_template(
		"ngo/dashboard.html",
		available_surplus_count=available_surplus_count,
		active_pickups_count=active_pickups_count,
		completed_pickups_count=completed_pickups_count,
		trust_score=round(float(trust_score), 2),
		recent_surplus=recent_surplus,
	)


@ngo.route("/ngo/nearby-surplus")
@role_required("ngo")
def ngo_nearby_surplus():
	receiver_location = (request.args.get("receiver_location") or "").strip()
	radius_km_raw = (request.args.get("radius_km") or "8").strip()

	try:
		radius_km = float(radius_km_raw)
	except ValueError:
		radius_km = 8.0

	all_available = (
		Surplus.query.filter_by(status="available")
		.order_by(Surplus.created_at.desc())
		.all()
	)

	resolved_location = None
	if receiver_location:
		filtered, resolved_location = filter_surplus_by_location(all_available, receiver_location, radius_km)
		available_surplus = filtered
		if resolved_location is None:
			flash("Could not find that location. Try a nearby place name.", "warning")
	else:
		available_surplus = []

	return render_template(
		"ngo/nearby_surplus.html",
		available_surplus=available_surplus,
		receiver_location=receiver_location,
		radius_km=radius_km,
		resolved_location=resolved_location,
	)


@ngo.route("/ngo/request-food/<int:surplus_id>", methods=["POST"])
@role_required("ngo")
def ngo_request_food(surplus_id):
	ngo_id = _ngo_id_from_session()
	surplus = Surplus.query.get_or_404(surplus_id)

	if surplus.status != "available":
		flash("This batch is not ready yet. Provider must mark it as ready first.", "warning")
		return redirect(url_for("ngo.ngo_nearby_surplus"))

	if not surplus.photo_path:
		flash("Photo is required before applying for food.", "warning")
		return redirect(url_for("ngo.ngo_nearby_surplus"))

	allocation = Allocation(
		surplus_id=surplus.id,
		provider_id=surplus.provider_id,
		ngo_id=ngo_id,
		status="requested",
		pickup_time=datetime.utcnow() + timedelta(hours=2),
		otp_code=_generate_unique_pickup_code(),
	)

	db.session.add(allocation)
	surplus.status = "requested"
	db.session.commit()
	publish_platform_update(scope="allocation", action="requested", actor_role="ngo")

	flash("Pickup request sent. Status is now On the way. Share your 6-digit pickup code at collection.", "success")
	return redirect(url_for("ngo.ngo_nearby_surplus"))


@ngo.route("/ngo/allocations")
@role_required("ngo")
def ngo_allocations():
	ngo_id = _ngo_id_from_session()
	allocations = (
		Allocation.query.filter_by(ngo_id=ngo_id)
		.order_by(Allocation.created_at.desc())
		.all()
	)
	return render_template("ngo/allocations.html", allocations=allocations)


@ngo.route("/ngo/history")
@role_required("ngo")
def ngo_history():
	ngo_id = _ngo_id_from_session()
	history_allocations = (
		Allocation.query.filter_by(ngo_id=ngo_id, status="completed")
		.order_by(Allocation.created_at.desc())
		.all()
	)
	total_meals_served = sum(int(((a.surplus.quantity if a.surplus and a.surplus.quantity is not None else (a.surplus.quantity_kg if a.surplus else 0)) * 2.5)) for a in history_allocations)
	return render_template("ngo/history.html", history_allocations=history_allocations, total_meals_served=total_meals_served)


@ngo.route("/ngo/reviews", methods=["GET", "POST"])
@role_required("ngo")
def ngo_reviews():
	ngo_id = _ngo_id_from_session()

	provider_ids = (
		db.session.query(Allocation.provider_id)
		.filter(Allocation.ngo_id == ngo_id)
		.distinct()
		.all()
	)
	provider_ids = [provider_id for (provider_id,) in provider_ids if provider_id]
	providers = User.query.filter(User.id.in_(provider_ids)).all() if provider_ids else []

	if request.method == "POST":
		action_type = request.form.get("action_type")

		if action_type == "review":
			provider_id_raw = request.form.get("provider_id")
			rating_raw = request.form.get("rating")
			comment = (request.form.get("comment") or "").strip()

			if not provider_id_raw or not rating_raw:
				flash("Provider and rating are required.", "warning")
				return redirect(url_for("ngo.ngo_reviews"))

			provider_id = int(provider_id_raw)
			rating = int(rating_raw)

			if provider_id not in provider_ids:
				flash("You can review only providers you received food from.", "error")
				return redirect(url_for("ngo.ngo_reviews"))

			if rating < 1 or rating > 5 or not comment:
				flash("Please provide valid rating and comment.", "warning")
				return redirect(url_for("ngo.ngo_reviews"))

			review = Review(
				ngo_id=ngo_id,
				provider_id=provider_id,
				rating=rating,
				comment=comment,
			)
			db.session.add(review)
			db.session.commit()
			publish_platform_update(scope="review", action="created", actor_role="ngo")
			flash("Review submitted successfully.", "success")
			return redirect(url_for("ngo.ngo_reviews"))

		if action_type == "complaint":
			provider_id_val = request.form.get("provider_id")
			issue_type = (request.form.get("issue_type") or "").strip()
			description = (request.form.get("description") or "").strip()

			provider_id = int(provider_id_val) if provider_id_val else None
			complaint = Complaint(
				ngo_id=ngo_id,
				provider_id=provider_id,
				issue_type=issue_type,
				description=description,
				status="Under Review",
			)
			db.session.add(complaint)
			db.session.commit()
			publish_platform_update(scope="complaint", action="created", actor_role="ngo")
			flash("Complaint submitted.", "success")
			return redirect(url_for("ngo.ngo_reviews"))

	reviews = Review.query.filter_by(ngo_id=ngo_id).order_by(Review.created_at.desc()).all()
	recent_complaints = Complaint.query.filter_by(ngo_id=ngo_id).order_by(Complaint.created_at.desc()).limit(10).all()

	return render_template(
		"ngo/reviews.html",
		providers=providers,
		reviews=reviews,
		recent_complaints=recent_complaints,
	)
