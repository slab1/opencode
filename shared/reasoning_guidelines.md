# Global Reasoning Guidelines: The Agentic Loop

To move from "Chatbot" behavior (one-shot response) to "Agentic" behavior (iterative problem solving), all OpenCode agents must adhere to the following reasoning framework.

## 1. The "Thought Trace" Pattern (Working Memory)
Before executing any tool or providing a final answer, the agent MUST maintain an internal monologue. This acts as "working memory" to prevent logical leaps and confirmation bias.

**Format:**
`<thought>`
- **Goal**: What am I trying to achieve in this specific step?
- **Context**: What information do I currently have? What is missing?
- **Hypothesis**: I suspect that X is true because of Y.
- **Plan**: I will call tool Z to verify this.
- **Risk**: If tool Z returns A, it means B; if it returns C, it means D.
`</thought>`

**Rule**: The `<thought>` block must precede every tool call and the final response.

## 2. The "Signal-First" Iteration
Convergence on the correct answer requires a **Feedback Signal**.
- **Coding**: The signal is the Test Result.
- **Research**: The signal is the Source Verification (comparing two independent sources).
- **Trading**: The signal is the Adversarial Critique (Skeptic Agent).

**Rule**: Do not mark a task as "complete" until a verification signal has been obtained and processed.

## 3. Planning Loop & Safety Rails
Autonomous loops must be bound by three non-negotiable rails:

### A. The Budget (Token/Step Limit)
- Every loop must have a `max_steps` limit (default: 10).
- If the limit is reached without a resolution, the agent must stop and report "Budget Exhausted" along with the current best hypothesis.

### B. Reflection (The "Step Back" Moment)
- After every 3 steps, the agent MUST perform a "Meta-Review":
  - "Am I circling the same problem?"
  - "Is my current hypothesis still supported by the data?"
  - "Is there a simpler path I missed?"

### C. Escalation (The Human-in-the-Loop)
- If the agent encounters a "Hard Blocker" (e.g., permission denied, contradictory ground-truth, missing critical API key), it must **Escalate immediately**.
- **Escalation Format**: `ESC_REQUIRED: [Reason] | [Suggested Resolution]`.

## 4. Dynamic Tooling (MCP)
- Treat tools as dynamic capabilities.
- If a tool fails, do not assume it is "broken"; assume the *input* was wrong or the *environment* changed.
- Attempt one alternative approach before escalating.
