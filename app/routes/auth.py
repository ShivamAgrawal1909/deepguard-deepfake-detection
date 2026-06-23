from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app import db
from app.models import User
from app.utils.helpers import log_action, log_login

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("user.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            if not user.is_active_account:
                log_login(user, status="blocked")
                flash("Your account has been deactivated. Contact admin.", "danger")
                return render_template("auth/login.html")

            login_user(user)
            log_login(user, status="success")
            log_action("auth", "User login", f"{user.username} logged in", user.id)

            next_page = request.args.get("next")
            if user.is_admin:
                return redirect(next_page or url_for("admin.dashboard"))
            return redirect(next_page or url_for("user.dashboard"))

        log_login(user, status="failed") if user else None
        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("user.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([username, email, password]):
            flash("All required fields must be filled.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
        else:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                phone=phone,
                role="user",
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            log_action("auth", "User registration", f"New user: {username}", user.id)
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        log_action("auth", "User logout", f"{current_user.username} logged out", current_user.id)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
