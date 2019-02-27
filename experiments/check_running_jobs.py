import re
import subprocess
import sys
import os

flag = bool(int(sys.argv[1])) or 0

data = subprocess.check_output(['qstat']).decode('utf-8')
data = data.split('\n')

running = []
for i, line in enumerate(data):
  line = re.sub('\\s+', '@', line)
  if 1 < i < len(data) - 1:
    #print(line.split('@')[1])
    running.append(line.split('@')[1])

datasets = ['c10', 'c100']
evals = ['600', '1000']
runs = 5

for d in datasets:
  for e in evals:
    for r in range(runs):
      c = f'{d}-{e}-{r+1}'
      if c not in running:
        if not flag: print(c, 'NOT running')
        else: os.system(f'./single.sh {d} {e} 1 {r+1}')

os.system('qstat')