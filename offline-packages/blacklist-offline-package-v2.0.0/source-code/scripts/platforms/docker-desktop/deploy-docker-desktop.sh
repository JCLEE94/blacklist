#!/bin/bash
# Docker Desktop 환경용 통합 배포 스크립트 - 다중 환경 지원

echo "🐳 Kubernetes 환경 감지 및 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 환경 변수 및 설정
NAMESPACE=${NAMESPACE:-blacklist}
REGISTRY=${REGISTRY:-registry.jclee.me}
REGISTRY_USER=${REGISTRY_USER:-qws9411}
REGISTRY_PASS=${REGISTRY_PASS:-bingogo1}
IMAGE_TAG=${IMAGE_TAG:-latest}
NODE_PORT=${NODE_PORT:-32541}
DEPLOYMENT_TIMEOUT=${DEPLOYMENT_TIMEOUT:-300}
USE_LOCAL_IMAGE=${USE_LOCAL_IMAGE:-false}
FORCE_RECREATE=${FORCE_RECREATE:-true}

# 프록시 설정 감지
if [ -n "$HTTP_PROXY" ] || [ -n "$http_proxy" ]; then
    echo -e "${YELLOW}🔧 프록시 환경 감지: ${HTTP_PROXY:-$http_proxy}${NC}"
    export PROXY_ENABLED=true
fi

# 0. Kubernetes 종류 감지
echo -e "\n${YELLOW}[0/8] Kubernetes 환경 감지...${NC}"
K8S_CONTEXT=$(kubectl config current-context 2>/dev/null)
K8S_TYPE="unknown"

if [[ "$K8S_CONTEXT" == *"docker-desktop"* ]]; then
    K8S_TYPE="docker-desktop"
    echo -e "${BLUE}📦 Docker Desktop Kubernetes 감지${NC}"
elif [[ "$K8S_CONTEXT" == *"minikube"* ]]; then
    K8S_TYPE="minikube"
    echo -e "${BLUE}🔧 Minikube 감지${NC}"
elif [[ "$K8S_CONTEXT" == *"kind"* ]]; then
    K8S_TYPE="kind"
    echo -e "${BLUE}🐋 Kind 클러스터 감지${NC}"
elif [[ "$K8S_CONTEXT" == *"k3s"* ]] || [[ "$K8S_CONTEXT" == *"k3d"* ]]; then
    K8S_TYPE="k3s"
    echo -e "${BLUE}⚡ K3s/K3d 클러스터 감지${NC}"
elif [[ "$K8S_CONTEXT" == *"rancher"* ]]; then
    K8S_TYPE="rancher"
    echo -e "${BLUE}🐄 Rancher Desktop 감지${NC}"
else
    echo -e "${YELLOW}⚠️  알 수 없는 Kubernetes 환경: $K8S_CONTEXT${NC}"
    echo -e "${CYAN}계속 진행합니다...${NC}"
fi

# 1. Docker/Container Runtime 상태 확인
echo -e "\n${YELLOW}[1/8] Container Runtime 상태 확인...${NC}"
if command -v docker &>/dev/null && docker info &>/dev/null; then
    echo -e "${GREEN}✅ Docker 실행 중${NC}"
    CONTAINER_RUNTIME="docker"
elif command -v podman &>/dev/null && podman info &>/dev/null; then
    echo -e "${GREEN}✅ Podman 실행 중${NC}"
    CONTAINER_RUNTIME="podman"
elif command -v nerdctl &>/dev/null && nerdctl info &>/dev/null; then
    echo -e "${GREEN}✅ Containerd (nerdctl) 실행 중${NC}"
    CONTAINER_RUNTIME="nerdctl"
else
    echo -e "${RED}❌ Container Runtime이 실행되지 않았습니다.${NC}"
    exit 1
fi

