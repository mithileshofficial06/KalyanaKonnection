from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func

from app import db
from app.models.allocation import Allocation
from app.models.complaint import Complaint
from app.models.event import Event
from app.models.review import Review
from app.models.surplus import Surplus
from app.models.user import User
from app.services.realtime_service import publish_platform_update
from app.utils.decorators import role_required


admin = Blueprint("admin", __name__)


def _safe_rate(numerator, denominator):
	if not denominator:
		return 0.0
	return round((numerator / denominator) * 100, 1)


def _build_dashboard_metrics():
	total_providers = User.query.filter_by(role="provider").count()
	total_ngos = User.query.filter_by(role="ngo").count()
	total_events = Event.query.count()
	total_surplus_kg = db.session.query(
		func.coalesce(func.sum(func.coalesce(Surplus.quantity, Surplus.quantity_kg)), 0.0)
	).scalar() or 0
	total_allocations = Allocation.query.count()
	active_complaints = Complaint.query.filter(Complaint.status.in_(["Under Review", "Escalated"])).count()

	return {
		"total_providers": total_providers,
		"total_ngos": total_ngos,
		"total_events": total_events,
		"total_surplus_kg": round(float(total_surplus_kg), 1),
		"total_allocations": total_allocations,
		"active_complaints": active_complaints,
	}


def _build_operational_insights(metrics):
	completed_allocations = Allocation.query.filter(func.lower(Allocation.status) == "completed").count()
	pending_allocations = Allocation.query.filter(func.lower(Allocation.status) != "completed").count()
	avg_trust_score = db.session.query(func.avg(Review.rating)).scalar() or 0
	high_risk_batches = Surplus.query.filter(func.lower(func.coalesce(Surplus.estimated_expiry, "")).like("%1%")).count()
	open_complaints = Complaint.query.filter(func.lower(Complaint.status).in_(["under review", "escalated"])).count()
	unallocated_surplus = db.session.query(Surplus.id).outerjoin(Allocation, Allocation.surplus_id == Surplus.id).filter(Allocation.id.is_(None)).count()
	completion_rate = _safe_rate(completed_allocations, metrics["total_allocations"])

	return {
		"completed_allocations": completed_allocations,
		"pending_allocations": pending_allocations,
		"avg_trust_score": round(float(avg_trust_score), 2),
		"high_risk_batches": high_risk_batches,
		"open_complaints": open_complaints,
		"unallocated_surplus": unallocated_surplus,
		"completion_rate": completion_rate,
	}


def _build_analytics_payload(metrics):
	now = datetime.utcnow()
	month_labels = []
	month_keys = []
	for idx in reversed(range(6)):
		reference = (now.replace(day=1) - timedelta(days=idx * 30))
		month_key = reference.strftime("%Y-%m")
		month_keys.append(month_key)
		month_labels.append(reference.strftime("%b %Y"))

	start_window = now - timedelta(days=190)
	surplus_rows = Surplus.query.filter(Surplus.created_at >= start_window).all()
	allocation_rows = Allocation.query.filter(Allocation.created_at >= start_window).all()

	monthly_surplus_map = defaultdict(float)
	for row in surplus_rows:
		if not row.created_at:
			continue
		key = row.created_at.strftime("%Y-%m")
		monthly_surplus_map[key] += float(row.quantity or row.quantity_kg or 0)

	monthly_completed_allocations_map = defaultdict(int)
	for row in allocation_rows:
		if not row.created_at or (row.status or "").lower() != "completed":
			continue
		key = row.created_at.strftime("%Y-%m")
		monthly_completed_allocations_map[key] += 1

	monthly_surplus = [round(monthly_surplus_map.get(key, 0), 1) for key in month_keys]
	monthly_completed_allocations = [monthly_completed_allocations_map.get(key, 0) for key in month_keys]

	complaint_status_rows = (
		db.session.query(func.lower(Complaint.status), func.count(Complaint.id))
		.group_by(func.lower(Complaint.status))
		.all()
	)
	complaint_status = {status or "unknown": count for status, count in complaint_status_rows}

	top_providers = (
		db.session.query(
			User.full_name,
			func.coalesce(func.sum(func.coalesce(Surplus.quantity, Surplus.quantity_kg)), 0.0).label("donated_kg"),
		)
		.join(Surplus, Surplus.provider_id == User.id)
		.filter(User.role == "provider")
		.group_by(User.id, User.full_name)
		.order_by(func.coalesce(func.sum(func.coalesce(Surplus.quantity, Surplus.quantity_kg)), 0.0).desc())
		.limit(5)
		.all()
	)

	top_ngos = (
		db.session.query(User.full_name, func.count(Allocation.id).label("completed_pickups"))
		.join(Allocation, Allocation.ngo_id == User.id)
		.filter(User.role == "ngo", func.lower(Allocation.status) == "completed")
		.group_by(User.id, User.full_name)
		.order_by(func.count(Allocation.id).desc())
		.limit(5)
		.all()
	)

	avg_trust_score = db.session.query(func.avg(Review.rating)).scalar() or 0
	completed_allocations = Allocation.query.filter(func.lower(Allocation.status) == "completed").count()
	allocation_efficiency = _safe_rate(completed_allocations, metrics["total_allocations"])

	return {
		"month_labels": month_labels,
		"monthly_surplus": monthly_surplus,
		"monthly_completed_allocations": monthly_completed_allocations,
		"complaint_status": complaint_status,
		"top_providers": [{"name": name, "donated_kg": round(float(total or 0), 1)} for name, total in top_providers],
		"top_ngos": [{"name": name, "completed_pickups": count} for name, count in top_ngos],
		"avg_trust_score": round(float(avg_trust_score), 2),
		"allocation_efficiency": allocation_efficiency,
	}


