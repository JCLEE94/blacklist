#!/bin/bash
# Linux/Mac 배포 스크립트

kubectl delete all --all -n blacklist 2>/dev/null
kubectl create namespace blacklist 2>/dev/null

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
      containers:
      - name: blacklist
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: blacklist
  namespace: blacklist
spec:
  selector:
    app: blacklist
  ports:
  - port: 80
  type: LoadBalancer
EOF

sleep 5
kubectl get all -n blacklist