# 2. Kubernetes 활성화 확인
echo -e "\n${YELLOW}[2/8] Kubernetes 활성화 확인...${NC}"
if ! kubectl version --short &>/dev/null; then
    echo -e "${RED}❌ Kubernetes가 활성화되지 않았습니다.${NC}"
    
    # 환경별 안내
    case "$K8S_TYPE" in
        "docker-desktop")
            echo -e "${YELLOW}Docker Desktop 설정에서 Kubernetes를 활성화하세요.${NC}"
            ;;
        "minikube")
            echo -e "${YELLOW}minikube start 명령을 실행하세요.${NC}"
            ;;
        "kind")
            echo -e "${YELLOW}kind create cluster 명령을 실행하세요.${NC}"
            ;;
        *)
            echo -e "${YELLOW}Kubernetes 클러스터를 시작하세요.${NC}"
            ;;
    esac
    exit 1
fi
echo -e "${GREEN}✅ Kubernetes 활성화됨${NC}"

# Storage Class 확인 및 설정
echo -e "\n${YELLOW}[2.5/8] Storage Class 확인...${NC}"
STORAGE_CLASSES=$(kubectl get storageclass -o name 2>/dev/null | wc -l)
if [ "$STORAGE_CLASSES" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Storage Class가 없습니다. hostPath 사용${NC}"
    USE_HOSTPATH=true
else
    DEFAULT_SC=$(kubectl get storageclass -o json | jq -r '.items[] | select(.metadata.annotations."storageclass.kubernetes.io/is-default-class"=="true") | .metadata.name' 2>/dev/null)
    if [ -n "$DEFAULT_SC" ]; then
        echo -e "${GREEN}✅ 기본 Storage Class: $DEFAULT_SC${NC}"
        STORAGE_CLASS=$DEFAULT_SC
    else
        FIRST_SC=$(kubectl get storageclass -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        echo -e "${YELLOW}⚠️  기본 Storage Class 없음. '$FIRST_SC' 사용${NC}"
        STORAGE_CLASS=$FIRST_SC
    fi
fi

# 3. 기존 리소스 정리
echo -e "\n${YELLOW}[3/8] 기존 리소스 정리...${NC}"

# 네임스페이스가 Terminating 상태인지 확인
NS_STATUS=$(kubectl get namespace $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null)
if [ "$NS_STATUS" = "Terminating" ]; then
    echo -e "${YELLOW}⚠️  네임스페이스가 Terminating 상태입니다. 강제 삭제 시도...${NC}"
    # Finalizers 제거
    kubectl patch namespace $NAMESPACE -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null
    kubectl patch namespace $NAMESPACE -p '{"spec":{"finalizers":null}}' --type=merge 2>/dev/null
    # API 리소스 정리
    kubectl api-resources --verbs=list --namespaced -o name | xargs -n 1 kubectl get --show-kind --ignore-not-found -n $NAMESPACE 2>/dev/null | grep -v "No resources found" | awk '{print $1}' | xargs -I {} kubectl delete {} -n $NAMESPACE --force --grace-period=0 2>/dev/null
fi

# 일반 삭제
kubectl delete namespace $NAMESPACE --force --grace-period=0 2>/dev/null

# 완전 삭제 대기
echo -e "${CYAN}네임스페이스 삭제 대기 중...${NC}"
for i in {1..30}; do
    if ! kubectl get namespace $NAMESPACE &>/dev/null; then
        echo -e "${GREEN}✅ 네임스페이스 삭제 완료${NC}"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# 4. 네임스페이스 및 기본 리소스 생성
echo -e "\n${YELLOW}[4/8] 네임스페이스 및 리소스 생성...${NC}"
kubectl create namespace $NAMESPACE

# Resource Quota 설정 (리소스 제한 환경용)
if [ "$K8S_TYPE" = "docker-desktop" ] || [ "$K8S_TYPE" = "minikube" ] || [ "$K8S_TYPE" = "kind" ]; then
    echo -e "${CYAN}리소스 제한 설정 중...${NC}"
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: $NAMESPACE-quota
  namespace: $NAMESPACE
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
    persistentvolumeclaims: "10"
EOF
fi

# Registry Secret 생성
echo -e "${CYAN}Registry Secret 생성 중...${NC}"
kubectl delete secret regcred -n $NAMESPACE 2>/dev/null
kubectl create secret docker-registry regcred \
    --docker-server=$REGISTRY \
    --docker-username=$REGISTRY_USER \
    --docker-password=$REGISTRY_PASS \
    -n $NAMESPACE

# 5. 로컬 이미지 빌드 옵션
echo -e "\n${YELLOW}[5/8] 이미지 준비...${NC}"

if [ "$USE_LOCAL_IMAGE" = "true" ] || [ "$K8S_TYPE" = "minikube" ]; then
    echo -e "${CYAN}로컬 이미지 빌드 중...${NC}"
    
    # Minikube docker env 설정
    if [ "$K8S_TYPE" = "minikube" ]; then
        eval $(minikube docker-env)
    fi
    
    # 로컬 빌드
    if [ -f "Dockerfile" ] || [ -f "deployment/Dockerfile" ]; then
        DOCKERFILE_PATH="Dockerfile"
        [ -f "deployment/Dockerfile" ] && DOCKERFILE_PATH="deployment/Dockerfile"
        
        $CONTAINER_RUNTIME build -t blacklist:local -f $DOCKERFILE_PATH .
        echo -e "${GREEN}✅ 로컬 이미지 빌드 완료${NC}"
        IMAGE_PULL_POLICY="Never"
        IMAGE_NAME="blacklist:local"
    else
        echo -e "${YELLOW}⚠️  Dockerfile을 찾을 수 없습니다. Registry 이미지 사용${NC}"
        IMAGE_PULL_POLICY="Always"
        IMAGE_NAME="$REGISTRY/blacklist:$IMAGE_TAG"
    fi
else
    IMAGE_PULL_POLICY="Always"
    IMAGE_NAME="$REGISTRY/blacklist:$IMAGE_TAG"
fi

# 6. 배포 매니페스트 생성
echo -e "\n${YELLOW}[6/8] 배포 매니페스트 생성...${NC}"

# Service Type 결정
case "$K8S_TYPE" in
    "kind")
        SERVICE_TYPE="NodePort"
        echo -e "${CYAN}Kind 클러스터: NodePort 사용${NC}"
        ;;
    "minikube")
        SERVICE_TYPE="NodePort"
        echo -e "${CYAN}Minikube: NodePort 사용${NC}"
        ;;
    *)
        SERVICE_TYPE="LoadBalancer"
        ;;
