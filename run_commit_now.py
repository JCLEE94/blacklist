#!/usr/bin/env python3
import subprocess
import os

os.chdir('/home/jclee/app/blacklist')
result = subprocess.run(['python3', 'commit_execution_result.py'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)