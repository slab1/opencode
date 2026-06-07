---
name: security-threat-model
description: STRIDE-based threat modeling for the security, architect, and plan agents. Use when designing a new system, reviewing an architecture, or evaluating a third-party integration. Produces a structured threat model with mitigations before code is written.
license: MIT
compatibility: opencode>=1.16.0
---

# Security Threat Model

Apply **STRIDE** to every system design before it's implemented. The goal is to find threats early, when they're cheap to fix.

## The STRIDE categories

| Category | Question | Examples |
|----------|----------|----------|
| **S**poofing | Can an attacker pretend to be someone/something else? | Forged tokens, fake APIs, identity theft |
| **T**ampering | Can data be modified in transit or at rest? | MITM, log injection, config drift |
| **R**epudiation | Can a user deny an action they took? | Missing audit logs, unsigned commits |
| **I**nformation disclosure | Can data leak to unauthorized parties? | Verbose errors, exposed secrets, side channels |
| **D**enial of service | Can the system be made unavailable? | Resource exhaustion, algorithmic complexity attacks |
| **E**levation of privilege | Can a user gain capabilities they shouldn't have? | Auth bypass, role confusion, RCE |

## The 5-step process

### Step 1: Define the system

Document:
- **Components** (servers, services, databases, queues, external APIs)
- **Data flows** (who sends what to whom, in what format, over what protocol)
- **Trust boundaries** (where auth/authz is enforced, where data crosses)
- **Assets** (what's valuable — credentials, PII, business logic, availability)
- **Actors** (users, admins, services, attackers)

### Step 2: Build a data flow diagram (DFD)

Sketch the components and flows. Mark trust boundaries explicitly. Use:
- External entity (rectangle)
- Process (circle)
- Data store (parallel lines)
- Trust boundary (dashed line)

### Step 3: Enumerate threats per STRIDE category

For each component and flow, ask each STRIDE question. Document:
- Threat: <what could go wrong>
- Target: <which component/flow is affected>
- Preconditions: <what must be true for the threat to succeed>
- Impact: <what's the worst case>

### Step 4: Rate severity (DREAD)

For each threat, score 1-10 on:
- **D**amage potential
- **R**eproducibility
- **E**xploitability
- **A**ffected users
- **D**iscoverability

**Risk = (D + R + E + A + D) / 5**. Threats scoring ≥ 6 require a documented mitigation.

### Step 5: Define mitigations

For each high-risk threat:
- **Prevent**: design choice that eliminates the threat
- **Detect**: monitoring/alerting that catches the threat
- **Respond**: incident response procedure

If no mitigation is possible, document acceptance and the reason.

## Output template

```markdown
# Threat Model: <System Name>

## System overview
<1-paragraph summary>

## Data flow diagram
<ASCII or mermaid diagram with trust boundaries marked>

## Assets
- <Asset 1>: <why it's valuable>
- <Asset 2>: <why it's valuable>

## Trust boundaries
- <Boundary 1>: <what's on each side>
- <Boundary 2>: <what's on each side>

## Threat enumeration

### Spoofing
| Threat | Target | Preconditions | Impact | DREAD | Mitigation |
|--------|--------|---------------|--------|-------|------------|
| ...    | ...    | ...           | ...    | ...   | ...        |

### Tampering
...

## Prioritized mitigations
1. <Mitigation 1> (blocks threats X, Y)
2. <Mitigation 2> (blocks threat Z)

## Accepted risks
- <Risk>: <reason for acceptance>
```

## When to use

- Before implementing a new system or major feature
- Before integrating a third-party service or library
- After a security incident (model what went wrong)
- During architecture review (architect agent)
- For new agent capabilities (meta-agent)

## When NOT to use

- Pure documentation changes
- Read-only analysis with no system context
- Already-secured commodity systems (using bcrypt? probably fine)

## Integration with security agent

The `security` agent should:
1. Run a threat model as the first step of any review
2. Use the `security-audit` skill for code-level findings
3. Use this skill for architecture-level findings
4. Produce a combined report

## Integration with architect agent

The `architect` agent should:
1. Include a threat model section in any system design
2. Run STRIDE before recommending the final architecture
3. Document accepted risks in the ADR
