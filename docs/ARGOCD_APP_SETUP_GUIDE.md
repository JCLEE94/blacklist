# ArgoCD 애플리케이션 설정 가이드

## 🚀 ArgoCD 웹 UI에서 Blacklist 애플리케이션 설정

### 1. ArgoCD 접속
- **URL**: https://argo.jclee.me
- **Username**: admin
- **Password**: bingogo1

### 2. 새 애플리케이션 생성 (애플리케이션이 없는 경우)

#### Step 1: NEW APP 클릭
상단의 `+ NEW APP` 버튼 클릭

#### Step 2: 기본 정보 입력
```yaml
Application Name: blacklist
Project Name: default
Sync Policy: Automatic (체크)
  ✓ Prune Resources
  ✓ Self Heal
Sync Options:
  ✓ Auto-Create Namespace
  ✓ Apply Out Of Sync Only
```

#### Step 3: Source 설정
```yaml
Repository URL: https://github.com/JCLEE94/blacklist.git
Revision: main
Path: k8s
```

#### Step 4: Destination 설정
```yaml
Cluster URL: https://kubernetes.default.svc
Namespace: blacklist
```

#### Step 5: Kustomize 설정 (HELM 섹션 아래)
```yaml
Images:
  - registry.jclee.me/blacklist:latest
```

#### Step 6: CREATE 클릭

### 3. 기존 애플리케이션 수정 (애플리케이션이 있는 경우)

#### A. 애플리케이션 상태 확인
1. `blacklist` 애플리케이션 클릭
2. 상단 상태 확인:
   - **Sync Status**: Synced ✅ 또는 OutOfSync ⚠️
   - **Health Status**: Healthy ✅ 또는 Degraded ❌

#### B. 동기화 문제 해결
**OutOfSync** 상태인 경우:
1. **SYNC** 버튼 클릭
2. **SYNCHRONIZE** 클릭
3. 옵션 선택:
   - ✓ Prune (불필요한 리소스 제거)
   - ✓ Force (강제 동기화)
   - ✓ Apply Only (동기화되지 않은 것만)

#### C. 애플리케이션 설정 수정
1. **APP DETAILS** 클릭
2. **EDIT** 버튼 클릭
3. 필요한 설정 변경:

**이미지 설정 확인/수정**:
```yaml
Source:
  Path: k8s
  Repository: https://github.com/JCLEE94/blacklist.git
  Target Revision: main

Kustomize:
  Images:
    - registry.jclee.me/blacklist:latest  # ⚠️ 중요: 이 부분이 올바른지 확인
```

### 4. Image Updater 설정 확인

#### A. Annotations 확인
**APP DETAILS** → **MANIFEST** 탭에서 확인:
```yaml
metadata:
  annotations:
    argocd-image-updater.argoproj.io/image-list: blacklist=registry.jclee.me/blacklist:latest
    argocd-image-updater.argoproj.io/blacklist.update-strategy: latest
    argocd-image-updater.argoproj.io/write-back-method: git
```

#### B. Image Updater 로그 확인
터미널에서:
```bash
kubectl logs -n argocd deployment/argocd-image-updater --tail=50 | grep blacklist
```

### 5. 문제 해결

#### A. Health Status가 Degraded인 경우
1. 애플리케이션 클릭 → 빨간색 리소스 확인
2. 문제가 있는 리소스 클릭 → **EVENTS** 탭 확인
3. 일반적인 문제:
   - `ImagePullBackOff`: 이미지를 찾을 수 없음
   - `CrashLoopBackOff`: 컨테이너가 계속 재시작됨
   - `Pending`: 리소스 부족 또는 스케줄링 문제

#### B. Sync가 실패하는 경우
1. **SYNC** → **SYNCHRONIZE** → **DRY RUN** 먼저 실행
2. 에러 메시지 확인
3. 필요시 **FORCE** 옵션으로 강제 동기화

#### C. 수동으로 이미지 업데이트
**APP DETAILS** → **PARAMETERS** 탭:
1. **IMAGES** 섹션 찾기
2. 이미지 태그를 최신으로 변경
3. **SAVE** 클릭

### 6. CLI로 설정 (대안)

웹 UI 대신 CLI 사용:
```bash
# 로그인
argocd login argo.jclee.me --username admin --password bingogo1 --grpc-web

# 애플리케이션 생성
argocd app create blacklist \
  --repo https://github.com/JCLEE94/blacklist.git \
  --path k8s \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace blacklist \
  --sync-policy automated \
  --self-heal \
  --auto-prune

# 동기화
argocd app sync blacklist

# 상태 확인
argocd app get blacklist
```

### 7. 배포 확인

성공적으로 배포되면:
1. ArgoCD UI에서 모든 리소스가 녹색으로 표시됨
2. 다음 URL에서 애플리케이션 접근 가능:
   - https://blacklist.jclee.me
   - https://blacklist.jclee.me/health

### 8. 추가 팁

#### 자동 동기화 설정
1. **APP DETAILS** → **SYNC POLICY** → **ENABLE AUTO-SYNC**
2. 옵션 활성화:
   - ✓ Prune Resources (Git에서 삭제된 리소스 자동 제거)
   - ✓ Self Heal (수동 변경사항 자동 복구)

#### 알림 설정
1. **Settings** → **Notifications**
2. Slack/Email 등 알림 채널 설정
3. 동기화 실패 시 알림 받기

### 9. 모니터링

#### ArgoCD 대시보드에서 확인할 사항:
- **Last Sync**: 마지막 동기화 시간
- **Sync Revision**: 현재 배포된 Git 커밋
- **Health**: 모든 리소스의 상태
- **Resources**: 배포된 Kubernetes 리소스 목록

#### 실시간 로그 확인:
1. Pod 리소스 클릭
2. **LOGS** 탭 선택
3. 실시간 로그 스트리밍 확인