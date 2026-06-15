from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from .extensions import db, login_manager


book_genres = db.Table(
    "book_genres",
    db.Column("book_id", db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    db.Column("genre_id", db.Integer, db.ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    users = db.relationship("User", back_populates="role")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    middle_name = db.Column(db.String(120))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role", back_populates="users")
    reviews = db.relationship("Review", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(part for part in parts if part)

    @property
    def role_name(self):
        return self.role.name if self.role else ""

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Genre(db.Model):
    __tablename__ = "genres"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    books = db.relationship("Book", secondary=book_genres, back_populates="genres")


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    short_description = db.Column(db.Text, nullable=False)
    publication_year = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    page_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    genres = db.relationship("Genre", secondary=book_genres, back_populates="books")
    cover = db.relationship("Cover", back_populates="book", cascade="all, delete-orphan", uselist=False, passive_deletes=True)
    reviews = db.relationship("Review", back_populates="book", cascade="all, delete-orphan", passive_deletes=True)

    @property
    def approved_reviews(self):
        return [review for review in self.reviews if review.status and review.status.name == "approved"]

    @property
    def approved_reviews_count(self):
        return len(self.approved_reviews)

    @property
    def average_rating(self):
        reviews = self.approved_reviews
        if not reviews:
            return None
        return round(sum(review.rating for review in reviews) / len(reviews), 2)


class Cover(db.Model):
    __tablename__ = "covers"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(120), nullable=False)
    md5_hash = db.Column(db.String(32), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, unique=True)
    book = db.relationship("Book", back_populates="cover")


class ReviewStatus(db.Model):
    __tablename__ = "review_statuses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    title = db.Column(db.String(120), nullable=False)
    reviews = db.relationship("Review", back_populates="status")


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status_id = db.Column(db.Integer, db.ForeignKey("review_statuses.id"), nullable=False)
    book = db.relationship("Book", back_populates="reviews")
    user = db.relationship("User", back_populates="reviews")
    status = db.relationship("ReviewStatus", back_populates="reviews")
    __table_args__ = (db.UniqueConstraint("book_id", "user_id", name="uq_reviews_book_user"),)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
