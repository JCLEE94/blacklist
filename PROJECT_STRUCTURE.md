# Project Structure - Standard Organization

## Root Directory
```
blacklist/
├── main.py                      # Application entry point
├── README.md                    # Korean documentation
├── README_EN.md                 # English documentation
├── CLAUDE.md                    # Claude Code configuration
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development dependencies
└── index.html                   # GitHub Pages portfolio
```

## Core Application (`src/`)
```
src/
├── core/                        # Main application logic
│   ├── app_compact.py          # Flask app factory
│   ├── container.py            # Dependency injection
│   ├── routes/                 # Modular route system
│   ├── services/               # Business logic services
│   └── common/                 # Shared utilities
├── config/                      # Configuration management
├── utils/                       # Application utilities
└── web/                        # Web interface components
```

## Infrastructure (`k8s/`, `charts/`, `deployment/`)
```
k8s/                            # Kubernetes manifests
├── base/                       # Base configurations
├── overlays/                   # Environment-specific patches
└── argocd/                     # GitOps configurations

charts/blacklist/               # Helm chart
├── Chart.yaml                  
├── values.yaml                 
└── templates/                  

deployment/                     # Docker configurations
├── Dockerfile                  
└── docker-compose.yml          
```

## Testing (`tests/`)
```
tests/
├── integration/                # Integration tests
├── performance/                # Performance tests
└── conftest.py                # Test configuration
```

## Scripts (`scripts/`)
```
scripts/
├── k8s-management.sh          # Kubernetes operations
├── deploy.sh                  # Basic deployment
└── lib/                       # Shared script libraries
```

## Documentation (`docs/`)
```
docs/
├── DEPLOYMENT_CHECKLIST.md   # Production deployment guide
├── ARGOCD_SETUP.md           # GitOps setup instructions
└── archive/                   # Historical documentation
```

## Data & Logs (`data/`, `logs/`)
```
data/                          # Application data
├── regtech/                   # REGTECH collection data
└── sources/                   # Data sources configuration

logs/                          # Application logs
```

## Clean Structure Principles

1. **Essential Files Only**: Keep only production-necessary files
2. **Clear Separation**: Separate code, config, docs, and data
3. **Archive Unused**: Move old files to archive/ directories
4. **Standard Names**: Use conventional naming patterns
5. **Minimal Depth**: Avoid deep nested structures

## File Count Targets
- Root level: < 20 files
- Each subdirectory: < 30 files
- Documentation: Essential guides only
- Archive old/unused files regularly