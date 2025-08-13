# Blacklist Management System

Enterprise threat intelligence platform for IP blacklist management and FortiGate integration.

## Features

- IP blacklist management with automatic expiration
- FortiGate External Connector integration
- REGTECH/SECUDIUM data collection
- Real-time monitoring and analytics
- Offline deployment support for air-gapped environments

## Quick Start

```bash
# Setup
cp .env.example .env
nano .env  # Edit configuration

# Run
python main.py

# Or with Docker
docker-compose -f docker/docker-compose.yml up -d
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/blacklist/active` | Active IP list |
| `GET /api/fortigate` | FortiGate format |
| `POST /api/collection/trigger` | Manual collection |

## Configuration

Create `.env` file:
```env
DATABASE_URL=sqlite:////app/instance/blacklist.db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password
```

## Project Structure

```
blacklist/
├── main.py             # Entry point
├── init_database.py    # DB initialization
├── start.sh           # Service management
├── src/               # Application code
├── templates/         # HTML templates
├── static/           # CSS/JS files
├── config/           # Configuration files
├── docker/           # Docker files
├── scripts/          # Utility scripts
└── tests/            # Test suite
```

## Documentation

- [Installation Guide](docs/installation.md)
- [API Reference](docs/api-reference.md)
- [Offline Deployment](docs/offline-deployment.md)
- [Development Guide](CLAUDE.md)

## Requirements

- Python 3.8+
- Docker 20.10+ (optional)
- Redis 7+ (optional)
- Linux/Unix environment

## License

MIT License

## Support

For issues and questions, please use [GitHub Issues](https://github.com/JCLEE94/blacklist/issues).