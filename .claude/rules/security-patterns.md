# Security Patterns (OWASP ASVS Level 2)

> Vision principle: **"Security is structural, not optional."** Auth tokens come from environment variables only. No hardcoded credentials. No eval. No injection vectors.

These patterns are enforced on ALL code in this repository. Violations must be fixed before committing.

## Forbidden — Never Generate These

- `eval()`, `exec()`, `compile()` with any user-controlled input
- Hardcoded secrets, API keys, passwords, or tokens
- `subprocess` calls with `shell=True` and user input
- `verify=False` or `rejectUnauthorized: false` in HTTP/TLS clients
- `pickle.loads()` on untrusted data
- Logging of passwords, session tokens, API keys, or PII

## Required Patterns

### HTTP Client
- Auth headers built from config, never hardcoded
- TLS verification enabled by default (`verify_ssl=True`)
- Structured error handling per HTTP status code
- Timeouts on all requests

### Input Validation
- Validate all tool parameters before passing to API
- Allowlists over denylists
- No user input interpolated into URLs without validation

### Configuration
- All secrets via environment variables (pydantic-settings)
- No default values for tokens or credentials
- Auth type auto-detection from available env vars

### Error Handling
- Never expose raw API error responses with auth details
- Structured error messages with context
- No stack traces in tool responses

## When Adding New Tools

1. Validate all parameters at the tool function boundary
2. Use the shared client for all HTTP operations
3. Handle all error responses (4xx, 5xx, timeouts)
4. Never log or return auth headers/tokens
5. Test error paths, not just happy paths
