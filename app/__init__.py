from pathlib import Path
from flask import Flask
from .auth import bp as auth_bp
from .books import bp as books_bp
from .config import Config
from .extensions import db, login_manager
from .models import Role, User, Genre, Book, ReviewStatus
from .reviews import bp as reviews_bp
from .utils import can_manage_books, can_review, is_admin, is_moderator, render_markdown


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Для выполнения данного действия необходимо пройти процедуру аутентификации"
    login_manager.login_message_category = "warning"
    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(reviews_bp)

    @app.context_processor
    def inject_helpers():
        return {
            "can_manage_books": can_manage_books,
            "can_review": can_review,
            "is_admin": is_admin,
            "is_moderator": is_moderator,
            "render_markdown": render_markdown,
        }

    @app.cli.command("init-db")
    def init_db_command():
        db.drop_all()
        db.create_all()
        seed_database()
        print("Database initialized")

    return app


def seed_database():
    from werkzeug.security import generate_password_hash
    roles = [
        Role(name="administrator", description="Суперпользователь с полным доступом к системе"),
        Role(name="moderator", description="Пользователь для редактирования книг и модерации рецензий"),
        Role(name="user", description="Пользователь для просмотра книг и создания рецензий"),
    ]
    statuses = [
        ReviewStatus(name="pending", title="На рассмотрении"),
        ReviewStatus(name="approved", title="Одобрена"),
        ReviewStatus(name="rejected", title="Отклонена"),
    ]
    genres = [
        Genre(name="Фантастика"),
        Genre(name="Детектив"),
        Genre(name="Роман"),
        Genre(name="Научная литература"),
        Genre(name="История"),
    ]
    db.session.add_all(roles + statuses + genres)
    db.session.flush()
    role_map = {role.name: role for role in roles}
    users = [
        User(login="admin", password_hash=generate_password_hash("qwerty"), last_name="Кузнецов", first_name="Никита", middle_name="Владимирович", role=role_map["administrator"]),
        User(login="moderator", password_hash=generate_password_hash("qwerty"), last_name="Иванов", first_name="Модератор", middle_name="Петрович", role=role_map["moderator"]),
        User(login="user", password_hash=generate_password_hash("qwerty"), last_name="Петров", first_name="Читатель", middle_name="Иванович", role=role_map["user"]),
    ]
    db.session.add_all(users)
    db.session.commit()
