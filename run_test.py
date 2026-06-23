#!/usr/bin/env python3

import csv
import logging
from cli.cli import run_tournament
import pathlib

# Source - https://stackoverflow.com/a/49563550
# Posted by Goolmoos
# Retrieved 2026-06-23, License - CC BY-SA 3.0

formatter = logging.Formatter('%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s')
logging.getLogger('').setLevel(logging.DEBUG)
fh = logging.FileHandler('baseline.log', mode='a')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logging.getLogger('').addHandler(fh)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)  
logging.getLogger('').addHandler(ch)

logging.info("Running baseline")

student_list = []

with open('score.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)
    for student in reader:
        student_list.append(student)

header = student_list.pop(0)
print(header)

current_dir = pathlib.Path(__file__).parent.resolve()

with open('new_score.csv', 'a') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(header)

for idx, student in enumerate(student_list):
    student_id = student[0]
    if student[1] == 'y':
        for baseline in header:
            algo = 'minimax'
            if baseline  in ('minimax-weak', 'minimax-strong'):
                algo = 'minimax'
            elif baseline in ('boss'):
                algo = 'pvs'
            else:
                continue
            logging.debug(
                    f'run {student_id} vs {baseline}'
                    )
            score = run_tournament(
                engine1_path=f'{current_dir}/build/{student_id}-ubgi',
                engine2_path=f'{current_dir}/build/{baseline}-ubgi',
                time_limit=2000,
                algo1='submission',
                algo2=algo,
                num_games=2,
                verbose=True,
            )
            logging.info(f'student {student_id} score: {score}')
            student[header.index(baseline)] = score
            student_list[idx] = student
        with open('new_score.csv', 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(student)
