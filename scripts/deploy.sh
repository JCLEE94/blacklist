#!/bin/bash
# Linux/Mac 배포 스크립트

# 기존 리소스 정리
kubectl delete all --all -n blacklist 2>/dev/null
kubectl create namespace blacklist 2>/dev/null

# Registry Secret 생성
kubectl delete secret regcred -n blacklist 2>/dev/null
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=registry_username \
  --docker-password=registry_password \
  -n blacklist

# 배포
kubectl apply -k k8s/

sleep 5
kubectl get all -n blacklist