from pathlib import Path

from flask import Flask

from app.db import init_db


def create_app() -> Flask:
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    init_db()
    from app import routes

    app.register_blueprint(routes.bp)
    return app
