---
name: research-research-paper-writing
title: Research Paper Writing Pipeline
description: "Write ML papers for NeurIPS/ICML/ICLR: design→submit."
version: 1.1.0
author: Orchestra Research
license: MIT
dependencies: [semanticscholar, arxiv, habanero, requests, scipy, numpy, matplotlib, SciencePlots]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Research, Paper Writing, Experiments, ML, AI, NeurIPS, ICML, ICLR, ACL, AAAI, COLM, LaTeX, Citations, Statistical Analysis]
    category: research
    related_skills: [arxiv, ml-paper-writing, subagent-driven-development, plan]
    requires_toolsets: [terminal, files]

---

# Research Paper Writing Pipeline

End-to-end pipeline for producing publication-ready ML/AI research papers targeting **NeurIPS, ICML, ICLR, ACL, AAAI, and COLM**. This skill covers the full research lifecycle: experiment design, execution, monitoring, analysis, paper writing, review, revision, and submission.

This is **not a linear pipeline** — it is an iterative loop. Results trigger new experiments. Reviews trigger new analysis. The agent must handle these feedback loops.

<!-- ascii-guard-ignore -->
```
┌─────────────────────────────────────────────────────────────┐
│                    RESEARCH PAPER PIPELINE                  │
│                                                             │
│  Phase 0: Project Setup ──► Phase 1: Literature Review      │
│       │                          │                          │
│       ▼                          ▼                          │
│  Phase 2: Experiment     Phase 5: Paper Drafting ◄──┐      │
│       Design                     │                   │      │
│       │                          ▼                   │      │
│       ▼                    Phase 6: Self-Review      │      │
│  Phase 3: Execution &           & Revision ──────────┘      │
│       Monitoring                 │                          │
│       │                          ▼                          │
│       ▼                    Phase 7: Submission               │
│  Phase 4: Analysis ─────► (feeds back to Phase 2 or 5)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
<!-- ascii-guard-ignore-end -->

---

## When To Use This Skill

Use this skill when:
- **Starting a new research paper** from an existing codebase or idea
- **Designing and running experiments** to support paper claims
- **Writing or revising** any section of a research paper
- **Preparing for submission** to a specific conference or workshop
- **Responding to reviews** with additional experiments or revisions
- **Converting** a paper between conference formats
- **Writing non-empirical papers** — theory, survey, benchmark, or position papers (see [Paper Types Beyond Empirical ML](#paper-types-beyond-empirical-ml))
- **Designing human evaluations** for NLP, HCI, or alignment research
- **Preparing post-acceptance deliverables** — posters, talks, code releases

## Core Philosophy

1. **Be proactive.** Deliver complete drafts, not questions. Scientists are busy — produce something concrete they can react to, then iterate.
2. **Never hallucinate citations.** AI-generated citations have ~40% error rate. Always fetch programmatically. Mark unverifiable citations as `[CITATION NEEDED]`.
3. **Paper is a story, not a collection of experiments.** Every paper needs one clear contribution stated in a single sentence. If you can't do that, the paper isn't ready.
4. **Experiments serve claims.** Every experiment must explicitly state which claim it supports. Never run experiments that don't connect to the paper's narrative.
5. **Commit early, commit often.** Every completed experiment batch, every paper draft update — commit with descriptive messages. Git log is the experiment history.

### Proactivity and Collaboration

**Default: Be proactive. Draft first, ask with the draft.**

| Confidence Level | Action |
|-----------------|--------|
| **High** (clear repo, obvious contribution) | Write full draft, deliver, iterate on feedback |
| **Medium** (some ambiguity) | Write draft with flagged uncertainties, continue |
| **Low** (major unknowns) | Ask 1-2 targeted questions via `clarify`, then draft |

| Section | Draft Autonomously? | Flag With Draft |
|---------|-------------------|-----------------|
| Abstract | Yes | "Framed contribution as X — adjust if needed" |
| Introduction | Yes | "Emphasized problem Y — correct if wrong" |
| Methods | Yes | "Included details A, B, C — add missing pieces" |
| Experiments | Yes | "Highlighted results 1, 2, 3 — reorder if needed" |
| Related Work | Yes | "Cited papers X, Y, Z — add any I missed" |

**Block for input only when**: target venue unclear, multiple contradictory framings, results seem incomplete, explicit request to review first.

---

## Phase 0: Project Setup

**Goal**: Establish the workspace, understand existing work, identify the contribution.

**Detail**: [references/phase-0-project-setup.md](references/phase-0-project-setup.md)

- Step 0.1: Explore the Repository
- Step 0.2: Organize the Workspace
- Step 0.3: Set Up Version Control
- Step 0.4: Identify the Contribution
- Step 0.5: Create a TODO List
- Step 0.6: Estimate Compute Budget
- Step 0.7: Multi-Author Coordination

---

## Phase 1: Literature Review

**Goal**: Find related work, identify baselines, gather citations.

**Detail**: [references/phase-1-literature-review.md](references/phase-1-literature-review.md)

- Step 1.1: Identify Seed Papers
- Step 1.2: Search for Related Work
- Step 1.2b: Deepen the Search (Breadth-First, Then Depth)
- Step 1.3: Verify Every Citation
- Step 1.4: Organize Related Work

---

## Phase 2: Experiment Design

**Goal**: Design experiments that directly support paper claims. Every experiment must answer a specific question.

**Detail**: [references/phase-2-experiment-design.md](references/phase-2-experiment-design.md)

- Step 2.1: Map Claims to Experiments
- Step 2.2: Design Baselines
- Step 2.3: Define Evaluation Protocol
- Step 2.4: Write Experiment Scripts
- Step 2.5: Design Human Evaluation (If Applicable)

---

## Phase 3: Experiment Execution & Monitoring

**Goal**: Run experiments reliably, monitor progress, recover from failures.

**Detail**: [references/phase-3-execution-monitoring.md](references/phase-3-execution-monitoring.md)

- Step 3.1: Launch Experiments
- Step 3.2: Set Up Monitoring (Cron Pattern)
- Step 3.3: Handle Failures
- Step 3.4: Commit Completed Results
- Step 3.5: Maintain an Experiment Journal

---

## Phase 4: Result Analysis

**Goal**: Extract findings, compute statistics, identify the story.

**Detail**: [references/phase-4-result-analysis.md](references/phase-4-result-analysis.md)

- Step 4.1: Aggregate Results
- Step 4.2: Statistical Significance
- Step 4.3: Identify the Story
- Step 4.4: Create Figures and Tables
- Step 4.5: Decide: More Experiments or Write?
- Step 4.6: Write the Experiment Log (Bridge to Writeup)

---

## Iterative Refinement: Strategy Selection

**Detail**: [references/refinement-strategy-selection.md](references/refinement-strategy-selection.md)

- Quick Decision Table
- The Generation-Evaluation Gap
- Autoreason Loop (Summary)
- Applying to Paper Drafts
- Failure Modes

---

## Phase 5: Paper Drafting

**Goal**: Write a complete, publication-ready paper.

**Detail**: [references/paper-drafting-workflow.md](references/paper-drafting-workflow.md) — see also [references/latex-tooling-and-figures.md](references/latex-tooling-and-figures.md).

- Context Management for Large Projects
- The Narrative Principle
- The Sources Behind This Guidance
- Time Allocation
- Writing Workflow
- Two-Pass Refinement Pattern
- LaTeX Error Checklist
- Step 5.0: Title
- Step 5.1: Abstract (5-Sentence Formula)
- Step 5.2: Figure 1
- Step 5.3: Introduction (1-1.5 pages max)
- Step 5.4: Methods
- Step 5.5: Experiments & Results
- Step 5.6: Related Work
- Step 5.7: Limitations (REQUIRED)
- Step 5.8: Conclusion & Discussion
- Step 5.9: Appendix Strategy
- Page Budget Management
- Step 5.10: Ethics & Broader Impact Statement
- Step 5.11: Datasheets & Model Cards (If Applicable)
- Writing Style

---

## Phase 6: Self-Review & Revision

**Goal**: Simulate the review process before submission. Catch weaknesses early.

**Detail**: [references/phase-6-self-review.md](references/phase-6-self-review.md)

- Step 6.1: Simulate Reviews (Ensemble Pattern)
- Step 6.1b: Visual Review Pass (VLM)
- Step 6.1c: Claim Verification Pass
- Step 6.2: Prioritize Feedback
- Step 6.3: Revision Cycle
- Step 6.4: Rebuttal Writing
- Step 6.5: Paper Evolution Tracking

---

## Phase 7: Submission Preparation

**Goal**: Final checks, formatting, and submission.

**Detail**: [references/phase-7-submission.md](references/phase-7-submission.md)

- Step 7.1: Conference Checklist
- Step 7.2: Anonymization Checklist
- Step 7.3: Formatting Verification
- Step 7.4: Pre-Compilation Validation
- Step 7.5: Final Compilation
- Step 7.6: Conference-Specific Requirements
- Step 7.7: Conference Resubmission & Format Conversion
- Step 7.8: Camera-Ready Preparation (Post-Acceptance)
- Step 7.9: arXiv & Preprint Strategy
- Step 7.10: Research Code Packaging

---

## Phase 8: Post-Acceptance Deliverables

**Goal**: Maximize the impact of your accepted paper through presentation materials and community engagement.

**Detail**: [references/phase-8-post-acceptance.md](references/phase-8-post-acceptance.md)

- Step 8.1: Conference Poster
- Step 8.2: Conference Talk / Spotlight
- Step 8.3: Blog Post / Social Media

---

## Hermes Agent Integration

**Detail**: [references/hermes-agent-integration.md](references/hermes-agent-integration.md)

- Related Skills
- Hermes Tools Reference
- Tool Usage Patterns
- State Management with `memory` and `todo`
- Cron Monitoring with `cronjob`
- Communication Patterns
- Decision Points Requiring Human Input

## Workshop & Short Papers

Workshop papers and short papers (e.g., ACL short papers, Findings papers) follow the same pipeline but with different constraints and expectations.

### Workshop Papers

| Property | Workshop | Main Conference |
|----------|----------|-----------------|
| **Page limit** | 4-6 pages (typically) | 7-9 pages |
| **Review standard** | Lower bar for completeness | Must be complete, thorough |
| **Review process** | Usually single-blind or light review | Double-blind, rigorous |
| **What's valued** | Interesting ideas, preliminary results, position pieces | Complete empirical story with strong baselines |
| **arXiv** | Post anytime | Timing matters (see arXiv strategy) |
| **Contribution bar** | Novel direction, interesting negative result, work-in-progress | Significant advance with strong evidence |

**When to target a workshop:**
- Early-stage idea you want feedback on before a full paper
- Negative result that doesn't justify 8+ pages
- Position piece or opinion on a timely topic
- Replication study or reproducibility report

### ACL Short Papers & Findings

ACL venues have distinct submission types:

| Type | Pages | What's Expected |
|------|-------|-----------------|
| **Long paper** | 8 | Complete study, strong baselines, ablations |
| **Short paper** | 4 | Focused contribution: one clear point with evidence |
| **Findings** | 8 | Solid work that narrowly missed main conference |

**Short paper strategy**: Pick ONE claim and support it thoroughly. Don't try to compress a long paper into 4 pages — write a different, more focused paper.

---

## Paper Types Beyond Empirical ML

The main pipeline above targets empirical ML papers. Other paper types require different structures and evidence standards. See [references/paper-types.md](references/paper-types.md) for detailed guidance on each type.

### Theory Papers

**Structure**: Introduction → Preliminaries (definitions, notation) → Main Results (theorems) → Proof Sketches → Discussion → Full Proofs (appendix)

**Key differences from empirical papers:**
- Contribution is a theorem, bound, or impossibility result — not experimental numbers
- Methods section replaced by "Preliminaries" and "Main Results"
- Proofs are the evidence, not experiments (though empirical validation of theory is welcome)
- Proof sketches in main text, full proofs in appendix is standard practice
- Experimental section is optional but strengthens the paper if it validates theoretical predictions

**Proof writing principles:**
- State theorems formally with all assumptions explicit
- Provide intuition before formal proof ("The key insight is...")
- Proof sketches should convey the main idea in 0.5-1 page
- Use `\begin{proof}...\end{proof}` environments
- Number assumptions and reference them in theorems: "Under Assumptions 1-3, ..."

### Survey / Tutorial Papers

**Structure**: Introduction → Taxonomy / Organization → Detailed Coverage → Open Problems → Conclusion

**Key differences:**
- Contribution is the organization, synthesis, and identification of open problems — not new methods
- Must be comprehensive within scope (reviewers will check for missing references)
- Requires a clear taxonomy or organizational framework
- Value comes from connections between works that individual papers don't make
- Best venues: TMLR (survey track), JMLR, Foundations and Trends in ML, ACM Computing Surveys

### Benchmark Papers

**Structure**: Introduction → Task Definition → Dataset Construction → Baseline Evaluation → Analysis → Intended Use & Limitations

**Key differences:**
- Contribution is the benchmark itself — it must fill a genuine evaluation gap
- Dataset documentation is mandatory, not optional (see Datasheets, Step 5.11)
- Must demonstrate the benchmark is challenging (baselines don't saturate it)
- Must demonstrate the benchmark measures what you claim it measures (construct validity)
- Best venues: NeurIPS Datasets & Benchmarks track, ACL (resource papers), LREC-COLING

### Position Papers

**Structure**: Introduction → Background → Thesis / Argument → Supporting Evidence → Counterarguments → Implications

**Key differences:**
- Contribution is an argument, not a result
- Must engage seriously with counterarguments
- Evidence can be empirical, theoretical, or logical analysis
- Best venues: ICML (position track), workshops, TMLR
## Reviewer Evaluation Criteria

Understanding what reviewers look for helps focus effort:

| Criterion | What They Check |
|-----------|----------------|
| **Quality** | Technical soundness, well-supported claims, fair baselines |
| **Clarity** | Clear writing, reproducible by experts, consistent notation |
| **Significance** | Community impact, advances understanding |
| **Originality** | New insights (doesn't require new method) |

**Scoring (NeurIPS 6-point scale):**
- 6: Strong Accept — groundbreaking, flawless
- 5: Accept — technically solid, high impact
- 4: Borderline Accept — solid, limited evaluation
- 3: Borderline Reject — weaknesses outweigh
- 2: Reject — technical flaws
- 1: Strong Reject — known results or ethics issues

See [references/reviewer-guidelines.md](references/reviewer-guidelines.md) for detailed guidelines, common concerns, and rebuttal strategies.

---

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Abstract too generic | Delete first sentence if it could prepend any ML paper. Start with your specific contribution. |
| Introduction exceeds 1.5 pages | Split background into Related Work. Front-load contribution bullets. |
| Experiments lack explicit claims | Add: "This experiment tests whether [specific claim]..." before each one. |
| Reviewers find paper hard to follow | Add signposting, use consistent terminology, make figure captions self-contained. |
| Missing statistical significance | Add error bars, number of runs, statistical tests, confidence intervals. |
| Scope creep in experiments | Every experiment must map to a specific claim. Cut experiments that don't. |
| Paper rejected, need to resubmit | See Conference Resubmission in Phase 7. Address reviewer concerns without referencing reviews. |
| Missing broader impact statement | See Step 5.10. Most venues require it. "No negative impacts" is almost never credible. |
| Human eval criticized as weak | See Step 2.5 and [references/human-evaluation.md](references/human-evaluation.md). Report agreement metrics, annotator details, compensation. |
| Reviewers question reproducibility | Release code (Step 7.9), document all hyperparameters, include seeds and compute details. |
| Theory paper lacks intuition | Add proof sketches with plain-language explanations before formal proofs. See [references/paper-types.md](references/paper-types.md). |
| Results are negative/null | See Phase 4.3 on handling negative results. Consider workshops, TMLR, or reframing as analysis. |

## Reference Documents

| Document | Contents |
|----------|----------|
| [references/writing-guide.md](references/writing-guide.md) | Gopen & Swan 7 principles, Perez micro-tips, Lipton word choice, Steinhardt precision, figure design |
| [references/citation-workflow.md](references/citation-workflow.md) | Citation APIs, Python code, CitationManager class, BibTeX management |
| [references/checklists.md](references/checklists.md) | NeurIPS 16-item, ICML, ICLR, ACL requirements, universal pre-submission checklist |
| [references/reviewer-guidelines.md](references/reviewer-guidelines.md) | Evaluation criteria, scoring, common concerns, rebuttal template |
| [references/sources.md](references/sources.md) | Complete bibliography of all writing guides, conference guidelines, APIs |
| [references/experiment-patterns.md](references/experiment-patterns.md) | Experiment design patterns, evaluation protocols, monitoring, error recovery |
| [references/autoreason-methodology.md](references/autoreason-methodology.md) | Autoreason loop, strategy selection, model guide, prompts, scope constraints, Borda scoring |
| [references/human-evaluation.md](references/human-evaluation.md) | Human evaluation design, annotation guidelines, agreement metrics, crowdsourcing QC, IRB guidance |
| [references/paper-types.md](references/paper-types.md) | Theory papers (proof writing, theorem structure), survey papers, benchmark papers, position papers |
| [references/phase-0-project-setup.md](references/phase-0-project-setup.md) | Phase 0 detail: repo exploration, workspace layout, git discipline, contribution statement, TODO list, compute budget, multi-author coordination. **Load when** starting a new paper. |
| [references/phase-1-literature-review.md](references/phase-1-literature-review.md) | Phase 1 detail: seed papers, breadth-then-depth search, mandatory 5-step citation verification, organizing related work. **Load when** doing literature review. |
| [references/phase-2-experiment-design.md](references/phase-2-experiment-design.md) | Phase 2 detail: claim→experiment mapping, baseline design, evaluation protocol, experiment scripts, human evaluation design. **Load when** designing experiments. |
| [references/phase-3-execution-monitoring.md](references/phase-3-execution-monitoring.md) | Phase 3 detail: launching with nohup, cron monitoring template, failure recovery table, experiment journal format. **Load when** running long experiments. |
| [references/phase-4-result-analysis.md](references/phase-4-result-analysis.md) | Phase 4 detail: aggregation scripts, statistical significance, negative-result handling, figures/tables, `experiment_log.md`. **Load when** analysing results. |
| [references/refinement-strategy-selection.md](references/refinement-strategy-selection.md) | Refinement strategy selection: quick decision table, generation-evaluation gap, autoreason loop, failure modes. **Load when** choosing how to iterate on an artifact. |
| [references/paper-drafting-workflow.md](references/paper-drafting-workflow.md) | Phase 5 detail: context management, narrative principle, time allocation, two-pass refinement, LaTeX error checklist, per-section requirements (Steps 5.0-5.11), writing style. **Load when** drafting. |
| [references/latex-tooling-and-figures.md](references/latex-tooling-and-figures.md) | LaTeX templates, template pitfalls, conference page limits, professional preamble, siunitx, subfigures, algorithm2e, TikZ, latexdiff, SciencePlots. **Load when** building the LaTeX artifact or figures. |
| [references/phase-6-self-review.md](references/phase-6-self-review.md) | Phase 6 detail: ensemble simulated reviews + meta-review, visual review pass, claim verification pass, feedback triage, rebuttal writing, version snapshots. **Load when** self-reviewing. |
| [references/phase-7-submission.md](references/phase-7-submission.md) | Phase 7 detail: venue checklists, anonymization, formatting and pre-compilation validation, final compilation, format conversion, camera-ready, arXiv strategy, code packaging. **Load when** submitting. |
| [references/phase-8-post-acceptance.md](references/phase-8-post-acceptance.md) | Phase 8 detail: conference poster, talk/spotlight, blog and social summaries. **Load when** preparing post-acceptance deliverables. |
| [references/hermes-agent-integration.md](references/hermes-agent-integration.md) | Hermes runtime integration: related skills, Hermes tools, tool usage patterns, `memory`/`todo` state management, cron monitoring, communication patterns, decision points. **Load when** wiring the pipeline into Hermes. |

### LaTeX Templates

Templates in `templates/` for: **NeurIPS 2025**, **ICML 2026**, **ICLR 2026**, **ACL**, **AAAI 2026**, **COLM 2025**.

See [templates/README.md](templates/README.md) for compilation instructions.

### Key External Sources

**Writing Philosophy:**
- [Neel Nanda: How to Write ML Papers](https://www.alignmentforum.org/posts/eJGptPbbFPZGLpjsp/highly-opinionated-advice-on-how-to-write-ml-papers)
- [Sebastian Farquhar: How to Write ML Papers](https://sebastianfarquhar.com/on-research/2024/11/04/how_to_write_ml_papers/)
- [Gopen & Swan: Science of Scientific Writing](https://cseweb.ucsd.edu/~swanson/papers/science-of-writing.pdf)
- [Lipton: Heuristics for Scientific Writing](https://www.approximatelycorrect.com/2018/01/29/heuristics-technical-scientific-writing-machine-learning-perspective/)
- [Perez: Easy Paper Writing Tips](https://ethanperez.net/easy-paper-writing-tips/)

**APIs:** [Semantic Scholar](https://api.semanticscholar.org/api-docs/) | [CrossRef](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | [arXiv](https://info.arxiv.org/help/api/basics.html)

**Venues:** [NeurIPS](https://neurips.cc/Conferences/2025/PaperInformation/StyleFiles) | [ICML](https://icml.cc/Conferences/2025/AuthorInstructions) | [ICLR](https://iclr.cc/Conferences/2026/AuthorGuide) | [ACL](https://github.com/acl-org/acl-style-files)
