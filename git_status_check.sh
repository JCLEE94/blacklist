#!/bin/bash
# Temporary script to check git status
cd /home/jclee/app/blacklist
git status --porcelain | head -20
echo "---"
git status