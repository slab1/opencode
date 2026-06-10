---
name: security-audit
description: Perform structured security audits following OWASP methodology. Map attack surface, trace data flow, check trust boundaries, audit secrets, evaluate dependencies. Rate findings by CVSS severity with reproducible steps and remediation.
license: MIT
compatibility: opencode>=1.16.0
---

# Security Audit

A **structured methodology** for security audits based on OWASP Top 10, with reproducible findings and CVSS-rated severity.

## The Method

### 1. Map Attack Surface
- Identify entry points: APIs, UIs, file uploads, webhooks, network ports
- Inventory authentication and authorization mechanisms
- Document trust boundaries (user input, internal vs external, public vs private)

### 2. Trace Data Flow
- For each entry point, follow data through the system
- Identify validation points: is input validated at every boundary?
- Note where data crosses trust zones

### 3. Check Trust Boundaries
- Verify validation at every boundary crossing
- Check escape handling: SQL, HTML, shell, JSON, path
- Check for SSRF, XXE, deserialization vulnerabilities

### 4. Review Auth Flows
- Examine authentication: passwords, tokens, sessions, MFA
- Examine authorization: role-based, scope-based, ownership checks
- Check for IDOR, privilege escalation, broken access control

### 5. Audit Secrets
- Search for hardcoded credentials (API keys, passwords, tokens)
- Check secret management: env vars, vault, KMS
- Check log files for accidental secret exposure

### 6. Evaluate Dependencies
- Run `npm audit`, `pip audit`, `cargo audit`, `go mod tidy`
- Check for known CVEs in third-party packages
- Check for abandoned or malicious packages

## Severity (CVSS-style)

| Severity  | Description                                              |
|-----------|----------------------------------------------------------|
| Critical  | Immediately exploitable, high impact (data loss, RCE)    |
| High      | Exploitable with some effort, significant impact         |
| Medium    | Requires specific conditions, moderate impact            |
| Low       | Minor issue, limited impact                              |
| Info      | Best practice recommendation, no direct vulnerability     |

## Finding Format

```json
{
  "id": "sec-1717700000",
  "type": "vulnerability",
  "title": "SQL injection in user search",
  "severity": "critical",
  "cwe": "CWE-89",
  "owasp": "A03:2021 Injection",
  "cvss": 9.8,
  "location": {"file": "src/users.py", "line": 47},
  "description": "User input is concatenated into SQL query without parameterization",
  "reproduction": "GET /api/users?name=' OR '1'='1 returns all users",
  "impact": "Full database read/write/delete access; possible RCE via SQL",
  "remediation": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE name = %s', (name,))",
  "references": ["https://owasp.org/www-community/attacks/SQL_Injection"]
}
```

## OWASP Top 10 (2021) — Quick Reference

1. **A01 Broken Access Control** — IDOR, missing auth, privilege escalation
2. **A02 Cryptographic Failures** — Weak ciphers, missing encryption, exposed data
3. **A03 Injection** — SQL, NoSQL, command, LDAP, XPath
4. **A04 Insecure Design** — Missing threat modeling, business logic flaws
5. **A05 Security Misconfiguration** — Default configs, debug modes, missing headers
6. **A06 Vulnerable Components** — Outdated deps, abandoned libraries
7. **A07 Auth Failures** — Weak passwords, missing MFA, session issues
8. **A08 Software/Data Integrity** — Unsigned updates, insecure deserialization
9. **A09 Logging Failures** — Missing audit logs, unmonitored events
10. **A10 SSRF** — Server-side request forgery via user-controlled URLs

## Common Quick Wins

- Add security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- Enable HTTPS only, redirect HTTP
- Implement rate limiting on all public endpoints
- Use parameterized queries everywhere
- Hash passwords with bcrypt/argon2 (not MD5/SHA1)
- Sanitize HTML output to prevent XSS
- Validate file uploads by content (not just extension)
- Rotate secrets regularly, use secret management
- Enable structured audit logging
- Add MFA for privileged accounts

## What NOT to Do

- Never output found secrets in reports (just the location)
- Never disable security features to "make it work"
- Never store passwords in plain text
- Never trust client-side validation alone
- Never expose stack traces to users


## When to use

Load this skill when:
- The task description matches the patterns described in this skill
- You are uncertain about the recommended approach
- You need a checklist or pattern to follow

## When NOT to use

- The task clearly doesn't match (use a different skill)
- You have a more specific skill for the situation
- The user explicitly requests a different approach
