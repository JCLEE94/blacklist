---
description: Show available Claude Code commands and usage information
allowed-tools: [Task]
argument-hint: [category: commands|agents|tools|examples]
---

# Help - Claude Code Commands Reference

Automatically invoke general-purpose Native Agent for comprehensive help information.

## 🎯 Execution Strategy

Analyze help request and delegate to general-purpose agent:

```python
# Auto-detect help category from arguments
help_category = detect_help_intent("$ARGUMENTS")
selected_agent = "general-purpose"

# Invoke Native Agent via Task MCP
Task(
    subagent_type="general-purpose",
    description="Comprehensive Claude Code commands and usage help",
    prompt="""
    Provide comprehensive help information for claude-commands project.
    
    Help Category: $ARGUMENTS or "all" if not specified
    
    Project Context: /home/jclee/.claude/commands/
    - Claude Code slash command orchestration system
    - 6 Native Agents with specialized capabilities
    - 15+ available commands for various operations
    - Task MCP integration for all operations
    
    Help Tasks:
    1. List all available slash commands with descriptions
    2. Explain Native Agents and their specializations
    3. Show command usage examples and argument formats
    4. Provide best practices for command chaining
    5. Display troubleshooting and error resolution
    6. Include agent tool permissions and restrictions
    
    Tools Available: Read, Write, Edit, Glob, Bash, Memory
    
    Please provide help information in Korean with English examples.
    """
)
```

## 📚 Available Commands

### Core Workflow Commands
- **`/main`** - Intelligent workflow orchestrator with Native Agents integration
- **`/clean`** - Code cleanup with duplicate removal and formatting  
- **`/test`** - Automated test execution with coverage analysis
- **`/deploy`** - GitOps deployment management with ArgoCD and Kubernetes
- **`/analyze`** - Project health analysis and code quality assessment

### Utility Commands
- **`/organize`** - Project structure organization with MSA/DDD patterns
- **`/commit`** - Smart Git commit with conventional commits format
- **`/help`** - Show available commands and usage information
- **`/config`** - Configuration management and environment setup
- **`/debug`** - System debugging and troubleshooting assistance

## 🤖 Native Agents Overview

### Specialized Agents
- **cleaner-code-quality**: Code cleanup, formatting, duplicate removal
- **runner-test-automation**: Test execution, coverage analysis, failure diagnosis  
- **analyzer-project-state**: Git analysis, project health, code quality metrics
- **specialist-deployment-infra**: Docker, K8s, Helm, ArgoCD deployments
- **specialist-github-cicd**: GitHub Actions, PRs, CI/CD workflows
- **general-purpose**: Complex multi-step tasks, research, analysis

## 💡 Usage Examples

```bash
# Basic usage
/main clean duplicates
/test coverage
/deploy blacklist

# Advanced usage with arguments
/analyze project health
/organize msa
/commit "fix: resolve authentication issue"
```

---

**Delegates to general-purpose Native Agent for comprehensive help and documentation.**