# /test - Test Execution System

**Execute MCP tools for testing:**

```python
# 1. Activate Serena
mcp__serena__activate_project('.')
mcp__serena__switch_modes(['editing', 'interactive'])

# 2. Detect test framework
package_json = mcp__serena__read_file('package.json')
has_jest = 'jest' in package_json if package_json else False

# 3. Run tests with specialized agent
Task(
    subagent_type="runner-test-automation",
    description="Execute comprehensive testing",
    prompt="Run all tests, generate coverage report, ensure 80% coverage minimum"
)

# 4. Validate results
test_results = mcp__serena__execute_shell_command('npm test 2>&1 | tail -10')

# 5. Store test status
mcp__serena__write_memory('test_status', f'Tests run: {datetime.now()}')

# 6. Next step: /deploy
print("✅ Tests completed → Run /deploy next")
```
    "jest": "package.json contains jest",
    "pytest": "requirements.txt contains pytest", 
    "go_test": "go.mod file exists",
    "rspec": "Gemfile contains rspec"
}

# Execute TDD cycle based on detected framework
detected_framework = detect_test_framework()
Task(subagent_type="runner-test-automation",
     description=f"TDD workflow with {detected_framework}",
     prompt="Execute complete Red-Green-Refactor cycle")
```

### Comprehensive Test Execution with Silent Mode
```python
# Multi-phase testing approach with infinite scroll prevention
test_phases = [
    "unit_tests",      # Individual component testing
    "integration",     # Component interaction testing  
    "e2e",            # End-to-end user workflow testing
    "performance",     # Load and speed testing
    "security"         # Security vulnerability testing
]

# Silent execution to prevent Claude Code infinite scrolling
for phase in test_phases:
    # Execute tests with output suppression
    result = execute_silent_test(f"npm run test:{phase}", {
        "silent_mode": True,
        "output_file": f"test_results_{phase}.txt",
        "progress_only": True,
        "no_streaming": True
    })
    analyze_and_fix_failures(result)
```

## Coverage Enforcement (80% Minimum)

### Intelligent Coverage Analysis
```python
# Real-time coverage monitoring
coverage_analysis = {
    "current_coverage": get_current_coverage(),
    "coverage_target": 80,
    "uncovered_lines": identify_uncovered_code(),
    "critical_paths": find_critical_uncovered_paths()
}

# Automatic test generation for low coverage areas
if coverage_analysis.current_coverage < 80:
    generate_tests_for_uncovered_code(coverage_analysis.uncovered_lines)
```

### Quality Gates
- **Coverage Threshold**: Fail builds below 80% coverage
- **Critical Path Coverage**: Ensure 100% coverage for critical business logic
- **Regression Prevention**: Prevent coverage decrease in pull requests
- **Performance Testing**: Ensure no performance regression

## Intelligent Test Generation

### Auto-Test Creation
```python
# Generate tests for new functions/classes
def auto_generate_tests(code_changes):
    for changed_file in code_changes:
        functions = extract_functions(changed_file)
        for function in functions:
            if not has_existing_test(function):
                generate_unit_test(function)
                generate_integration_test(function)
```

### Test Pattern Recognition
- **Happy Path Tests**: Standard successful execution flows
- **Edge Case Tests**: Boundary conditions and edge cases  
- **Error Handling Tests**: Exception and error scenarios
- **Performance Tests**: Load and stress testing scenarios

## TDD Red-Green-Refactor Cycle

### Phase 1: Red (Write Failing Tests)
```python
# Write tests before implementation
test_specification = analyze_requirements()
failing_tests = generate_failing_tests(test_specification)

# Ensure tests fail for the right reasons
validate_test_failures(failing_tests)
```

### Phase 2: Green (Make Tests Pass)
```python
# Implement minimal code to pass tests
implementation = generate_minimal_implementation(failing_tests)

# Verify all tests now pass
test_result = run_all_tests()
assert test_result.all_passed == True
```

### Phase 3: Refactor (Improve Code Quality)
```python
# Refactor while maintaining test coverage
refactor_opportunities = identify_refactor_targets()
for opportunity in refactor_opportunities:
    refactor_code(opportunity)
    ensure_tests_still_pass()
