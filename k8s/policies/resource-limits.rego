package kubernetes.admission

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# CPU 제한 확인
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.cpu
    msg := sprintf("Container %s has no CPU limits", [container.name])
}

# 메모리 제한 확인
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %s has no memory limits", [container.name])
}

# CPU 요청 확인
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.requests.cpu
    msg := sprintf("Container %s has no CPU requests", [container.name])
}

# 메모리 요청 확인
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.requests.memory
    msg := sprintf("Container %s has no memory requests", [container.name])
}