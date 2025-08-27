#!/bin/bash

#################################################################################
# Jenkins 즉시 설정 스크립트
#################################################################################

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

JENKINS_URL="http://localhost:9999"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 Jenkins Job 생성 중...${NC}"
echo -e "${GREEN}========================================${NC}"

# Jenkins CLI 다운로드
echo -e "${YELLOW}Jenkins CLI 다운로드 중...${NC}"
wget -q ${JENKINS_URL}/jnlpJars/jenkins-cli.jar -O /tmp/jenkins-cli.jar

# Job 생성 (인증 없이 시도)
echo -e "${YELLOW}Job 생성 시도 중...${NC}"
java -jar /tmp/jenkins-cli.jar -s ${JENKINS_URL} create-job blacklist-pipeline < jenkins-job-config.xml 2>/dev/null || {
    echo -e "${YELLOW}⚠️  인증이 필요합니다. 수동으로 Job을 생성해주세요.${NC}"
    echo ""
    echo -e "${GREEN}수동 설정 방법:${NC}"
    echo "1. Jenkins 접속: ${JENKINS_URL}"
    echo "2. New Item 클릭"
    echo "3. Name: blacklist-pipeline"
    echo "4. Type: Pipeline 선택"
    echo "5. OK 클릭"
    echo "6. Pipeline 섹션에서 아래 스크립트 복사:"
    echo ""
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
        
        stage('Build Docker') {
            steps {
                sh """
                    cd ${PROJECT_PATH}
                    docker build -t ${REGISTRY}/${IMAGE_NAME}:latest .
                    docker build -t ${REGISTRY}/${IMAGE_NAME}:\$(date +%Y%m%d-%H%M%S) .
                """
            }
        }
        
        stage('Push to Registry') {
            steps {
                sh """
                    echo bingogo1 | docker login ${REGISTRY} -u jclee94 --password-stdin
                    docker push ${REGISTRY}/${IMAGE_NAME}:latest
                    docker logout ${REGISTRY}
                """
            }
        }
        
        stage('Deploy') {
            steps {
                sh """
                    cd ${PROJECT_PATH}
                    docker-compose down || true
                    docker-compose pull
                    docker-compose up -d
                    sleep 10
                    curl -f http://localhost:32542/health || exit 1
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
    echo "7. Save 클릭"
}

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Jenkins 설정 준비 완료!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}빌드 실행 방법:${NC}"
echo "1. Jenkins UI: ${JENKINS_URL}/job/blacklist-pipeline"
echo "2. Build Now 클릭"
echo ""
echo "또는 CLI로 실행:"
echo "curl -X POST ${JENKINS_URL}/job/blacklist-pipeline/build"
echo ""
echo -e "${GREEN}========================================${NC}"