import sys
import os

from app.db import init_db, list_chapters
from app.simulation import run_simulation_round
from app.historian import run_historian
from app.export_html import rebuild_index

def main():
    init_db()
    chapters_written = 0
    print("Starting Bootstrap...")
    while chapters_written < 5:
        print(f"\n--- Generating Chapter {chapters_written + 1} ---")
        # Run 15 simulations per chapter
        for i in range(15):
            res = run_simulation_round()
            print(f"Sim Round {res.get('round_num')}: {res.get('p1_name')} vs {res.get('p2_name')} - Drama: {res.get('is_drama')}")
            
        print("Writing Chapter...")
        chap_res = run_historian()
        if "error" in chap_res:
            print("Failed to write chapter:", chap_res["error"])
        else:
            print("Wrote Chapter:", chap_res.get("title"))
            chapters_written += 1
            
    # Finally, rebuild index
    print("Rebuilding HTML index...")
    rebuild_index(list_chapters())
    print("Bootstrap completed successfully.")

if __name__ == "__main__":
    main()
