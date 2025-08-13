# Blacklist Management System

Enterprise threat intelligence platform for IP blacklist management and FortiGate integration.

## Features

- IP blacklist management with automatic expiration
- FortiGate External Connector integration
- REGTECH/SECUDIUM data collection
- Real-time monitoring and analytics
- Offline deployment support for air-gapped environments

## Quick Start

### Docker
```bash
docker run -d -p 32542:2541 registry.jclee.me/jclee94/blacklist:latest
```

### Kubernetes
```bash
kubectl apply -f https://raw.githubusercontent.com/JCLEE94/blacklist/main/chart/blacklist/values.yaml
```

### Offline Installation
```bash
tar -xzf blacklist-offline-package-v2.0.tar.gz
cd blacklist-offline-package-v2.0
sudo ./scripts/install.sh
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

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start development server
python main.py --debug
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