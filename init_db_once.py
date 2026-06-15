from pathlib import Path
from app import create_app, seed_database
from app.extensions import db


app = create_app()


with app.app_context():
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///"):
        database_path = Path(uri.replace("sqlite:///", "", 1))
        database_path.parent.mkdir(parents=True, exist_ok=True)
        if not database_path.exists():
            db.create_all()
            seed_database()
