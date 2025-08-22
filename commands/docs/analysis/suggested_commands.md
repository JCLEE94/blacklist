# Suggested Commands

## Git Operations
```bash
git status                 # Check working tree status
git add .                  # Stage all changes
git commit -m "message"    # Commit with message
git push                   # Push to remote
```

## MCP Server Management
```bash
# No specific commands needed - MCP servers are managed via mcp.json configuration
# Servers start automatically when Claude Code connects
```

## File Operations
```bash
ls -la                     # List files with details
find . -name "*.md"        # Find specific file types
grep -r "pattern" .        # Search for patterns
cat filename               # View file contents
```

## Docker Operations (when Docker MCP is used)
```bash
docker ps                  # List running containers
docker images              # List available images
docker build -t name .     # Build image
docker push registry/name  # Push to registry
```

## Kubernetes Operations (for deployment)
```bash
kubectl get pods           # List pods
kubectl apply -f manifests/ # Apply K8s manifests
kubectl logs deployment/app # Check logs
```

## System Commands
```bash
pwd                        # Current directory
cd /path/to/dir           # Change directory
chmod +x script.sh        # Make executable
```