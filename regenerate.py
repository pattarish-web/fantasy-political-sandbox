from app.db import list_chapters
from app.export_html import export_chapter, export_all_characters, rebuild_index

if __name__ == "__main__":
    print("Exporting all chapters...")
    for c in list_chapters():
        export_chapter(c)
        print("Exported chapter", c["round_num"])

    print("Exporting all characters...")
    export_all_characters()

    print("Rebuilding index...")
    rebuild_index(list_chapters())

    print("Done.")