def _build_recent_activity(limit=8):
	allocation_rows = (
		Allocation.query.order_by(Allocation.created_at.desc()).limit(limit).all()
	)
	complaint_rows = (
		Complaint.query.order_by(Complaint.created_at.desc()).limit(limit).all()
	)
	event_rows = Event.query.order_by(Event.created_at.desc()).limit(limit).all()

	activity = []

	for row in allocation_rows:
		actor = row.ngo.full_name if getattr(row, "ngo", None) else "NGO"
		activity.append({
			"timestamp": row.created_at,
			"module": "Allocation",
			"event": f"Allocation {row.status}",
			"actor": actor,
			"status": row.status,
		})

	for row in complaint_rows:
		activity.append({
			"timestamp": row.created_at,
			"module": "Complaint",
			"event": row.issue_type,
			"actor": row.ngo_user.full_name if row.ngo_user else "NGO",
			"status": row.status,
		})

	for row in event_rows:
		activity.append({
			"timestamp": row.created_at,
			"module": "Event",
			"event": row.event_name,
			"actor": row.provider.full_name if row.provider else "Provider",
			"status": "created",
		})

	activity.sort(key=lambda item: item["timestamp"] or 0, reverse=True)
	return activity[:limit]


def _status_class(status_value: str) -> str:
	status_text = (status_value or "").lower()
	if status_text in {"completed", "resolved", "successful", "active"}:
		return "completed"
	if status_text in {"under review", "requested", "allocated", "open", "in transit"}:
		return "active"
	if status_text in {"escalated", "failed", "rejected"}:
		return "escalated"
	return "active"


@admin.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
	metrics = _build_dashboard_metrics()
	recent_activity = _build_recent_activity(limit=8)
	insights = _build_operational_insights(metrics)
	return render_template("admin/dashboard.html", metrics=metrics, insights=insights, recent_activity=recent_activity, status_class=_status_class)


@admin.route("/admin/dashboard/live")
@role_required("admin")
def admin_dashboard_live():
	metrics = _build_dashboard_metrics()
	recent_activity = _build_recent_activity(limit=8)
	insights = _build_operational_insights(metrics)
	return jsonify({
		"metrics": metrics,
		"insights": insights,
		"recent_activity": [
			{
				"timestamp": item["timestamp"].isoformat() if item["timestamp"] else "",
				"module": item["module"],
				"event": item["event"],
				"actor": item["actor"],
				"status": item["status"],
			}
			for item in recent_activity
		],
	})


