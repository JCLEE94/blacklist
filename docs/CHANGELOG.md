# Changelog

All notable changes to the Blacklist Management System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2025-01-11

### Added
- 🎨 SVG-based system architecture presentation with interactive viewer
  - 5-slide comprehensive presentation covering system overview
  - Architecture-only diagram for technical documentation
  - HTML viewer with keyboard navigation and fullscreen support
  - Touch gesture support for mobile devices

### Changed
- 🚀 Major CI/CD pipeline improvements
  - Consolidated multiple workflow files into single `cicd.yml`
  - Switched to private registry (registry.jclee.me) as primary
  - Removed all GitHub Container Registry (GHCR) dependencies
  - Simplified to push-only strategy with ArgoCD Image Updater
  - Added parallel execution with matrix strategy for tests
  - Implemented concurrency control to prevent duplicate runs
  - Added skip conditions for documentation-only changes

### Fixed
- 🐛 Resolved IPv6 connectivity issues with private registry
- 🔧 Fixed deprecated GitHub Actions (v3 → v4)
- ✅ Added missing pytest imports and dummy tests
- 🚑️ Handled missing kubeconfig gracefully in CI/CD

### Security
- 🔒 Enhanced security by using self-hosted runners exclusively
- 🔒 Removed external registry dependencies

### Documentation
- 📝 Updated CLAUDE.md with new CI/CD pipeline details
- 📝 Updated README.md to reflect private registry usage
- 📝 Added comprehensive presentation materials in docs/presentation

## [3.0.0] - 2025-01-04

### Added
- ✨ ArgoCD GitOps integration for automated deployments
- ✨ Multi-server deployment support (local + remote)
- ✨ ArgoCD Image Updater for automatic image updates
- ✨ Cloudflare Tunnel integration support
- ✨ HAR-based collectors for REGTECH and SECUDIUM
- ✨ V2 API endpoints with enhanced analytics
- ✨ Docker container management API
- ✨ Collection logging system with daily statistics

### Changed
- 🔄 Replaced CronJob auto-updater with ArgoCD Image Updater
- 🔄 Migrated namespace from `blacklist-new` to `blacklist`
- 🔄 Modernized all deployment scripts for GitOps
- 🔄 Updated to use self-hosted GitHub Actions runners

### Fixed
- 🐛 Fixed date parsing to use source data dates
- 🐛 Resolved cache parameter naming issues
- 🐛 Fixed SECUDIUM concurrent session handling

### Removed
- 🗑️ Legacy auto-updater scripts (moved to legacy/)
- 🗑️ Old namespace configurations

## [2.0.0] - 2024-12-15

### Added
- ✨ Dependency injection architecture with central container
- ✨ Plugin-based IP source system
- ✨ Multi-layered entry points with fallback support
- ✨ Redis cache with memory fallback
- ✨ Comprehensive health check system
- ✨ Rate limiting and security headers

### Changed
- 🔄 Complete architecture refactor to use DI container
- 🔄 Improved error handling and logging
- 🔄 Enhanced performance with orjson
- 🔄 Streamlined API endpoints

### Security
- 🔒 Added comprehensive security headers
- 🔒 Implemented rate limiting per endpoint
- 🔒 Enhanced authentication for collectors

## [1.0.0] - 2024-11-01

### Added
- ✨ Initial release of Blacklist Management System
- ✨ REGTECH collector integration
- ✨ SECUDIUM collector integration
- ✨ FortiGate External Connector API
- ✨ Web dashboard interface
- ✨ SQLite database with auto-migration
- ✨ Basic Docker support
- ✨ Kubernetes deployment manifests

### Features
- 📊 Real-time IP blacklist management
- 🔄 Automatic data collection from multiple sources
- 📡 RESTful API for blacklist access
- 🌐 FortiGate firewall integration
- 📈 Statistics and analytics
- 🔍 IP search functionality

---

## Version History

- **3.1.0** (2025-01-11): CI/CD consolidation and presentation system
- **3.0.0** (2025-01-04): GitOps transformation with ArgoCD
- **2.0.0** (2024-12-15): Architecture refactor with DI
- **1.0.0** (2024-11-01): Initial release