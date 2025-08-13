#!/bin/bash
# systemd 서비스 설정 스크립트

set -e

INSTALL_DIR="${1:-/opt/blacklist}"

echo "⚙️ systemd 서비스 설정 중..."

# systemd 서비스 파일 생성
cat > /etc/systemd/system/blacklist.service << EOF
[Unit]
Description=Blacklist Management System
After=network.target docker.service
Requires=docker.service

[Service]
Type=forking
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker-compose -f $INSTALL_DIR/docker-compose.yml up -d
ExecStop=/usr/bin/docker-compose -f $INSTALL_DIR/docker-compose.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# systemd 데몬 리로드
systemctl daemon-reload

# 서비스 활성화
systemctl enable blacklist

echo "✅ systemd 서비스 설정 완료"
echo "서비스 시작: systemctl start blacklist"
echo "상태 확인: systemctl status blacklist"
