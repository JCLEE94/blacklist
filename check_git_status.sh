#!/bin/bash
cd /home/jclee/app/blacklist
echo "📊 현재 Git 상태:"
git status --short
echo ""
echo "📝 준비된 커밋 메시지:"
cat commit_message.txt