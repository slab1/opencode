---
name: tdd-workflow
description: Test-driven development pattern: red-green-refactor cycle for the test and build agents. Use when implementing new features, fixing bugs, or refactoring — every change starts with a failing test, then minimal code, then cleanup. Reduces regressions and clarifies intent.
license: MIT
compatibility: opencode>=1.16.0
---

# TDD Workflow

Apply the **red-green-refactor** cycle to every code change. The `test` and `build` agents share responsibility for this pattern.

## The Cycle

### 1. RED — Write a failing test first
- Identify the smallest unit of behavior to add or change
- Write a test that exercises that behavior
- Run the test — confirm it FAILS for the right reason
- If it passes, your test is wrong; if it errors, your test is fine

### 2. GREEN — Write the minimum code to pass
- Write the simplest possible implementation
- Resist the urge to over-engineer
- Run the test — confirm it PASSES
- If it fails, fix the implementation, not the test

### 3. REFACTOR — Clean up while green
- Improve structure, naming, duplication
- Run the test after every change
- Commit when green

## When to use

Use this skill when:
- Implementing a new feature
- Fixing a bug (write a test that reproduces it first)
- Refactoring existing code
- Adding a public API
- The user says "TDD" or "test first"

## When NOT to use

- Throwaway prototypes / spikes
- Documentation-only changes
- Configuration changes (no testable behavior)
- Emergency hotfixes (add a regression test after, not before)

## Test shape (preferred)

```python
def test_<unit>_<scenario>_<expected>():
    # Arrange
    input = ...
    # Act
    result = unit(input)
    # Assert
    assert result == expected
```

## Coverage discipline

- Cover behavior, not implementation
- One assertion per concept (multiple assertions OK if testing the same concept)
- Test edge cases: empty, null, boundary, error path
- Don't test private methods directly — test through public API

## Integration with build agent

The `build` agent should:
1. Refuse to add a feature without a failing test (escalate if user objects)
2. Run tests after every edit
3. Commit only when tests are green
4. Update tests alongside refactors, not separately

## Integration with test agent

The `test` agent should:
1. Add coverage for newly added code (read PR diff if available)
2. Identify missing edge cases in existing tests
3. Improve test readability (naming, structure, fixtures)
4. Run the full suite (not just modified files) periodically
