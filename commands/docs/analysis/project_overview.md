# Project Overview

## Purpose
This is a Claude Code configuration project containing:
- Claude AI agent instructions (CLAUDE.md)
- MCP (Model Context Protocol) server configurations
- Development workflow and pipeline guidelines

## Tech Stack
- **Configuration**: JSON, Markdown
- **MCP Servers**: Various tools for AI agent capabilities
- **Deployment**: Docker containers, Kubernetes, ArgoCD
- **CI/CD**: GitHub Actions with self-hosted runners

## Project Structure
```
.claude/
├── CLAUDE.md              # Main AI agent instructions
├── mcp.json              # MCP server configurations
├── .credentials.json     # Sensitive credentials
├── .serena/              # Serena tool workspace
├── projects/             # Project-specific configurations
├── statsig/              # Statistics and analytics
├── local/                # Local development files
└── todos/                # Task management
```

## Core Components
1. **CLAUDE.md**: Comprehensive AI agent instructions including deployment pipelines
2. **MCP Servers**: 15+ integrated tools (GitHub, Docker, Memory, Search, etc.)
3. **Development Pipelines**: Two scenarios for offline/online deployment targets