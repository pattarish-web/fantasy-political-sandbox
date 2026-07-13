import sys
import os

from app.db import init_db, list_chapters
from app.simulation import run_simulation_batch
from app.historian import run_historian
from app.export_html import rebuild_index, export_all_characters

def main():
    init_db()
    chapters_written = 0
    max_failures = 10
    consecutive_failures = 0
    print("Starting Bootstrap...")
    while chapters_written < 5:
        print(f"\n--- จำลองเหตุการณ์ Chapter {chapters_written + 1} ---")
        any_batch_succeeded = False
        # Run 2 batches of 5 simulations per chapter (Total 10)
        for i in range(2):
            print(f"  > Batch {i+1} (5 events)...")
            res = run_simulation_batch(5)
            if "error" in res:
                print("Error in batch:", res["error"])
            else:
                print(f"Batch {i+1} completed: {res.get('events_processed')} events processed.")
                any_batch_succeeded = True
                
        if not any_batch_succeeded:
            print("Skipping historian: no simulation batches succeeded in this iteration.")
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                print(f"Aborting bootstrap: {max_failures} consecutive failures.")
                sys.exit(1)
            continue
            
        print("Writing Chapter...")
        chap_res = run_historian()
        if "error" in chap_res:
            print("Failed to write chapter:", chap_res["error"])
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                print(f"Aborting bootstrap: {max_failures} consecutive failures.")
                sys.exit(1)
        else:
            print("Wrote Chapter:", chap_res.get("title"))
            chapters_written += 1
            consecutive_failures = 0
            
    # Finally, rebuild index
    print("Exporting all character profiles...")
    export_all_characters()
    print("Rebuilding HTML index...")
    rebuild_index(list_chapters())
    print("Bootstrap completed successfully.")

if __name__ == "__main__":
    main()
