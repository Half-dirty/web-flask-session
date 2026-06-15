from pathlib import Path
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from sqlalchemy.exc import SQLAlchemyError
from .extensions import db
from .models import Book, Genre, Review
from .utils import can_manage_books, is_admin, roles_required, validate_book_form, save_cover, render_markdown


bp = Blueprint("books", __name__)


@bp.route("/covers/<path:filename>")
def cover_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = Book.query.order_by(Book.publication_year.desc(), Book.id.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("index.html", pagination=pagination, books=pagination.items, can_manage_books=can_manage_books, is_admin=is_admin)


@bp.route("/books/new", methods=["GET", "POST"])
@roles_required("administrator")
def create():
    genres = Genre.query.order_by(Genre.name).all()
    if request.method == "POST":
        data = validate_book_form(request.form, request.files, is_create=True)
        selected_genres = Genre.query.filter(Genre.id.in_(data["genre_ids"])).all() if data["genre_ids"] else []
        if data["errors"] or len(selected_genres) != len(data["genre_ids"]):
            flash("При сохранении данных возникла ошибка. Проверьте корректность введённых данных.", "danger")
            return render_template("book_form.html", book=data, genres=genres, selected_genres=data["genre_ids"], action="create")
        try:
            book = Book(
                title=data["title"],
                short_description=data["short_description"],
                publication_year=data["publication_year"],
                publisher=data["publisher"],
                author=data["author"],
                page_count=data["page_count"],
                genres=selected_genres,
            )
            db.session.add(book)
            db.session.flush()
            save_cover(book, data["cover"])
            db.session.commit()
            flash("Книга успешно добавлена", "success")
            return redirect(url_for("books.show", book_id=book.id))
        except SQLAlchemyError:
            db.session.rollback()
            flash("При сохранении данных возникла ошибка. Проверьте корректность введённых данных.", "danger")
    return render_template("book_form.html", book=None, genres=genres, selected_genres=[], action="create")


@bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@roles_required("administrator", "moderator")
def edit(book_id):
    book = Book.query.get_or_404(book_id)
    genres = Genre.query.order_by(Genre.name).all()
    if request.method == "POST":
        data = validate_book_form(request.form, request.files, is_create=False)
        selected_genres = Genre.query.filter(Genre.id.in_(data["genre_ids"])).all() if data["genre_ids"] else []
        if data["errors"] or len(selected_genres) != len(data["genre_ids"]):
            flash("При сохранении данных возникла ошибка. Проверьте корректность введённых данных.", "danger")
            return render_template("book_form.html", book=data, genres=genres, selected_genres=data["genre_ids"], action="edit")
        try:
            book.title = data["title"]
            book.short_description = data["short_description"]
            book.publication_year = data["publication_year"]
            book.publisher = data["publisher"]
            book.author = data["author"]
            book.page_count = data["page_count"]
            book.genres = selected_genres
            db.session.commit()
            flash("Книга успешно обновлена", "success")
            return redirect(url_for("books.show", book_id=book.id))
        except SQLAlchemyError:
            db.session.rollback()
            flash("При сохранении данных возникла ошибка. Проверьте корректность введённых данных.", "danger")
    selected_genres = [genre.id for genre in book.genres]
    return render_template("book_form.html", book=book, genres=genres, selected_genres=selected_genres, action="edit")


@bp.route("/books/<int:book_id>")
def show(book_id):
    book = Book.query.get_or_404(book_id)
    reviews = Review.query.filter(Review.book_id == book.id, Review.status.has(name="approved")).order_by(Review.created_at.desc()).all()
    user_review = None
    from flask_login import current_user
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(book_id=book.id, user_id=current_user.id).first()
    return render_template("book_show.html", book=book, reviews=reviews, user_review=user_review, description_html=render_markdown(book.short_description))


@bp.post("/books/<int:book_id>/delete")
@roles_required("administrator")
def delete(book_id):
    book = Book.query.get_or_404(book_id)
    cover = book.cover
    filename = cover.filename if cover else None
    reusable = False
    if cover:
        reusable = cover.__class__.query.filter(cover.__class__.filename == cover.filename, cover.__class__.id != cover.id).count() > 0
    try:
        db.session.delete(book)
        db.session.commit()
        if filename and not reusable:
            path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
            if path.exists():
                path.unlink()
        flash("Книга успешно удалена", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("При удалении книги возникла ошибка", "danger")
    return redirect(url_for("books.index"))