@admin.route("/admin/users")
@role_required("admin")
def admin_users():
	search = (request.args.get("search") or "").strip().lower()
	role = (request.args.get("role") or "").strip().lower()

	query = User.query
	if role in {"provider", "ngo", "admin"}:
		query = query.filter(User.role == role)

	if search:
		query = query.filter(
			func.lower(User.full_name).like(f"%{search}%") | func.lower(User.email).like(f"%{search}%")
		)

	users = query.order_by(User.id.desc()).all()

	provider_ratings = dict(
		db.session.query(Review.provider_id, func.avg(Review.rating)).group_by(Review.provider_id).all()
	)

	role_summary_rows = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
	role_summary = {row[0]: row[1] for row in role_summary_rows}
	users_count = len(users)

	return render_template(
		"admin/users.html",
		users=users,
		provider_ratings=provider_ratings,
		role_summary=role_summary,
		users_count=users_count,
		search=search,
		role=role,
	)


@admin.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def admin_delete_user(user_id):
	current_admin_id = session.get("user_id")
	if current_admin_id == user_id:
		flash("You cannot delete your own admin account while logged in.", "warning")
		return redirect(url_for("admin.admin_users"))

	target_user = User.query.get_or_404(user_id)

	Allocation.query.filter(
		(Allocation.provider_id == user_id) | (Allocation.ngo_id == user_id)
	).delete(synchronize_session=False)

	Review.query.filter(
		(Review.provider_id == user_id) | (Review.ngo_id == user_id)
	).delete(synchronize_session=False)

	Complaint.query.filter(
		(Complaint.provider_id == user_id) | (Complaint.ngo_id == user_id)
	).delete(synchronize_session=False)

	Surplus.query.filter_by(provider_id=user_id).delete(synchronize_session=False)
	Event.query.filter_by(provider_id=user_id).delete(synchronize_session=False)

	db.session.delete(target_user)
	db.session.commit()
	publish_platform_update(scope="user", action="deleted", actor_role="admin")

	flash("User deleted successfully.", "success")
	return redirect(url_for("admin.admin_users"))


@admin.route("/admin/events")
@role_required("admin")
def admin_events():
	events = Event.query.order_by(Event.created_at.desc()).limit(50).all()
	event_insights = {
		"total_events": len(events),
		"total_expected_guests": sum((item.guest_count or 0) for item in events),
		"events_with_surplus": sum(1 for item in events if item.surplus_batches),
	}
	return render_template("admin/events.html", events=events, event_insights=event_insights)


@admin.route("/admin/allocations")
@role_required("admin")
def admin_allocations():
	allocations = Allocation.query.order_by(Allocation.created_at.desc()).limit(60).all()
	status_totals = defaultdict(int)
	for row in allocations:
		status_totals[(row.status or "unknown").lower()] += 1

	allocation_insights = {
		"total": len(allocations),
		"completed": status_totals.get("completed", 0),
		"requested": status_totals.get("requested", 0),
		"allocated": status_totals.get("allocated", 0),
		"in_transit": status_totals.get("in transit", 0),
	}
	return render_template("admin/allocations.html", allocations=allocations, allocation_insights=allocation_insights, status_class=_status_class)


@admin.route("/admin/complaints")
@role_required("admin")
def admin_complaints():
	complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(60).all()
	status_totals = defaultdict(int)
	for row in complaints:
		status_totals[(row.status or "unknown").lower()] += 1

	complaint_insights = {
		"total": len(complaints),
		"under_review": status_totals.get("under review", 0),
		"escalated": status_totals.get("escalated", 0),
		"resolved": status_totals.get("resolved", 0),
		"rejected": status_totals.get("rejected", 0),
	}
	return render_template("admin/complaints.html", complaints=complaints, complaint_insights=complaint_insights, status_class=_status_class)


@admin.route("/admin/complaints/<int:complaint_id>/status", methods=["POST"])
@role_required("admin")
def admin_update_complaint_status(complaint_id):
	complaint = Complaint.query.get_or_404(complaint_id)
	next_status = (request.form.get("status") or "").strip()
	allowed = {"Under Review", "Escalated", "Resolved", "Rejected"}
	if next_status not in allowed:
		flash("Invalid complaint status selected.", "error")
		return redirect(url_for("admin.admin_complaints"))

	complaint.status = next_status
	db.session.commit()
	publish_platform_update(scope="complaint", action="status-updated", actor_role="admin")
	flash("Complaint status updated successfully.", "success")
	return redirect(url_for("admin.admin_complaints"))


@admin.route("/admin/analytics")
@role_required("admin")
def admin_analytics():
	metrics = _build_dashboard_metrics()
	analytics = _build_analytics_payload(metrics)

	return render_template(
		"admin/analytics.html",
		metrics=metrics,
		analytics=analytics,
	)
