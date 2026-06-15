from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from .extensions import db
from .models import Book, Review, ReviewStatus
from .utils import RATING_OPTIONS, authenticated_required, render_markdown, roles_required, sanitize_markdown


bp = Blueprint("reviews", __name__)


@bp.route("/books/<int:book_id>/reviews/new", methods=["GET", "POST"])
@authenticated_required
def create(book_id):
    book = Book.query.get_or_404(book_id)
    existing = Review.query.filter_by(book_id=book.id, user_id=current_user.id).first()
    if existing:
        flash("Вы уже оставили рецензию на эту книгу", "warning")
        return redirect(url_for("books.show", book_id=book.id))
    if request.method == "POST":
        rating_raw = request.form.get("rating", "5")
        text = (request.form.get("text") or "").strip()
        try:
            rating = int(rating_raw)
        except ValueError:
            rating = -1
        if rating not in range(0, 6) or not text:
            flash("При сохранении рецензии возникла ошибка. Проверьте корректность введённых данных.", "danger")
            return render_template("review_form.html", book=book, rating_options=RATING_OPTIONS, selected_rating=rating_raw, text=text)
        try:
            status = ReviewStatus.query.filter_by(name="pending").first()
            review = Review(book=book, user=current_user, rating=rating, text=sanitize_markdown(text), status=status)
            db.session.add(review)
            db.session.commit()
            flash("Рецензия отправлена на рассмотрение", "success")
            return redirect(url_for("books.show", book_id=book.id))
        except SQLAlchemyError:
            db.session.rollback()
            flash("При сохранении рецензии возникла ошибка. Проверьте корректность введённых данных.", "danger")
    return render_template("review_form.html", book=book, rating_options=RATING_OPTIONS, selected_rating=5, text="")


@bp.route("/my-reviews")
@roles_required("user")
def my_reviews():
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template("my_reviews.html", reviews=reviews, render_markdown=render_markdown)


@bp.route("/moderation/reviews")
@roles_required("administrator", "moderator")
def moderation_list():
    page = request.args.get("page", 1, type=int)
    pending = ReviewStatus.query.filter_by(name="pending").first_or_404()
    pagination = Review.query.filter_by(status_id=pending.id).order_by(Review.created_at.asc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("moderation_list.html", pagination=pagination, reviews=pagination.items)


@bp.route("/moderation/reviews/<int:review_id>")
@roles_required("administrator", "moderator")
def moderation_show(review_id):
    review = Review.query.get_or_404(review_id)
    return render_template("moderation_show.html", review=review, review_html=render_markdown(review.text))


@bp.post("/moderation/reviews/<int:review_id>/approve")
@roles_required("administrator", "moderator")
def approve(review_id):
    return change_status(review_id, "approved", "Рецензия одобрена")


@bp.post("/moderation/reviews/<int:review_id>/reject")
@roles_required("administrator", "moderator")
def reject(review_id):
    return change_status(review_id, "rejected", "Рецензия отклонена")


def change_status(review_id, status_name, message):
    review = Review.query.get_or_404(review_id)
    status = ReviewStatus.query.filter_by(name=status_name).first_or_404()
    try:
        review.status = status
        db.session.commit()
        flash(message, "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("При изменении статуса рецензии возникла ошибка", "danger")
    return redirect(url_for("reviews.moderation_list"))
