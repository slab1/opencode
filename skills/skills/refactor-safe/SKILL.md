---
name: refactor-safe
description: Refactor code safely by following test-first refactoring patterns. Ensure tests exist before changing code, change one thing at a time, keep behavior identical. Use for any non-trivial refactor that risks breaking existing functionality.
license: MIT
compatibility: opencode>=1.16.0
---

# Refactor: Safe Refactoring

Refactor **without changing behavior**. The golden rule: if tests pass before and after, the refactor is correct.

## The Pre-Refactor Checklist

Before touching code, verify:
- [ ] Tests exist for the code being refactored
- [ ] All tests currently pass
- [ ] You have a clear refactor goal (not "just cleanup")
- [ ] You understand the current behavior (read the code, not just the docs)

If tests don't exist: **write them first**. This is the most important step.

## The Refactor Cycle

For each small change:

1. **Identify** the smallest meaningful change
2. **Verify** tests still pass
3. **Apply** the change
4. **Re-run** tests
5. **If failed**: revert and analyze; don't keep stacking fixes
6. **If passed**: commit (if using VCS) and proceed to next change

## Refactor Catalog (Fowler's)

### Composing Methods
- **Extract Method** — turn a code fragment into a method with a name
- **Inline Method** — replace a method call with its body (when too short)
- **Extract Variable** — give a complex expression a name
- **Inline Temp** — replace a temp with the expression it holds

### Moving Features
- **Move Method/Field** — move to the class that uses it most
- **Move Statements into/in out of Method** — colocate related code
- **Replace Method with Method Object** — when local vars tangle refactor
- **Extract Class** — split a class with two responsibilities
- **Inline Class** — merge a class that's no longer pulling weight

### Organizing Data
- **Encapsulate Field** — make field private, provide accessors
- **Replace Magic Number with Symbolic Constant** — name the constant
- **Replace Type Code with Class** — turn enum into class
- **Replace Type Code with Subclasses** — when type affects behavior
- **Replace Array with Object** — when fields have different meanings

### Simplifying Conditional Logic
- **Decompose Conditional** — extract the then/else branches
- **Consolidate Conditional Expression** — combine into one return
- **Replace Nested Conditional with Guard Clauses** — early returns
- **Replace Conditional with Polymorphism** — type-based behavior

### Simplifying Method Calls
- **Rename Method/Parameter** — clear names beat short names
- **Add/Remove Parameter** — only what's actually needed
- **Parameterize Method** — same body, different values
- **Preserve Whole Object** — pass the object, not its fields
- **Replace Parameter with Method** — call the method, don't pass its result
- **Introduce Parameter Object** — bundle related params
- **Remove Setting Method** — make field immutable when possible
- **Hide Method** — make a method private when no external user
- **Replace Constructor with Factory Method** — when constructor isn't enough

## When to Refactor

- **Rule of Three** — refactor on the third occurrence
- **Before adding a feature** — clean the area you'll modify
- **After getting a feature working** — apply lessons learned
- **During code review** — small improvements as you read

## When NOT to Refactor

- Right before a deadline (refactor introduces risk)
- Without tests to validate behavior
- When you don't understand what the code does
- When the refactor would be larger than the original code

## Code Smells (signs you should refactor)

- **Long Method** — > 20 lines
- **Large Class** — too many responsibilities
- **Long Parameter List** — > 3-4 params
- **Divergent Change** — one class changes for many reasons
- **Shotgun Surgery** — one change requires many small changes
- **Feature Envy** — method uses another class more than its own
- **Data Clumps** — same fields always appear together
- **Primitive Obsession** — using primitives when a class is needed
- **Switch Statements** — type code that should be polymorphism
- **Parallel Inheritance** — adding a subclass requires adding another
- **Speculative Generality** — "just in case" code
- **Temporary Field** — field only set in some circumstances
- **Message Chains** — long a.b().c().d() chains
- **Middle Man** — class delegates almost everything
- **Inappropriate Intimacy** — classes know too much about each other
- **Comments** — often a sign the code could be clearer

## Output Format

```json
{
  "id": "refactor-1717700000",
  "type": "refactor",
  "summary": "Extract Method: split parse_query into parse_filter and parse_sort",
  "before": {"file": "src/query.py", "line": 45, "loc": 87},
  "after": {"file": "src/query.py", "line": 45, "loc": 23},
  "tests_added": 4,
  "tests_still_passing": true,
  "behavior_changed": false,
  "refactor_pattern": "Extract Method"
}
```


## When to use

Load this skill when:
- The task description matches the patterns described in this skill
- You are uncertain about the recommended approach
- You need a checklist or pattern to follow

## When NOT to use

- The task clearly doesn't match (use a different skill)
- You have a more specific skill for the situation
- The user explicitly requests a different approach
