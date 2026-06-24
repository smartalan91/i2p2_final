#!/usr/bin/env python3

import csv
import logging
import pathlib
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from cli.cli import run_tournament


# ======================
# Config
# ======================

SCORE_FILE = pathlib.Path("score.csv")
BACKUP_FILE = pathlib.Path("score.csv.bak")
MAX_WORKERS = 4   # adjust this: 2, 4, 8, etc.


# ======================
# Logging
# ======================

formatter = logging.Formatter(
    "%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s"
)

logging.getLogger("").setLevel(logging.DEBUG)

fh = logging.FileHandler("baseline.log", mode="a")
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logging.getLogger("").addHandler(fh)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logging.getLogger("").addHandler(ch)

logging.info("Running baseline")


# ======================
# Helpers
# ======================

def get_algo(baseline: str):
    if baseline in ("minimax-weak", "minimax-strong"):
        return "minimax"
    elif baseline == "boss":
        return "pvs"
    return None


def write_score_csv(header, student_list):
    """
    Atomically rewrite score.csv.
    This avoids corrupting score.csv if the program crashes while writing.
    """
    tmp_file = SCORE_FILE.with_suffix(".csv.tmp")

    with open(tmp_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(student_list)

    os.replace(tmp_file, SCORE_FILE)


def run_one_match(current_dir, student_id, baseline, algo):
    """
    Worker function run in a thread.
    Do NOT write CSV here.
    Only return the result.
    """
    logging.debug(f"run {student_id} vs {baseline}")

    score = run_tournament(
        engine1_path=str(current_dir / "build" / f"{student_id}-ubgi"),
        engine2_path=str(current_dir / "build" / f"{baseline}-ubgi"),
        time_limit=2000,
        algo1="submission",
        algo2=algo,
        num_games=2,
        verbose=True,
    )

    logging.info(f"student {student_id} vs {baseline} score: {score}")
    return student_id, baseline, score


# ======================
# Read score.csv
# ======================

with open(SCORE_FILE, newline="") as csvfile:
    reader = csv.reader(csvfile)
    rows = list(reader)

header = rows[0]
student_list = rows[1:]

print(header)

# Make backup before modifying score.csv
if not BACKUP_FILE.exists():
    shutil.copyfile(SCORE_FILE, BACKUP_FILE)
    logging.info("Created backup score.csv.bak")

current_dir = pathlib.Path(__file__).parent.resolve()


# ======================
# Build jobs
# ======================

jobs = []

for row_idx, student in enumerate(student_list):
    student_id = student[0]

    # Pad row if it is shorter than header
    while len(student) < len(header):
        student.append("")

    if len(student) > 1 and student[1] == "y":
        for col_idx, baseline in enumerate(header):
            algo = get_algo(baseline)
            if algo is None:
                continue

            jobs.append({
                "row_idx": row_idx,
                "col_idx": col_idx,
                "student_id": student_id,
                "baseline": baseline,
                "algo": algo,
            })

logging.info(f"Total jobs: {len(jobs)}")
logging.info(f"Using MAX_WORKERS={MAX_WORKERS}")


# ======================
# Run jobs multithreaded
# ======================

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_job = {}

    for job in jobs:
        future = executor.submit(
            run_one_match,
            current_dir,
            job["student_id"],
            job["baseline"],
            job["algo"],
        )
        future_to_job[future] = job

    for future in as_completed(future_to_job):
        job = future_to_job[future]

        try:
            student_id, baseline, score = future.result()

            row_idx = job["row_idx"]
            col_idx = job["col_idx"]

            student_list[row_idx][col_idx] = score

            # Write back to score.csv after each completed match
            write_score_csv(header, student_list)

            logging.info(
                f"Updated score.csv: student={student_id}, baseline={baseline}, score={score}"
            )

        except Exception as e:
            logging.exception(
                f"FAILED: student={job['student_id']} vs baseline={job['baseline']}: {e}"
            )

logging.info("All jobs finished")
