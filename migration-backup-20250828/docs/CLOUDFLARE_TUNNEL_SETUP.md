# Cloudflare Tunnel 설정 가이드

이 문서는 Blacklist 서비스를 Cloudflare Zero Trust를 통해 외부에 안전하게 노출하는 방법을 설명합니다.

## 개요

Cloudflare Tunnel을 사용하면:
- 공인 IP 없이도 서비스를 외부에 노출 가능
- 방화벽 포트 개방 불필요
- Zero Trust 보안 정책 적용 가능
- SSL/TLS 자동 처리

## 사전 요구사항

1. Cloudflare 계정 (무료 플랜 가능)
2. Cloudflare에 등록된 도메인
3. Kubernetes 클러스터에 배포된 Blacklist 서비스

## 자동 설정 (권장)

모든 설정이 자동화되어 있습니다:

```bash
# 배포 시 자동으로 DNS 레코드 생성 및 Tunnel 설정
./scripts/k8s-management.sh init

# 또는 CI/CD 파이프라인 사용
git push origin main
```

자동으로 설정되는 항목:
- DNS 레코드: blacklist.jclee.me → Cloudflare Tunnel
- Cloudflare Tunnel 토큰 및 연결
- Kubernetes Secret 및 Deployment

## 설정 단계 (수동)

### 1. Cloudflare Zero Trust 대시보드에서 터널 생성

1. [Cloudflare Zero Trust 대시보드](https://one.dash.cloudflare.com/) 접속
2. **Access** > **Tunnels** 메뉴로 이동
3. **Create a tunnel** 클릭
4. 터널 이름 입력 (예: `blacklist-tunnel`)
5. 생성된 토큰 복사 (한 번만 표시되므로 안전하게 보관)

### 2. 자동 설정 (권장)

#### 방법 1: CI/CD 파이프라인 통합

GitHub Actions를 사용하는 경우:

```bash
# GitHub Secrets에 토큰 추가
# Settings > Secrets and variables > Actions
# CLOUDFLARE_TUNNEL_TOKEN = <복사한 토큰>
```

파이프라인이 자동으로 cloudflared를 배포합니다.

#### 방법 2: 스크립트를 통한 수동 배포

```bash
# 환경 변수 설정
export CLOUDFLARE_TUNNEL_TOKEN="<복사한 토큰>"
export CLOUDFLARE_HOSTNAME="blacklist.yourdomain.com"

# Cloudflare Tunnel 배포
./scripts/setup/cloudflared-k8s-setup.sh deploy
```

#### 방법 3: k8s-management.sh 통합

```bash
# 초기 설정 시 cloudflared 포함
ENABLE_CLOUDFLARED=true ./scripts/k8s-management.sh init

# 또는 기존 배포에 추가
ENABLE_CLOUDFLARED=true CLOUDFLARE_TUNNEL_TOKEN="<토큰>" ./scripts/deploy.sh
```

### 3. 수동 설정 (고급)

#### 3.1 로컬 머신에 cloudflared 설치

```bash
# Ubuntu/Debian
sudo ./scripts/setup/install-cloudflared.sh install

# 설치 확인
cloudflared --version
```

#### 3.2 Kubernetes에 배포

```bash
# Secret 생성
kubectl create secret generic cloudflared-secret \
  --from-literal=token="<CLOUDFLARE_TUNNEL_TOKEN>" \
  -n blacklist

# Deployment 적용
kubectl apply -f k8s/cloudflared-deployment.yaml

# 상태 확인
kubectl get pods -l app=cloudflared -n blacklist
```

## 설정 옵션

### 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare 터널 토큰 | (필수) |
| `CLOUDFLARE_HOSTNAME` | 외부 접속 도메인 | blacklist.yourdomain.com |
| `NODE_PORT` | NodePort 서비스 포트 | 32452 |
| `NAMESPACE` | Kubernetes 네임스페이스 | blacklist |

### 고급 설정

`k8s/cloudflared-deployment.yaml` 파일을 수정하여 추가 설정 가능:

```yaml
# 예: 여러 호스트명 라우팅
ingress:
  - hostname: blacklist.example.com
    service: http://blacklist-nodeport:2541
  - hostname: api.example.com
    service: http://blacklist-nodeport:2541
    path: /api
  - service: http_status:404
```

## 모니터링 및 관리

### 상태 확인

```bash
# Pod 상태
kubectl get pods -l app=cloudflared -n blacklist

# 로그 확인
kubectl logs -l app=cloudflared -n blacklist -f

# 터널 상태 (Cloudflare 대시보드)
https://one.dash.cloudflare.com/ > Access > Tunnels
```

### 문제 해결

```bash
# 재시작
kubectl rollout restart deployment/cloudflared -n blacklist

# 상세 진단
./scripts/setup/cloudflared-k8s-setup.sh status

# 로그 분석
./scripts/setup/cloudflared-k8s-setup.sh logs
```

### 삭제

```bash
# Cloudflare Tunnel 제거
./scripts/setup/cloudflared-k8s-setup.sh delete

# 또는 수동으로
kubectl delete deployment cloudflared -n blacklist
kubectl delete secret cloudflared-secret -n blacklist
kubectl delete configmap cloudflared-config -n blacklist
```

## 보안 고려사항

1. **토큰 보안**: Cloudflare 터널 토큰은 절대 공개 저장소에 커밋하지 마세요
2. **Access 정책**: Cloudflare Zero Trust에서 접근 정책 설정 가능
3. **네트워크 격리**: cloudflared Pod는 최소 권한으로 실행

## Zero Trust 정책 설정 (선택적)

Cloudflare Zero Trust 대시보드에서 추가 보안 정책 설정:

1. **Access** > **Applications** 메뉴
2. **Add an application** 클릭
3. **Self-hosted** 선택
4. 애플리케이션 설정:
   - Name: Blacklist Service
   - Domain: blacklist.yourdomain.com
5. 정책 설정:
   - 이메일 인증
   - IP 범위 제한
   - 디바이스 인증

## 아키텍처

```
[인터넷] --> [Cloudflare Edge] --> [Cloudflare Tunnel] 
                                           |
                                           v
                              [cloudflared Pod in K8s]
                                           |
                                           v
                              [Blacklist NodePort Service]
                                           |
                                           v
                                   [Blacklist Pods]
```

## 자주 묻는 질문

**Q: 무료로 사용 가능한가요?**
A: 네, Cloudflare Zero Trust는 50명까지 무료로 사용 가능합니다.

**Q: 여러 클러스터에 배포 가능한가요?**
A: 네, 각 클러스터마다 별도의 터널을 생성하거나 로드 밸런싱 설정이 가능합니다.

**Q: 기존 Ingress와 함께 사용 가능한가요?**
A: 네, Cloudflare Tunnel은 독립적으로 동작하므로 기존 Ingress 설정과 충돌하지 않습니다.

## 관련 문서

- [Cloudflare Tunnel 공식 문서](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Kubernetes 배포 가이드](./k8s/README.md)
- [CI/CD 파이프라인 설정](./.github/workflows/README.md)