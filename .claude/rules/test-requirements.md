# Test Requirements

> Vision principle: **"100% test coverage — every line of business logic tested."** No exceptions.

## New Code Must Have Tests

When adding or modifying code in any server's `src/` directory:

1. **New modules** MUST have corresponding tests in `tests/unit/`
2. **New public functions/methods** MUST have at least one unit test covering the happy path
3. **Bug fixes** MUST include a regression test that would have caught the bug
4. **Modified functions** — if you change behavior, update or add tests to cover the change

## Test Conventions

- Test files: `tests/unit/test_<module>.py`
- Test functions: `test_<function_name>_<scenario>()`
- Mock all HTTP calls — never make real API requests in tests
- Use `pytest` fixtures, not setUp/tearDown
- Coverage target: 100% (enforced in pyproject.toml)

## Monorepo Test Commands

Each server has its own test suite. Run from the server directory:

```bash
# Single server
cd jira-mcp-server && pytest

# All servers
for dir in jira-mcp-server confluence-mcp-server bitbucket-mcp-server; do
  (cd $dir && pytest)
done
```

## What Doesn't Need Tests

- Private helper functions (tested indirectly through public API)
- Type definitions and Pydantic models (unless they have methods with logic)
- Configuration constants
- `__init__.py` re-exports
- Server entry points (`server.py` main block, tool registration) — covered by `# pragma: no cover`

## Before Committing

Run the tests for the server(s) you changed. Confirm all tests pass and coverage is 100%. Do not commit with failing tests.
