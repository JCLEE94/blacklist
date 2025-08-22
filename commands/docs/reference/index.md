# Claude Commands - Enhanced AI Agent System

## 🚀 Core Architecture

**Intelligent automation platform** with **conversation-driven routing** and **self-improving procedures**.

### 🔄 Organic Command Chain

```mermaid
graph LR
    A[/init] --> B[/auth]
    B --> C[/main]
    C --> D[/clean]
    C --> E[/deploy]
    D --> F[/test]
    F --> E
    E --> G[Complete]
```

### 📋 Command Specifications

| Command | Category | Time | Dependencies | Success Rate |
|---------|----------|------|-------------|--------------|
| `/init` | core | 15-30s | none | 98% |
| `/auth` | infra | 20-40s | init | 95% |
| `/main` | core | 30-60s | none | 92% |
| `/clean` | dev | 45-90s | init | 89% |
| `/test` | dev | 60-120s | clean | 87% |
| `/deploy` | infra | 90-180s | auth,test | 94% |

### Support Commands
- **`/help`** - Command usage guide
- **`/index`** - This organic command chain
- **`/validate`** - System health validation
- **`/recover`** - Emergency error recovery

## MCP Tools Integration

Each command uses **MCP tools** for execution:

```bash
# All commands start with Serena activation
mcp__serena__activate_project('.')
mcp__serena__switch_modes(['editing', 'interactive'])

# Then use specialized agents via Task tool
Task(subagent_type="cleaner-code-quality", ...)
Task(subagent_type="specialist-deployment-infra", ...)
```

### Essential MCP Tools
- **Serena**: Project management, file operations
- **Task**: Native agent orchestration  
- **Shrimp Task Manager**: Task planning
- **Sequential Thinking**: Problem solving
- **Brave/Exa Search**: External research