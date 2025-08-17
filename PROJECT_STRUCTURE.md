# Project Structure

## Root Directory (Clean)
```
blacklist/
├── main.py                 # Application entry point
├── docker-compose.yml      # Docker orchestration
├── Dockerfile             # Container definition
├── Makefile              # Build automation
├── requirements.txt      # Python dependencies
├── pyproject.toml       # Project configuration
├── pytest.ini           # Test configuration
├── README.md           # Project documentation
├── CLAUDE.md          # AI assistant guidelines
├── VERSION            # Version tracking
└── .env.example      # Environment template
```

## Directory Organization
```
├── src/               # Source code
│   ├── core/         # Core application modules
│   └── utils/        # Utility functions
├── tests/            # Test suites
├── k8s/              # Kubernetes & GitOps
│   ├── manifests/    # K8s resource definitions
│   ├── argocd-app.yaml # ArgoCD application
│   └── apply.sh      # Deployment script
├── docs/             # Documentation
│   └── reports/      # Analysis reports
├── scripts/          # Automation scripts
├── config/           # Configuration files
├── monitoring/       # Monitoring configs
├── static/           # Static assets
├── templates/        # HTML templates
├── data/             # Application data
├── logs/             # Application logs
└── instance/         # Instance-specific data
```

## File Count
- Root files: 14 (optimized from 20+)
- Removed: Duplicate configs, temporary files, archives
- Organized: Reports → docs/, Scripts → scripts/

## Key Changes
1. ✅ Removed Helm charts (using Kustomize)
2. ✅ Consolidated environment files
3. ✅ Cleaned temporary/cache files
4. ✅ Organized reports into docs/reports
5. ✅ Standardized K8s manifests