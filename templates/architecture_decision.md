# Architecture Decision Memo

## Decision
I would prefer the single agent architecture and ship it today. The latency numbers for single agent workflows are significantly better than the staged workflows, and it is also simpler to reason about the code. It is currently sufficient for the client's problems and is enough for the MVP.

## Evidence

| Metric | Single agent | Staged / 2-agent |
|---|---:|---:|
| Cases passing your quality criteria | 6/6 | 6/6 |
| Avg latency | 6.5 ms | 11.3 ms |
| Avg LLM calls | 0 | 0 |
| Avg tool calls | 5 | 7 |
| Notable policy/grounding failures | 0 | 0 |

## Trade-offs
The single agent workflow is clearly faster and simpler than the staged workflow. It is also cheaper because it uses fewer tools and has lower latency. 

When I integrated the staging workflow, there was no improvements on the current evals. The cost that it came with was 2 more tool calls, +4.8 ms in latency. With no accuracy gain, it was more sensible to stay with single agent workflow.

If in the staged workflow we were integrating a LLM call and leveraging it to do the policy checks, handling injections and re-evaluating the policy, it would make sense to have the staged workflow. However, at the moment all of these checks are deterministic and can be done in a single pass.

## Risks / limitations
Before shipping it to production, I would run the automated tests against a larger dataset to ensure the robustness of the solution. I would also test for edge cases such as 365 day edge cases, new injection phrases, duplicate use edge case, etc. 

I would also address the current limitation which is a no LLM call and all reasoning being done using Deterministic checks and reviews. Integrating LLM calls for policy checks, summarization, injection preventions would be a great improvement to the current MVP and would make it fit to be shipped to production.

Overlap is currently catalog product/vendor/category (OR logic); `purchase_history.csv` renewals/duplicate-seats not yet reasoned over.

## Why this is the right MVP
The single agent workflow is sufficient for the client problem because it is able to handle all of the requirements of the client problem without unnecessary orchestration. It is also simple to reason about and has low latency. This makes it a good candidate for an MVP.

`CODE` does thresholds/budget/expiry, `HUMAN` approves (human_review_required=True always), `AI` slot intentionally empty - deterministic is sufficient and cheaper for MVP; add LLM only when free-text justification quality becomes bottleneck