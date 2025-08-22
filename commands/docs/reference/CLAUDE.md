# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code Agent System - a sophisticated orchestration framework for specialized AI agents. The system provides standardized agent definitions, execution patterns, and workflow automation for development tasks. Located in `~/.claude/agents/`, it can be invoked from any project directory.

## Agent Execution Commands

### Direct Agent Invocation
```bash
# List all available agents by category
python agent-runner.py --list

# Execute specific agent with task
python agent-runner.py orchestrator-master-system "Full project cleanup and optimization"
python agent-runner.py cleaner-code-quality "Remove duplicates and format code"
python agent-runner.py runner-test-automation "Run all tests with coverage"
python agent-runner.py analyzer-project-state "Analyze project health"
```

### Slash Command → Agent Mapping
When users type slash commands, immediately invoke via Task MCP tool:
- `/main` → `general-purpose` agent
- `/clean` → `cleaner-code-quality` agent  
- `/test` → `runner-test-automation` agent
- `/analyze` → `analyzer-project-state` agent
- `/deploy` → `specialist-deployment-infra` agent
- `/commit` → `specialist-github-cicd` agent

### Korean Keyword → Agent Routing
Automatically detect and route Korean keywords:
- "정리" → `cleaner-code-quality`
- "테스트" → `runner-test-automation`
- "분석" → `analyzer-project-state`
- "배포" → `specialist-deployment-infra`
- "커밋" → `specialist-github-cicd`

## High-Level Architecture

### Agent Registry Structure
```
agents/
├── agent-registry.json        # Legacy agent metadata and mappings
├── registry-native.json      # Native Claude Code agent definitions
├── agent-runner.py           # Python execution engine for agents
├── README.md                 # User-facing documentation
└── [agent-name].md          # Individual agent specifications
```

### Agent Categories & Hierarchy

**Management Layer (Priority 8-10)**
- `orchestrator-master-system` - System-wide orchestration
- `orchestrator-workflow-automation` - Workflow chain management
- `orchestrator-modular-system` - Modular task coordination
- `coordinator-adaptive-intelligence` - Learning and adaptation

**Execution Layer (Priority 5-7)**
- `executor-command-system` - Command execution
- `runner-test-automation` - Test framework automation
- `analyzer-project-state` - Project health analysis

**Specialist Layer (Priority 3-5)**
- `specialist-deployment-infra` - Docker/K8s/Helm/ArgoCD
- `specialist-github-cicd` - GitHub Actions and CI/CD
- `guardian-quality-project` - Quality gates and security

**Maintenance Layer (Priority 1-3)**
- `cleaner-code-quality` - Code cleanup and formatting

### Native Agent Integration

The system uses two registry files:
- **agent-registry.json**: Traditional agent definitions with role-function-domain naming
- **registry-native.json**: Claude Code native agents with MCP tool restrictions

Native agents have restricted tool access:
- `general-purpose`: All tools available
- `cleaner-code-quality`: Read, Edit, MultiEdit, Glob, ESLint, Bash
- `runner-test-automation`: Bash, Read, Write, code-runner
- `analyzer-project-state`: Read, Bash, Glob, Grep, memory tools
- `specialist-deployment-infra`: Read, Write, Edit, Bash, docker tools

## Critical Workflow Patterns

### Task MCP Invocation Pattern
```python
# Never execute agents via bash - always use Task MCP
Task(
    subagent_type="agent-type",
    description="Brief task description",
    prompt="Detailed instructions including Korean feedback requirement"
)
```

### Workflow Chaining
For complex operations, chain agents sequentially:
1. `analyzer-project-state` → Understand current state
2. `cleaner-code-quality` → Clean and format
3. `runner-test-automation` → Verify with tests
4. `specialist-github-cicd` → Create commit/PR
5. `specialist-deployment-infra` → Deploy to infrastructure

### Korean Feedback Pattern
All agents must provide user feedback in Korean:
```python
# Agent response template
"🔍 분석 중..." → During analysis
"✅ 완료됨:" → On completion
"❌ 오류 발생:" → On error
"💡 제안사항:" → For suggestions
```

## Infrastructure Configuration

All deployment agents use jclee.me domain services:
- **Docker Registry**: `registry.jclee.me`
- **Helm Repository**: `charts.jclee.me`
- **ArgoCD Dashboard**: `argo.jclee.me`
- **Kubernetes API**: `k8s.jclee.me`

Never use internal IPs or localhost for infrastructure operations.

## Agent Execution Rules

### Timeout Limits
Each agent has specific execution timeouts:
- `analyzer-project-state`: 300 seconds
- `cleaner-code-quality`: 600 seconds
- `runner-test-automation`: 900 seconds
- `general-purpose`: 1200 seconds
- `specialist-deployment-infra`: 1800 seconds

### Parallel Execution
- Maximum 3 agents can run concurrently
- Use TodoWrite to track parallel executions
- Coordinate via orchestrator agents for complex workflows

### Error Handling
1. Primary agent fails → Retry with extended timeout
2. Agent not found → Fallback to `orchestrator-master-system`
3. Tool access error → Use alternative available tools
4. Always report errors in Korean with actionable solutions

## Test Framework Detection

Agents automatically detect and use appropriate test frameworks:

**Node.js Projects**
- Check package.json for: jest, mocha, vitest, tape
- Default: `npm test`

**Python Projects**
- Check for: pytest, unittest, tox in requirements.txt
- Default: `pytest`

**Go Projects**
- Native: `go test ./...`

**Ruby Projects**
- Check for: rspec, minitest
- Default: `rspec`

## Memory & Learning Integration

Agents store patterns for optimization:
```python
# Store execution patterns
mcp__memory__create_entities(entities=[{
    "name": "AgentWorkflowPattern",
    "entityType": "execution_pattern",
    "observations": ["successful workflows", "common errors", "optimization opportunities"]
}])

# Retrieve learned patterns
mcp__memory__search_entities(query="workflow optimization")
```

## File Management Rules

### Enforcement by cleaner-code-quality
- Maximum 500 lines per file (ESLint enforced)
- No backup files (-original, -backup, -v2)
- Direct in-place editing only
- Consistent naming conventions

### Project Structure Standards
- Single responsibility per module
- Clear separation of concerns
- Index files for clean exports
- Proper error handling patterns

## Security Constraints

### Restricted Operations
- Never execute `rm -rf /` or destructive commands
- No access to: /etc, /sys, /root, ~/.ssh
- Maximum 1000 file operations per execution
- No sudo or privilege escalation

### Credential Management
- Always validate credentials before infrastructure operations
- Never log or expose secrets
- Use environment variables for sensitive data
- Implement proper secret rotation

## Agent Development Guidelines

### Creating New Agents
1. Follow role-function-domain naming: `role-function-domain.md`
2. Define clear tool restrictions in frontmatter
3. Specify compatible commands and workflows
4. Include Korean response templates
5. Register in both registry files

### Agent Specification Format
```yaml
---
name: agent-name
description: Clear description of agent purpose
tools: List, of, allowed, MCP, tools
---

Agent prompt and behavioral instructions...
```

## Debugging & Monitoring

### Agent Execution Logs
- Execution logs stored in session files
- Use TodoWrite for progress tracking
- Monitor with `agent-runner.py --status`

### Performance Metrics
- Track execution times per agent
- Monitor tool usage patterns
- Analyze failure rates and causes
- Optimize based on memory patterns