# Trigger CI/CD Build

This file triggers a new CI/CD build with the environment variable priority fix.

Build triggered at: 2025-07-17 17:39:00 KST

## Fix Summary
- CollectionManager now prioritizes COLLECTION_ENABLED environment variable
- Helm values.yaml sets collectionEnabled: false
- ArgoCD deployment sets COLLECTION_ENABLED=false

## Expected Result
After deployment, collection should be disabled by default.