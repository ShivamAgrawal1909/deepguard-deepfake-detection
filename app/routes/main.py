from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import ContactQuery

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("landing.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/awareness")
def awareness():
    return render_template("awareness.html")


@main_bp.route("/guidelines")
def guidelines():
    return render_template("guidelines.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        query = ContactQuery(
            name=request.form.get("name", ""),
            email=request.form.get("email", ""),
            subject=request.form.get("subject", ""),
            message=request.form.get("message", ""),
        )
        db.session.add(query)
        db.session.commit()
        flash("Your message has been sent. We will get back to you soon.", "success")
        return redirect(url_for("main.contact"))
    return render_template("contact.html")
