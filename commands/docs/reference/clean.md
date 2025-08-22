# /clean - Code Quality & Organization

**Execute MCP tools for code cleanup:**

```python
# 1. Activate Serena
mcp__serena__activate_project('.')
mcp__serena__switch_modes(['editing', 'interactive'])

# 2. Scan for issues
root_violations = mcp__serena__list_dir('.', recursive=False)
duplicates = mcp__serena__search_for_pattern('.*', paths_include_glob='*.md')

# 3. Clean up with specialized agent
Task(
    subagent_type="cleaner-code-quality",
    description="Clean code and organize files",
    prompt="Remove duplicates, organize root directory, fix naming conventions"
)

# 4. Store cleanup results
mcp__serena__write_memory('cleanup_status', f'Cleaned: {datetime.now()}')

# 5. Next step: /test
print("✅ Code cleaned → Run /test next")
``` 
     description="Complete root directory cleanup",
     prompt="""
CRITICAL: Ensure only README.md and CLAUDE.md exist in project root.
Move all other files to appropriate subdirectories:
- Scripts → commands/scripts/
- Configs → commands/config/  
- Documentation → docs/
- Tests → test/
- Temporary files → DELETE
""")
```

### Automatic File Relocation
```bash
# Detect misplaced files
find . -maxdepth 1 -type f ! -name "README.md" ! -name "CLAUDE.md" ! -name ".git*"

# Smart relocation based on file type
*.js → commands/scripts/
*.json → commands/config/
*.md → docs/
*test* → test/
*backup* → DELETE
*-old* → DELETE
```

## ESLint Integration & Automation

### Current ESLint Status (Auto-detected)
- **18 errors, 1 warning** requiring attention
- **11 auto-fixable issues** via `npm run lint:fix`
- **File size violations**: 500 lines maximum
- **Function size violations**: 100 lines maximum

### Advanced ESLint Workflow
```python
# Comprehensive ESLint automation
eslint_status = mcp__eslint__lint-files(["."])

if eslint_status.auto_fixable > 0:
    mcp__serena__execute_shell_command("npm run lint:fix")
    
# Manual fix guidance for complex issues
manual_fixes = [
    "quotes: Convert to single quotes",
    "unused-vars: Remove unused variables", 
    "curly: Add braces to if statements",
    "max-lines-per-function: Split large functions"
]
```

## Technical Debt Elimination

### Code Structure Optimization
```python
# Dead code detection and removal
Task(subagent_type="cleaner-code-quality",
     description="Remove dead code",
     prompt="""
1. Unused imports and variables
2. Unreachable code blocks
3. Duplicate functions
4. Obsolete comments
5. Empty files and directories
""")
```

### Module Organization
- **Import Optimization**: Group and sort imports by type
- **Dependency Analysis**: Remove unused packages from package.json
- **Code Duplication**: Identify and consolidate duplicate logic
- **Architecture Review**: Suggest structural improvements

## Performance-Driven Cleanup

### Automated Optimization
```python
# Performance impact analysis
performance_analysis = {
    "bundle_size": analyze_bundle_size(),
    "load_times": measure_load_performance(),
    "memory_usage": profile_memory_consumption(),
    "cpu_efficiency": analyze_computation_efficiency()
}

# Optimize based on findings
if performance_analysis.bundle_size > threshold:
    implement_code_splitting()
if performance_analysis.memory_usage > threshold:
    optimize_memory_patterns()
```

### Quality Metrics Tracking
- **Code Coverage**: Maintain >80% test coverage
- **Complexity Score**: Keep cyclomatic complexity low
- **Maintainability Index**: Track long-term code health
- **Security Compliance**: Regular security pattern audits

## Korean User Feedback
```korean
사용자 피드백:
- "루트 디렉토리 정리 시작..."
- "ESLint 오류 자동 수정 중..."
- "코드 품질 분석 완료"
- "기술 부채 제거 진행 중..."
- "성능 최적화 완료"
```

## Advanced Features

### Intelligent Cleanup Patterns
- **Context-Aware**: Different cleanup strategies for different project types
- **Learning System**: Improve cleanup efficiency based on project patterns
- **Batch Operations**: Optimize multiple file operations for speed
- **Rollback Capability**: Undo cleanup operations if needed

### Integration with Development Workflow
- **Pre-commit Hooks**: Automatic cleanup before commits
- **CI/CD Integration**: Quality gates in deployment pipeline
- **Real-time Monitoring**: Continuous code quality tracking
- **Team Synchronization**: Consistent quality standards across developers