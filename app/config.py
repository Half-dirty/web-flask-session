from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


def default_database_url():
    if "AMVERA" in os.environ:
        return "sqlite:////data/library.db"
    return f"sqlite:///{BASE_DIR / 'library.db'}"


def default_upload_folder():
    if "AMVERA" in os.environ:
        return Path("/data/covers")
    return BASE_DIR / "app" / "static" / "uploads" / "covers"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "exam-library-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", default_database_url())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", default_upload_folder()))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
