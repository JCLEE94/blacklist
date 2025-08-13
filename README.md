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
cp config/.env.example .env
nano .env  # Edit configuration

# Run
python app/main.py

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
├── README.md          # Documentation
├── CLAUDE.md          # Development guide
├── VERSION            # Version info
├── app/               # Application files
│   ├── main.py
│   ├── init_database.py
│   └── start.sh
├── src/               # Source code
├── config/            # Configuration
├── docker/            # Docker files
├── scripts/           # Scripts
└── tests/             # Tests
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