from app import db
from app.export_html import clear_exported_content, export_all_characters, rebuild_index


def reset_world() -> dict:
    import random
    summary = db.reset_world_state()
    state = db.get_story_state()
    state["image_seed_salt"] = random.randint(1, 999999)
    db.save_story_state(state)
    clear_exported_content()
    export_all_characters()
    rebuild_index(db.list_chapters())
    return summary
