# User Request Tracking System Design

## Overview
MCP Memory API를 활용한 실시간 사용자 요청 추적 시스템

## Entity Structure

### UserRequest Entity
```json
{
  "entity_type": "UserRequest",
  "attributes": {
    "request_id": "string (auto-generated UUID)",
    "timestamp": "datetime (ISO 8601)",
    "category": "enum[file,code,analysis,test,deploy,docs,other]",
    "description": "string (user request description)",
    "priority": "enum[low,medium,high,critical]",
    "status": "enum[pending,in_progress,completed,failed,cancelled]",
    "assigned_to": "string (agent or module name)",
    "evidence": "array[string] (proof of completion)",
    "completion_time": "datetime (when completed)",
    "verification_result": "object (detailed verification)"
  }
}
```

## Request Detection Patterns

### File Operations
- `파일.*만들` → CREATE_FILE
- `파일.*수정` → MODIFY_FILE
- `파일.*삭제` → DELETE_FILE
- `파일.*정리` → ORGANIZE_FILES

### Code Modifications
- `코드.*수정` → MODIFY_CODE
- `리팩토링` → REFACTOR_CODE
- `함수.*추가` → ADD_FUNCTION
- `버그.*수정` → FIX_BUG

### Analysis Tasks
- `분석.*해` → ANALYZE
- `조사.*해` → INVESTIGATE
- `확인.*해` → VERIFY
- `찾아.*봐` → SEARCH

## State Transitions
```
pending → in_progress → completed
                    ↘ → failed
                    ↘ → cancelled
```

## Integration Points

### 1. Conversation Monitor Integration
```python
# In conversation-monitor.md
def on_user_message(message):
    request = detect_request(message)
    if request:
        entity = create_request_entity(request)
        mcp__memory__create_entities([entity])
```

### 2. Auto Command Integration
```bash
# In auto.md Phase tracking
update_request_status() {
    local request_id="$1"
    local status="$2"
    mcp__memory__add_observations(
        entityName="Request-$request_id",
        contents=["Status updated to $status at $(date)"]
    )
}
```

### 3. Verification System
```python
def verify_request_completion(request_id):
    # Check file changes
    # Check command outputs
    # Check test results
    evidence = collect_evidence()
    
    mcp__memory__add_observations(
        entityName=f"Request-{request_id}",
        contents=[f"Verification: {evidence}"]
    )
```

## Metrics and Reporting

### Key Metrics
- Total requests by category
- Completion rate by category
- Average completion time
- Success rate
- User satisfaction score

### Report Generation
```python
def generate_report():
    graph = mcp__memory__read_graph()
    requests = filter_user_requests(graph)
    
    stats = {
        "total": len(requests),
        "completed": count_by_status(requests, "completed"),
        "success_rate": calculate_success_rate(requests),
        "by_category": group_by_category(requests)
    }
    
    return format_report(stats)
```

## Example Usage

### Creating a Request
```python
mcp__memory__create_entities([{
    "name": "Request-001",
    "entityType": "UserRequest",
    "observations": [
        "timestamp: 2024-01-20T10:30:00Z",
        "category: file",
        "description: 중복 파일 정리 및 통합",
        "priority: high",
        "status: pending"
    ]
}])
```

### Updating Status
```python
mcp__memory__add_observations({
    "entityName": "Request-001",
    "contents": [
        "status: in_progress",
        "assigned_to: clean-command",
        "started_at: 2024-01-20T10:31:00Z"
    ]
})
```

### Adding Evidence
```python
mcp__memory__add_observations({
    "entityName": "Request-001",
    "contents": [
        "status: completed",
        "evidence: Removed 156 duplicate files",
        "evidence: Consolidated 12 modules",
        "completion_time: 2024-01-20T10:45:00Z",
        "verification_result: {files_removed: 156, modules_consolidated: 12}"
    ]
})
```