```

## Advanced Testing Features

### Parallel Test Execution with Output Control
```python
# Optimize test execution time with infinite scroll prevention
parallel_test_config = {
    "workers": detect_optimal_worker_count(),
    "test_sharding": distribute_tests_across_workers(),
    "resource_isolation": ensure_test_isolation(),
    "output_management": {
        "silent_mode": True,
        "buffer_limit": 1000,
        "streaming_disabled": True,
        "log_to_files": True
    }
}

# Background execution to prevent terminal flooding
execute_parallel_tests_silently(parallel_test_config)
```

### Performance Benchmarking
```python
# Continuous performance monitoring
performance_benchmarks = {
    "response_time": measure_api_response_times(),
    "memory_usage": profile_memory_consumption(),
    "cpu_utilization": monitor_cpu_efficiency(),
    "database_queries": analyze_query_performance()
}
```

## Claude Code Infinite Scroll Prevention

### Silent Test Execution Strategy
```python
# Comprehensive output control to prevent infinite scrolling
silent_test_execution = {
    "output_suppression": {
        "stdout_redirect": "/dev/null",
        "stderr_to_file": "test_errors.log",
        "progress_minimal": True,
        "streaming_disabled": True
    },
    "background_execution": {
        "run_in_background": True,
        "notify_on_complete": True,
        "status_file": "test_status.json"
    },
    "buffer_management": {
        "max_output_lines": 50,
        "scroll_prevention": True,
        "terminal_buffer_limit": 1000
    }
}

# Execute tests without terminal flooding
def execute_tests_silently():
    Task(subagent_type="runner-test-automation",
         description="Silent TDD workflow execution",
         prompt="""
         Execute all tests with complete output suppression:
         1. Redirect all stdout to files
         2. Show only final results summary
         3. Prevent any streaming output
         4. Use background execution
         5. Generate completion notification only
         """)
```

### Emergency Scroll Prevention Protocol
```python
# Immediate response to infinite scroll detection
if detect_infinite_scroll():
    # Force silent mode activation
    enable_emergency_silent_mode()
    # Redirect current output
    redirect_output_to_file()
    # Continue execution in background
    move_to_background_execution()
```

## Korean User Feedback
```korean
무한 스크롤 방지 테스트 실행:
- "조용한 모드로 테스트 시작..."
- "출력 억제 활성화 완료"
- "백그라운드에서 테스트 진행 중..."
- "파일로 결과 저장 중..."
- "테스트 완료 - 요약만 표시"
- "무한 스크롤 없이 안전하게 완료"
```

## Failure Analysis & Auto-Fix

### Smart Failure Detection with Silent Analysis
```python
# Analyze test failures and suggest fixes without output flooding
failure_analysis = {
    "syntax_errors": detect_syntax_issues(),
    "logic_errors": identify_logic_problems(), 
    "dependency_issues": check_dependency_conflicts(),
    "environment_problems": validate_test_environment(),
    "output_control": {
        "silent_analysis": True,
        "log_to_file": "failure_analysis.log",
        "summary_only": True
    }
}

# Auto-fix common issues silently
for error_type, fixes in auto_fixable_errors.items():
    apply_automated_fixes_silently(fixes, output_mode="file")
```

### Terminal-Safe Test Command Integration
```bash
# Add to your shell profile for safe testing
alias ts-safe='claude test --silent --output-file=test_results.txt --no-streaming'
alias ts-background='claude test --background --notify-on-complete'
alias ts-minimal='claude test --progress-only --max-lines=20'

# Emergency scroll stop
alias stop-scroll='killall claude && claude --reset-terminal'
```

### Continuous Improvement
- **Test Quality Metrics**: Monitor test effectiveness and reliability
- **Flaky Test Detection**: Identify and fix unstable tests
- **Test Performance**: Optimize slow-running tests
- **Coverage Optimization**: Ensure meaningful, not just numerical coverage