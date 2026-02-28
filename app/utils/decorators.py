from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view_func):
	@wraps(view_func)
	def wrapper(*args, **kwargs):
		if not session.get("user_id"):
			flash("Please login to continue.", "warning")
			return redirect(url_for("auth.login"))
		return view_func(*args, **kwargs)

	return wrapper


def role_required(required_role):
	def decorator(view_func):
		@wraps(view_func)
		def wrapper(*args, **kwargs):
			if not session.get("user_id"):
				flash("Please login to continue.", "warning")
				return redirect(url_for("auth.login"))

			role = session.get("role")
			if role != required_role:
				flash("You are not authorized to access this page.", "error")
				return redirect(url_for("auth.login"))

			return view_func(*args, **kwargs)

		return wrapper

	return decorator