esac

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
      initContainers:
      - name: init-permissions
        image: busybox:latest
        command: ['sh', '-c', 'mkdir -p /app/instance && chmod 777 /app/instance']
        volumeMounts:
        - name: instance-data
          mountPath: /app/instance
      containers:
      - name: blacklist
        image: $IMAGE_NAME
        imagePullPolicy: $IMAGE_PULL_POLICY
        ports:
        - containerPort: 2541
        env:
        - name: PORT
          value: "2541"
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: REGTECH_USERNAME
          value: "nextrade"
        - name: REGTECH_PASSWORD
          value: "Sprtmxm1@3"
        - name: SECUDIUM_USERNAME
          value: "nextrade"
        - name: SECUDIUM_PASSWORD
          value: "Sprtmxm1@3"
        volumeMounts:
        - name: instance-data
          mountPath: /app/instance
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: instance-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: blacklist
  namespace: blacklist
spec:
  type: $SERVICE_TYPE
  selector:
    app: blacklist
  ports:
  - port: 2541
    targetPort: 2541
    nodePort: $NODE_PORT
EOF

# 7. 배포 대기 및 모니터링
echo -e "\n${YELLOW}[7/8] 배포 상태 모니터링...${NC}"

maxAttempts=$((DEPLOYMENT_TIMEOUT / 5))
attempt=0
lastStatus=""
imagePullError=false

