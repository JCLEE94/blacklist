#!/bin/bash
# Blacklist tmux session startup script
# 항상 올바른 디렉토리에서 시작하도록 보장

BLACKLIST_DIR="/home/jclee/app/blacklist"
TMUX_SOCKET="/home/jclee/.tmux/sockets/blacklist"
SESSION_NAME="blacklist"

# 기존 세션 종료
tmux -S "$TMUX_SOCKET" kill-session -t "$SESSION_NAME" 2>/dev/null

# 올바른 디렉토리에서 새 세션 시작
cd "$BLACKLIST_DIR"
tmux -S "$TMUX_SOCKET" new-session -d -s "$SESSION_NAME" -c "$BLACKLIST_DIR"

echo "✅ Blacklist tmux session started in: $BLACKLIST_DIR"