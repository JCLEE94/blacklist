# Project Structure

## Directory Organization

```
blacklist/
├── main.py                  # Primary entry point with fallback chain
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variable template
├── CLAUDE.md               # AI assistant instructions
├── README.md               # Project documentation
│
├── src/                    # Source code
│   ├── core/              # Core business logic
│   │   ├── app_compact.py # Main Flask application
│   │   ├── container.py   # Dependency injection container
│   │   ├── blacklist_unified.py  # Blacklist management
│   │   ├── database.py    # Database operations
│   │   ├── models.py      # Data models and types
│   │   ├── validators.py  # Input validation
│   │   ├── constants.py   # System constants
│   │   ├── exceptions.py  # Custom exceptions
│   │   ├── routes_unified.py     # API routes
│   │   ├── collection_manager.py # Data collection control
│   │   ├── regtech_collector.py  # REGTECH integration
│   │   ├── secudium_collector.py # SECUDIUM integration
│   │   └── ip_sources/    # Plugin-based IP sources
│   │       ├── base_source.py
│   │       ├── source_manager.py
│   │       └── sources/   # Individual source implementations
│   │
│   ├── config/            # Configuration management
│   │   ├── base.py        # Base configuration
│   │   ├── development.py # Dev settings
│   │   ├── production.py  # Prod settings
│   │   ├── factory.py     # Config factory
│   │   └── settings.py    # Settings management
│   │
│   ├── utils/             # Utility modules
│   │   ├── cache.py       # Cache management
│   │   ├── auth.py        # Authentication/authorization
│   │   ├── monitoring.py  # System monitoring
│   │   ├── performance.py # Performance optimization
│   │   └── advanced_cache.py # Enhanced caching
│   │
│   ├── services/          # Service layer
│   │   └── response_builder.py
│   │
│   └── web/              # Web interface
│       └── routes.py     # Web UI routes
│
├── tests/                # Test suite
│   ├── pytest.ini       # Pytest configuration
│   └── test_*.py        # Test modules
│
├── scripts/             # Utility scripts
│   ├── github-setup.sh  # GitHub repository setup
│   ├── integration_test_comprehensive.py
│   └── debug_regtech_advanced.py
│
├── deployment/          # Deployment configuration
│   ├── deploy.sh       # Deployment script
│   ├── Dockerfile      # Container definition
│   └── nginx.conf      # Nginx configuration
│
├── docker/             # Docker configurations
│   └── docker-compose.yml
│
├── docs/               # Documentation
├── static/             # Static assets
├── templates/          # HTML templates
├── logs/               # Application logs (gitignored)
├── instance/           # Instance-specific data (gitignored)
└── data/               # Data storage (partially gitignored)
```

## Key Files
- `main.py`: Entry point with intelligent fallback to handle various deployment scenarios
- `src/core/container.py`: Central dependency injection managing all services
- `src/core/app_compact.py`: Optimized Flask application with full features
- `src/core/blacklist_unified.py`: Core blacklist management logic
- `deployment/deploy.sh`: Production deployment to registry.jclee.me