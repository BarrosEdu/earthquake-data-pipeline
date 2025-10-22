# sync.py
import subprocess
import time
from datetime import datetime

def run_script(script_path):
    print(f"Running {script_path} ...")
    result = subprocess.run(["python", script_path], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error running {script_path}: {result.stderr}")
    else:
        print(f"Finished {script_path}")
    return result.returncode

if __name__ == "__main__":
    start_time = datetime.utcnow()
    print(f"Sync started at {start_time.isoformat()} UTC")

    # Step 1 — Transform data
    if run_script("ingest/transform.py") == 0:
        # Step 2 — Load to PostgreSQL
        if run_script("ingest/load_postgres.py") == 0:
            print("Sync complete — transform + load successful.")
        else:
            print("Load failed, check logs.")
    else:
        print("Transform failed, stopping process.")

    end_time = datetime.utcnow()
    print(f"Total duration: {(end_time - start_time).seconds} seconds")
