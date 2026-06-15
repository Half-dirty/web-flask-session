from functools import wraps
from hashlib import md5
from pathlib import Path
import bleach
import markdown
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
from .extensions import db
from .models import Cover


ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
    "p", "br", "pre", "span", "h1", "h2", "h3", "h4", "h5", "h6", "img", "table", "thead", "tbody", "tr", "th", "td"
}
ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title"],
    "img": ["src", "alt", "title"],
    "span": ["class"],
    "code": ["class"],
}
ALLOWED_PROTOCOLS = set(bleach.sanitizer.ALLOWED_PROTOCOLS) | {"data"}


RATING_OPTIONS = [
    (5, "отлично"),
    (4, "хорошо"),
    (3, "удовлетворительно"),
    (2, "неудовлетворительно"),
    (1, "плохо"),
    (0, "ужасно"),
]


def sanitize_markdown(text):
    return bleach.clean(text or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, protocols=ALLOWED_PROTOCOLS, strip=True)


def render_markdown(text):
    html = markdown.markdown(text or "", extensions=["extra", "nl2br"])
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, protocols=ALLOWED_PROTOCOLS, strip=True)


def is_admin():
    return current_user.is_authenticated and current_user.role_name == "administrator"


def is_moderator():
    return current_user.is_authenticated and current_user.role_name == "moderator"


def can_manage_books():
    return current_user.is_authenticated and current_user.role_name in {"administrator", "moderator"}


def can_review():
    return current_user.is_authenticated and current_user.role_name in {"administrator", "moderator", "user"}


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Для выполнения данного действия необходимо пройти процедуру аутентификации", "warning")
                return redirect(url_for("auth.login"))
            if current_user.role_name not in roles:
                flash("У вас недостаточно прав для выполнения данного действия", "danger")
                return redirect(url_for("books.index"))
            return view(*args, **kwargs)
        return wrapper
    return decorator


def authenticated_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Для выполнения данного действия необходимо пройти процедуру аутентификации", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapper


def validate_book_form(form, files, is_create=True):
    errors = []
    title = (form.get("title") or "").strip()
    short_description = (form.get("short_description") or "").strip()
    publication_year = (form.get("publication_year") or "").strip()
    publisher = (form.get("publisher") or "").strip()
    author = (form.get("author") or "").strip()
    page_count = (form.get("page_count") or "").strip()
    genre_ids = [int(value) for value in form.getlist("genres") if value.isdigit()]
    cover = files.get("cover")
    if not title:
        errors.append("title")
    if not short_description:
        errors.append("short_description")
    try:
        publication_year = int(publication_year)
        if publication_year < 1 or publication_year > 9999:
            errors.append("publication_year")
    except ValueError:
        publication_year = None
        errors.append("publication_year")
    if not publisher:
        errors.append("publisher")
    if not author:
        errors.append("author")
    try:
        page_count = int(page_count)
        if page_count <= 0:
            errors.append("page_count")
    except ValueError:
        page_count = None
        errors.append("page_count")
    if not genre_ids:
        errors.append("genres")
    if is_create and (not cover or not cover.filename):
        errors.append("cover")
    return {
        "title": title,
        "short_description": sanitize_markdown(short_description),
        "publication_year": publication_year,
        "publisher": publisher,
        "author": author,
        "page_count": page_count,
        "genre_ids": genre_ids,
        "cover": cover,
        "errors": errors,
    }


def save_cover(book, file_storage):
    data = file_storage.read()
    file_storage.seek(0)
    digest = md5(data).hexdigest()
    existing = Cover.query.filter_by(md5_hash=digest).first()
    original_name = secure_filename(file_storage.filename) or "cover"
    suffix = Path(original_name).suffix.lower()
    if existing:
        cover = Cover(filename=existing.filename, mime_type=file_storage.mimetype or existing.mime_type, md5_hash=digest, book=book)
        db.session.add(cover)
        db.session.flush()
        return cover
    cover = Cover(filename="pending", mime_type=file_storage.mimetype or "application/octet-stream", md5_hash=digest, book=book)
    db.session.add(cover)
    db.session.flush()
    cover.filename = f"{cover.id}{suffix}"
    path = Path(current_app.config["UPLOAD_FOLDER"])
    path.mkdir(parents=True, exist_ok=True)
    file_storage.save(path / cover.filename)
    return cover


def remove_cover_file_if_unused(cover):
    if not cover:
        return
    same_files = Cover.query.filter(Cover.filename == cover.filename, Cover.id != cover.id).count()
    if same_files:
        return
    path = Path(current_app.config["UPLOAD_FOLDER"]) / cover.filename
    if path.exists():
        path.unlink()