while [ $attempt -lt $maxAttempts ]; do
    # Pod 상태 체크
    podInfo=$(kubectl get pods -n $NAMESPACE -l app=blacklist -o json 2>/dev/null)
    podCount=$(echo "$podInfo" | jq '.items | length')
    
    if [ "$podCount" -gt 0 ]; then
        podStatus=$(echo "$podInfo" | jq -r '.items[0].status.phase')
        containerStatuses=$(echo "$podInfo" | jq -r '.items[0].status.containerStatuses[0].state | keys[0]')
        
        # 상태 변화 감지
        if [ "$podStatus" != "$lastStatus" ]; then
            echo -e "\n${CYAN}Pod 상태: $podStatus${NC}"
            lastStatus="$podStatus"
        fi
        
        # 상세 상태 확인
        case "$containerStatuses" in
            "running")
                # 실제 애플리케이션 준비 상태 확인
                ready=$(echo "$podInfo" | jq -r '.items[0].status.containerStatuses[0].ready')
                if [ "$ready" = "true" ]; then
                    echo -e "${GREEN}✅ Pod 준비 완료!${NC}"
                    break
                else
                    echo -ne "\r⏳ 애플리케이션 초기화 중... ($attempt/$maxAttempts)"
                fi
                ;;
            "waiting")
                reason=$(echo "$podInfo" | jq -r '.items[0].status.containerStatuses[0].state.waiting.reason')
                message=$(echo "$podInfo" | jq -r '.items[0].status.containerStatuses[0].state.waiting.message')
                
                case "$reason" in
                    "ErrImagePull"|"ImagePullBackOff")
                        if [ "$imagePullError" = "false" ]; then
                            echo -e "\n${RED}❌ 이미지 Pull 실패: $message${NC}"
                            echo -e "${YELLOW}로컬 이미지로 전환 시도...${NC}"
                            
                            # 로컬 이미지로 전환
                            kubectl set image deployment/blacklist blacklist=blacklist:local -n $NAMESPACE
                            kubectl patch deployment blacklist -n $NAMESPACE -p '{"spec":{"template":{"spec":{"containers":[{"name":"blacklist","imagePullPolicy":"Never"}]}}}}'
                            imagePullError=true
                        fi
                        ;;
                    "CrashLoopBackOff")
                        echo -e "\n${RED}❌ 컨테이너 충돌 반복!${NC}"
                        echo -e "${YELLOW}최근 로그:${NC}"
                        kubectl logs -n $NAMESPACE -l app=blacklist --tail=20
                        exit 1
                        ;;
                    *)
                        echo -ne "\r⏳ 대기 중: $reason ($attempt/$maxAttempts)"
                        ;;
                esac
                ;;
            "terminated")
                reason=$(echo "$podInfo" | jq -r '.items[0].status.containerStatuses[0].state.terminated.reason')
                exitCode=$(echo "$podInfo" | jq -r '.items[0].status.containerStatuses[0].state.terminated.exitCode')
                echo -e "\n${RED}❌ 컨테이너 종료: $reason (Exit: $exitCode)${NC}"
                kubectl logs -n $NAMESPACE -l app=blacklist --tail=50
                exit 1
                ;;
        esac
        
        # Pending 상태 원인 분석
        if [ "$podStatus" = "Pending" ]; then
            # PVC 바인딩 확인
            pvcIssue=$(kubectl describe pod -n $NAMESPACE -l app=blacklist | grep -i "persistentvolumeclaim" | grep -i "not found\|pending")
            if [ -n "$pvcIssue" ]; then
                echo -e "\n${YELLOW}⚠️  PVC 바인딩 문제 감지. EmptyDir로 전환...${NC}"
                kubectl patch deployment blacklist -n $NAMESPACE --type='json' -p='[{"op": "remove", "path": "/spec/template/spec/volumes"}]' 2>/dev/null
                kubectl patch deployment blacklist -n $NAMESPACE --type='json' -p='[{"op": "add", "path": "/spec/template/spec/volumes", "value": [{"name":"instance-data","emptyDir":{}}]}]'
            fi
            
            # 스케줄링 문제 확인
            events=$(kubectl get events -n $NAMESPACE --field-selector involvedObject.name=blacklist --sort-by='.lastTimestamp' | tail -5)
            if echo "$events" | grep -q "FailedScheduling"; then
                echo -e "\n${YELLOW}⚠️  스케줄링 문제 감지${NC}"
                echo "$events"
            fi
        fi
    else
        echo -ne "\r⏳ Pod 생성 대기 중... ($attempt/$maxAttempts)"
    fi
    
    ((attempt++))
    sleep 5
