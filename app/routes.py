from functools import wraps

from flask import Blueprint, jsonify, render_template, request, abort

from app import config
from app import db
from app.simulation import run_simulation_batch
from app.historian import run_historian

bp = Blueprint("main", __name__)


def require_app_password(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not config.APP_PASSWORD:
            abort(403)
        provided = request.headers.get("X-App-Password", "")
        if provided != config.APP_PASSWORD:
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


@bp.get("/")
def dashboard():
    return render_template("mobile_dashboard.html")
from flask import send_from_directory
import os

@bp.get("/local_chronicle/<path:filename>")
def serve_chronicle(filename):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(os.path.join(root, "chronicle"), filename)

@bp.get("/local_chronicle/")
def serve_chronicle_index():
    return serve_chronicle("index.html")


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
            "current_api_index": "Groq",
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


@bp.post("/api/git_sync")
@require_app_password
def api_git_sync():
    import subprocess
    try:
        # Rebuild index just in case
        from app.db import list_chapters
        from app.export_html import rebuild_index
        rebuild_index(list_chapters())
        
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Auto: Local Dashboard Sync"], capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        return jsonify({"status": "success"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Git sync failed: {e.stderr.decode('utf-8', errors='ignore')}"})
    except Exception as e:
        return jsonify({"error": str(e)})
