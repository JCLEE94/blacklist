#!/bin/bash
# Docker Desktop 환경용 통합 배포 스크립트

echo "🐳 Docker Desktop 환경 감지 및 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 1. Docker Desktop 상태 확인
echo -e "\n${YELLOW}[1/7] Docker Desktop 상태 확인...${NC}"
if ! docker info &>/dev/null; then
    echo -e "${RED}❌ Docker Desktop이 실행되지 않았습니다. Docker Desktop을 시작하세요.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Desktop 실행 중${NC}"

# 2. Kubernetes 활성화 확인
echo -e "\n${YELLOW}[2/7] Kubernetes 활성화 확인...${NC}"
if ! kubectl version --short &>/dev/null; then
    echo -e "${RED}❌ Kubernetes가 활성화되지 않았습니다.${NC}"
    echo -e "${YELLOW}Docker Desktop 설정에서 Kubernetes를 활성화하세요.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Kubernetes 활성화됨${NC}"

# 3. 기존 리소스 정리
echo -e "\n${YELLOW}[3/7] 기존 리소스 정리...${NC}"
kubectl delete namespace blacklist --force --grace-period=0 2>/dev/null
sleep 3

# 4. 네임스페이스 및 기본 리소스 생성
echo -e "\n${YELLOW}[4/7] 네임스페이스 및 리소스 생성...${NC}"
kubectl create namespace blacklist

# Registry Secret 생성
kubectl create secret docker-registry regcred \
    --docker-server=registry.jclee.me \
    --docker-username=qws9411 \
    --docker-password=bingogo1 \
    -n blacklist

# 5. Docker Desktop용 간단한 배포 (PVC 없이)
echo -e "\n${YELLOW}[5/7] Docker Desktop용 간단 배포...${NC}"

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blacklist
  namespace: blacklist
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blacklist
  template:
    metadata:
      labels:
        app: blacklist
    spec:
      imagePullSecrets:
      - name: regcred
      containers:
      - name: blacklist
        image: registry.jclee.me/blacklist:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 2541
        env:
        - name: PORT
          value: "2541"
        - name: PYTHONUNBUFFERED
          value: "1"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: blacklist
  namespace: blacklist
spec:
  type: LoadBalancer
  selector:
    app: blacklist
  ports:
  - port: 2541
    targetPort: 2541
    nodePort: 32541
EOF

# 6. 배포 대기 및 모니터링
echo -e "\n${YELLOW}[6/7] 배포 상태 모니터링...${NC}"

maxAttempts=60
attempt=0

while [ $attempt -lt $maxAttempts ]; do
    podStatus=$(kubectl get pods -n blacklist -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    
    if [ "$podStatus" = "Running" ]; then
        echo -e "${GREEN}✅ Pod 실행 중!${NC}"
        break
    elif [ "$podStatus" = "Pending" ]; then
        echo -e "⏳ Pod 시작 중... ($attempt/60)"
    elif [ "$podStatus" = "Failed" ] || [ "$podStatus" = "CrashLoopBackOff" ]; then
        echo -e "${RED}❌ Pod 실패!${NC}"
        kubectl describe pods -n blacklist
        exit 1
    elif [[ "$podStatus" == *"ImagePull"* ]]; then
        echo -e "${RED}❌ 이미지 Pull 실패!${NC}"
        echo -e "${YELLOW}로컬 이미지로 전환 시도...${NC}"
        
        # 로컬 이미지로 전환
        kubectl set image deployment/blacklist blacklist=blacklist:local -n blacklist
        kubectl patch deployment blacklist -n blacklist -p '{"spec":{"template":{"spec":{"containers":[{"name":"blacklist","imagePullPolicy":"Never"}]}}}}'
    fi
    
    ((attempt++))
    sleep 1
done

# 7. 최종 상태 확인
echo -e "\n${YELLOW}[7/7] 최종 상태 확인...${NC}"
kubectl get all -n blacklist

# 서비스 접속 정보
nodePort=$(kubectl get service blacklist -n blacklist -o jsonpath='{.spec.ports[0].nodePort}')

echo -e "\n${GREEN}=====================================
✅ 배포 완료!
=====================================
접속 URL: http://localhost:$nodePort
대시보드: http://localhost:$nodePort/
API 문서: http://localhost:$nodePort/docs
=====================================${NC}\n"

# 로그 스트리밍 옵션
read -p "로그를 보시겠습니까? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl logs -f deployment/blacklist -n blacklist -c blacklist
fi