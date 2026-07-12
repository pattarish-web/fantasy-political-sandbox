from functools import wraps

from flask import Blueprint, jsonify, render_template, request, abort

from app import config
from app import db
from app.gemini_client import get_current_key_display
from app.simulation import run_simulation_batch
from app.historian import run_historian

bp = Blueprint("main", __name__)


def require_app_password(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        password = config.APP_PASSWORD
        if password:
            provided = request.headers.get("X-App-Password", "") or request.args.get("password", "")
            if provided != password:
                abort(401)
        return fn(*args, **kwargs)

    return wrapper


@bp.get("/")
def dashboard():
    characters = db.list_characters()
    return render_template("mobile_dashboard.html", characters=characters)


@bp.get("/chronicle")
def chronicle_index():
    chapters = db.list_chapters()
    return render_template("chronicle_index.html", chapters=chapters)


@bp.get("/chronicle/<int:round_num>")
def chronicle_chapter(round_num: int):
    chapter = db.get_chapter_by_round(round_num)
    if not chapter:
        abort(404)
    return render_template("chronicle_chapter.html", chapter=chapter)


@bp.get("/api/status")
def api_status():
    return jsonify(
        {
            "alive": db.count_alive(),
            "round": db.get_latest_round(),
            "current_api_index": get_current_key_display(),
        }
    )


@bp.post("/api/simulate")
@require_app_password
def api_simulate():
    result = run_simulation_batch(1)
    return jsonify(result)


@bp.post("/api/historian")
@require_app_password
def api_historian():
    result = run_historian()
    return jsonify(result)