done

if [ $attempt -ge $maxAttempts ]; then
    echo -e "\n${RED}❌ 배포 시간 초과!${NC}"
    echo -e "${YELLOW}문제 진단:${NC}"
    kubectl describe deployment blacklist -n $NAMESPACE
    kubectl describe pods -n $NAMESPACE -l app=blacklist
    exit 1
fi

# 8. 최종 상태 확인 및 접속 정보
echo -e "\n${YELLOW}[8/8] 최종 상태 확인...${NC}"
kubectl get all -n $NAMESPACE

# 서비스 접속 정보
nodePort=$(kubectl get service blacklist -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')

# 환경별 접속 URL 안내
case "$K8S_TYPE" in
    "minikube")
        MINIKUBE_IP=$(minikube ip)
        ACCESS_URL="http://$MINIKUBE_IP:$nodePort"
        echo -e "\n${YELLOW}Minikube 터널링이 필요할 수 있습니다:${NC}"
        echo -e "${CYAN}minikube service blacklist -n $NAMESPACE${NC}"
        ;;
    "kind")
        ACCESS_URL="http://localhost:$nodePort"
        echo -e "\n${YELLOW}Kind 포트 포워딩이 필요할 수 있습니다:${NC}"
        echo -e "${CYAN}kubectl port-forward -n $NAMESPACE service/blacklist $nodePort:2541${NC}"
        ;;
    *)
        ACCESS_URL="http://localhost:$nodePort"
        ;;
esac

echo -e "\n${GREEN}=====================================
✅ 배포 완료!
=====================================
🌍 Kubernetes: $K8S_TYPE
📦 Container Runtime: $CONTAINER_RUNTIME
🔗 접속 URL: $ACCESS_URL
📊 대시보드: $ACCESS_URL/
📚 API 문서: $ACCESS_URL/docs
=====================================

유용한 명령어:
- Pod 로그: kubectl logs -f deployment/blacklist -n $NAMESPACE
- Pod 상태: kubectl get pods -n $NAMESPACE -w
- 서비스 확인: kubectl get svc -n $NAMESPACE
- 이벤트 확인: kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'
=====================================${NC}\n"

# 자동 초기 수집 확인
echo -e "${YELLOW}🔄 자동 초기 수집 상태 확인 중...${NC}"
sleep 5
collectionStatus=$(curl -s $ACCESS_URL/api/collection/status 2>/dev/null)
if [ -n "$collectionStatus" ]; then
    echo -e "${GREEN}✅ 수집 서비스 정상 작동${NC}"
    echo "$collectionStatus" | jq '.' 2>/dev/null || echo "$collectionStatus"
else
    echo -e "${YELLOW}⚠️  수집 서비스 확인 불가 (네트워크 설정 확인 필요)${NC}"
fi

# 로그 스트리밍 옵션
if [ -t 0 ]; then  # 인터랙티브 모드인 경우만
    read -p "로그를 보시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl logs -f deployment/blacklist -n $NAMESPACE -c blacklist
    fi
fi