package kubernetes.admission

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# 컨테이너가 루트로 실행되는 것을 방지
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.runAsUser == 0
    msg := sprintf("Container %s is running as root user", [container.name])
}

# 특권 컨테이너 방지
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf("Container %s is running in privileged mode", [container.name])
}

# 리소스 제한이 없는 컨테이너 방지
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits
    msg := sprintf("Container %s has no resource limits", [container.name])
}

# 이미지 태그가 latest인 경우 방지
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    endswith(container.image, ":latest")
    msg := sprintf("Container %s uses 'latest' tag", [container.name])
}

# 신뢰할 수 없는 레지스트리 방지
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not startswith(container.image, "registry.jclee.me/")
    not startswith(container.image, "docker.io/library/")
    msg := sprintf("Container %s uses untrusted image registry", [container.name])
}