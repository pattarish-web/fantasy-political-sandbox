from app import db
from app.export_html import clear_exported_content, export_all_characters, rebuild_index


def reset_world() -> dict:
    summary = db.reset_world_state()
    clear_exported_content()
    export_all_characters()
    rebuild_index(db.list_chapters())
    return summary
