# Task Completion Protocol

## When Tasks Are Completed

### Mandatory Steps
1. **Validation**: Verify all changes work as expected
2. **Testing**: Run any applicable tests (when test framework exists)
3. **Documentation**: Update CLAUDE.md if workflow changes
4. **Git Operations**: Stage, commit, and push changes if requested

### Configuration Updates
- **MCP Changes**: Update mcp.json if new servers are added
- **Pipeline Changes**: Update deployment sections in CLAUDE.md
- **Credential Updates**: Securely update .credentials.json (never commit)

### Quality Checks
- **Syntax**: Ensure JSON/Markdown syntax is valid
- **References**: Verify all file paths and references are correct
- **Environment**: Test MCP server connections work

### Best Practices
- Use descriptive commit messages
- Keep sensitive data in .credentials.json (gitignored)
- Update version numbers in CLAUDE.md when making significant changes
- Test MCP tool functionality after configuration changes

### NO Automatic File Creation
- Only edit existing files unless absolutely necessary
- Prefer editing CLAUDE.md over creating new documentation
- Use TodoWrite tool for task tracking during complex workflows