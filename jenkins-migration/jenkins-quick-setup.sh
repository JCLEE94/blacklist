#!/bin/bash

#################################################################################
# Jenkins Quick Setup for Blacklist Project - Local Environment
#################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 Jenkins 로컬 환경 빠른 설정${NC}"
echo -e "${GREEN}========================================${NC}"

# Jenkins 정보
JENKINS_URL="http://localhost:8080"
INITIAL_PASSWORD="ab8a6d316c644bf995fc48d3d878f06e"

echo -e "${YELLOW}📋 Jenkins 설정 정보:${NC}"
echo -e "URL: ${GREEN}${JENKINS_URL}${NC}"
echo -e "초기 관리자 비밀번호: ${GREEN}${INITIAL_PASSWORD}${NC}"

echo ""
echo -e "${YELLOW}📌 다음 단계를 따라주세요:${NC}"
echo ""
echo -e "${GREEN}1. Jenkins 접속:${NC}"
echo -e "   브라우저에서 ${JENKINS_URL} 접속"
echo ""
echo -e "${GREEN}2. 초기 설정:${NC}"
echo -e "   - Administrator password: ${INITIAL_PASSWORD}"
echo -e "   - 'Install suggested plugins' 선택"
echo -e "   - Admin 계정 생성 (예: admin/admin123)"
echo ""
echo -e "${GREEN}3. 플러그인 설치 (Jenkins 관리 → 플러그인 관리):${NC}"
echo -e "   필수 플러그인:"
echo -e "   - Git Plugin"
echo -e "   - GitHub Plugin"
echo -e "   - Pipeline"
echo -e "   - Docker Pipeline"
echo -e "   - Blue Ocean"
echo -e "   - Credentials Binding"
echo -e "   - AnsiColor"
echo ""
echo -e "${GREEN}4. 자격증명 생성 (Jenkins 관리 → Credentials):${NC}"
echo -e "   Docker Registry:"
echo -e "   - ID: registry-jclee-credentials"
echo -e "   - Username: jclee94"
echo -e "   - Password: bingogo1"
echo ""
echo -e "${GREEN}5. Pipeline Job 생성:${NC}"
echo -e "   - New Item → Pipeline"
echo -e "   - Name: blacklist-pipeline"
echo -e "   - Pipeline script from SCM"
echo -e "   - SCM: Git"
echo -e "   - Repository: /home/jclee/app/blacklist"
echo -e "   - Script Path: Jenkinsfile"
echo ""
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}🔧 Docker & Python 설정${NC}"
echo -e "${YELLOW}========================================${NC}"

# Docker 설치 in Jenkins
echo -e "${GREEN}Jenkins 컨테이너에 Docker CLI 설치 중...${NC}"
docker exec jenkins bash -c "
    apt-get update && \
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo 'deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \$(lsb_release -cs) stable' | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli
" || echo -e "${YELLOW}Docker CLI 이미 설치됨${NC}"

# Python 설치
echo -e "${GREEN}Python 3.11 설치 중...${NC}"
docker exec jenkins bash -c "
    apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3-pip && \
    python3.11 -m pip install --upgrade pip
" || echo -e "${YELLOW}Python 이미 설치됨${NC}"

# Trivy 설치
echo -e "${GREEN}Trivy 보안 스캐너 설치 중...${NC}"
docker exec jenkins bash -c "
    apt-get update && \
    apt-get install -y wget apt-transport-https gnupg lsb-release && \
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add - && \
    echo 'deb https://aquasecurity.github.io/trivy-repo/deb \$(lsb_release -sc) main' | tee -a /etc/apt/sources.list.d/trivy.list && \
    apt-get update && \
    apt-get install -y trivy
" || echo -e "${YELLOW}Trivy 이미 설치됨${NC}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 설정 완료!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}🎯 빠른 테스트:${NC}"
echo -e "1. Jenkins 접속: ${JENKINS_URL}"
echo -e "2. blacklist-pipeline Job 실행"
echo -e "3. Blue Ocean에서 파이프라인 확인"
echo ""
echo -e "${GREEN}🔍 유용한 명령어:${NC}"
echo -e "# Jenkins 로그 확인"
echo -e "docker logs -f jenkins"
echo ""
echo -e "# Jenkins 재시작"
echo -e "docker restart jenkins"
echo ""
echo -e "# Pipeline 수동 실행 (CLI)"
echo -e "curl -X POST ${JENKINS_URL}/job/blacklist-pipeline/build"
echo ""
echo -e "${GREEN}========================================${NC}"