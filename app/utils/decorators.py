from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("auth.login"))
        if not current_user.is_active_account:
            flash("Your account has been deactivated.", "danger")
            return redirect(url_for("auth.logout"))
        return f(*args, **kwargs)

    return decorated


def user_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        if not current_user.is_active_account:
            flash("Your account has been deactivated.", "danger")
            return redirect(url_for("auth.logout"))
        return f(*args, **kwargs)

    return decorated
