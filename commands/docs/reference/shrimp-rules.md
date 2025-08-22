# AI Agent Development Guidelines

## Project Overview
- **System Type**: Slash command backend for Claude Code automation
- **Core Technology**: MCP tools integration with markdown-based workflows
- **Language**: Hybrid Korean/English (Korean for user feedback, English for technical content)
- **Architecture**: Template-based workflow orchestration with intelligent agent coordination

## Mandatory Initialization Sequence
- **ALWAYS start with**: `mcp__serena__activate_project('.')`
- **ALWAYS follow with**: `mcp__serena__switch_modes(['editing', 'interactive'])`
- **ALWAYS check**: `mcp__serena__check_onboarding_performed()`
- **Never skip this sequence** - all other MCP tools depend on proper Serena activation

## File Structure and Coordination Rules

### Command Files (*.md)
- **Location**: Root directory (main.md, clean.md, test.md, deploy.md, init.md)
- **Structure**: Metadata header + AI Agent execution instructions + implementation details
- **Coordination Rule**: When modifying command files, check for related modules/*.md templates

### Module Templates (modules/*.md)
- **Location**: modules/ directory
- **Purpose**: Reusable workflow components referenced by command files
- **Coordination Rule**: When updating modules, verify all referencing command files for compatibility

### Documentation Coordination
- **Rule**: When modifying CLAUDE.md project intent, update related command files
- **Rule**: When adding new workflows, create both command.md AND corresponding modules/*.md
- **Rule**: All .md files MUST include metadata header with name, version, description, category

## MCP Tool Integration Standards

### Sequential Thinking Requirements
- **Mandatory for**: Complex decision making, workflow routing, failure analysis
- **Pattern**: Always use `mcp__sequential-thinking__sequentialthinking` before major decisions
- **Structure**: Set thoughtNumber, totalThoughts, nextThoughtNeeded appropriately

### Task MCP Orchestration
- **Rule**: Use Task MCP instead of direct bash commands
- **Pattern**: `Task(subagent_type="specialist-name", description="brief", prompt="detailed instructions")`
- **Prohibited**: Direct `mcp__mcp-server-commands__run_command` without Task wrapper

### Memory MCP Learning
- **Rule**: Store successful patterns in Memory MCP after workflow completion
- **Pattern**: `mcp__memory__create_entities` with entityType="workflow_pattern" or "automation_learning"
- **Purpose**: Continuous improvement of routing and execution accuracy

## Language and Feedback Standards

### Korean Feedback Rules
- **Use Korean for**: Status updates, progress messages, user-facing feedback
- **Examples**: "🔍 분석 중...", "✅ 완료되었습니다", "⚠️ 주의 필요"
- **Rule**: All console output to users should be in Korean

### English Technical Content
- **Use English for**: Code comments, technical documentation, MCP tool parameters
- **Rule**: All code blocks, function names, and technical specifications in English

## Workflow Execution Standards

### Think-First Approach
- **Rule**: Always analyze before acting using sequential-thinking MCP
- **Prohibited**: Immediate execution without analysis for complex tasks
- **Pattern**: Analysis → Planning → Execution → Learning

### CI/CD Integration
- **Rule**: Use cicd-auto-fix.md and cicd-failure-patterns.md for pipeline failures
- **Pattern**: Detect → Analyze → Auto-fix → Verify → Learn
- **Integration**: All CI/CD workflows must integrate with main.md routing

### Error Handling
- **Rule**: Never stop mid-execution without user notification
- **Rule**: Always provide Korean status updates during long-running operations
- **Rule**: Log failures to Memory MCP for pattern improvement

## File Modification Rules

### Template Structure Requirements
- **All .md files must include**:
  ```markdown
  ---
  metadata:
    name: "file-name"
    version: "x.x.x"
    description: "Purpose description"
    category: "category-type"
  ---
  ```

### Multi-file Coordination
- **When modifying main.md**: Check modules/routing.md, modules/automation.md
- **When adding CI/CD features**: Update both main.md and modules/cicd-*.md
- **When changing project intent**: Update CLAUDE.md and related command files

## Prohibited Actions

### File Creation Restrictions
- **Never create**: Unnecessary documentation files
- **Never create**: Backup files or temporary files
- **Never create**: Files without explicit user request or system requirement

### Execution Restrictions
- **Never use**: Direct bash commands without Task MCP wrapper
- **Never skip**: Sequential thinking for complex decisions
- **Never ignore**: Serena activation sequence
- **Never stop**: Mid-execution without Korean status message

### Pattern Violations
- **Never hardcode**: Environment-specific values
- **Never assume**: User intent without analysis
- **Never break**: Template structure requirements

## Decision-Making Standards

### Workflow Routing Priority
1. **Test failures** → /test workflow
2. **Lint errors** → /clean workflow  
3. **CI/CD failures** → /main with auto-fix integration
4. **Git changes** → /deploy workflow
5. **Unclear intent** → Sequential thinking analysis + user clarification

### Agent Selection Criteria
- **general-purpose**: Default for most tasks
- **specialist-deployment-infra**: Docker/Kubernetes operations
- **specialist-github-cicd**: GitHub Actions workflows
- **runner-test-automation**: Test execution and coverage
- **cleaner-code-quality**: Code cleanup and organization

### Success Verification
- **Rule**: Always verify workflow completion with appropriate MCP tools
- **Rule**: Update Memory MCP with success/failure patterns
- **Rule**: Provide Korean summary of results to user

## Integration Examples

### ✅ Correct Pattern
```python
# 1. Initialize
mcp__serena__activate_project('.')
mcp__serena__switch_modes(['editing', 'interactive'])

# 2. Think
mcp__sequential-thinking__sequentialthinking({
    "thought": "Analyzing user request for workflow routing",
    "thoughtNumber": 1,
    "totalThoughts": 3,
    "nextThoughtNeeded": True
})

# 3. Execute via Task
Task(
    subagent_type="general-purpose",
    description="Execute determined workflow",
    prompt="Detailed instructions based on analysis"
)

# 4. Learn
mcp__memory__create_entities([{
    "name": "successful_pattern",
    "entityType": "workflow_execution",
    "observations": ["Pattern details"]
}])
```

### ❌ Incorrect Pattern
```python
# Missing initialization
mcp__mcp-server-commands__run_command(command="git status")  # Direct bash
print("Task completed")  # English feedback to user
```

## Update Guidelines
- **Check all files** when updating rules
- **Maintain existing successful patterns** unless obsolete
- **Add new rules** based on recent codebase changes
- **Remove outdated rules** for deleted functionality