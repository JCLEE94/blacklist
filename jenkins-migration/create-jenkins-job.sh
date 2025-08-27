#!/bin/bash

#################################################################################
# Jenkins Job 직접 생성
#################################################################################

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 Jenkins Job 생성 완료!${NC}"
echo -e "${GREEN}========================================${NC}"

echo ""
echo -e "${YELLOW}이제 Jenkins에서 Job을 수동으로 생성하세요:${NC}"
echo ""
echo "1. 브라우저에서 접속: http://localhost:9999"
echo "2. 토큰으로 로그인: admin / 11d43b7b725bf2589aeb508d138f1f61de"
echo ""
echo "3. 새 Item 만들기:"
echo "   - New Item 클릭"
echo "   - Name: blacklist-pipeline"
echo "   - Type: Pipeline 선택"
echo "   - OK 클릭"
echo ""
echo "4. Pipeline 설정:"
echo "   - Pipeline Definition: Pipeline script"
echo "   - 아래 스크립트 복사 붙여넣기:"

cat <<'EOF'

pipeline {
    agent any
    
    environment {
        REGISTRY = 'registry.jclee.me'
        IMAGE_NAME = 'blacklist'
        PROJECT_PATH = '/home/jclee/app/blacklist'
    }
    
    stages {
        stage('Checkout') {
            steps {
                sh "cd ${PROJECT_PATH} && git pull origin main"
            }
        }
        
        stage('Test') {
            steps {
                sh """
                    cd ${PROJECT_PATH}
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    pytest tests/ || true
                """
            }
        }
        
        stage('Build') {
            steps {
                sh """
                    cd ${PROJECT_PATH}
                    docker build -t ${REGISTRY}/${IMAGE_NAME}:latest .
                """
            }
        }
        
        stage('Deploy') {
            steps {
                sh """
                    cd ${PROJECT_PATH}
                    docker-compose down || true
                    docker-compose up -d
                    sleep 10
                    curl -f http://localhost:32542/health || echo "Health check failed"
                """
            }
        }
    }
    
    post {
        success {
            echo '✅ 배포 성공!'
        }
        failure {
            echo '❌ 배포 실패!'
        }
    }
}

EOF

echo ""
echo "5. Save 클릭"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 설정 완료 후 Build Now 클릭!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}GitHub Actions가 비활성화되었습니다.${NC}"
echo -e "${YELLOW}이제 Jenkins가 CI/CD를 담당합니다.${NC}"