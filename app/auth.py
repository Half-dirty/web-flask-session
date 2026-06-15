from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from .models import User


bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("books.index"))
    if request.method == "POST":
        login_value = (request.form.get("login") or "").strip()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))
        user = User.query.filter_by(login=login_value).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("books.index"))
        flash("Невозможно аутентифицироваться с указанными логином и паролем", "danger")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(request.referrer or url_for("books.index"))
