# Week 6 — AI Code Review & Testing: Writeup

- **Repository:** https://github.com/Efeblk/week6-habit-tracker
- **Agent used for implementation:** Antigravity (Gemini 4 Argon High, one-shot prompt per feature)
- **AI PR reviewer used:** **CodeRabbit** (after GitHub Copilot review failed with `"insufficient remaining quota"`)
- **Feature PRs:**
  - **PR #1 (`feature/streak`):** [Add `GET /habits/{id}/streak`](https://github.com/Efeblk/week6-habit-tracker/pull/1)
  - **PR #2 (`feature/validation`):** [Validate habit names and check-in days](https://github.com/Efeblk/week6-habit-tracker/pull/2)
- **Comparison PRs (agent-only commits before manual review, closed after CodeRabbit reviewed them):**
  - **PR #3 (`agent-only/streak`):** [Comparison — Streak before manual review](https://github.com/Efeblk/week6-habit-tracker/pull/3)
  - **PR #4 (`agent-only/validation`):** [Comparison — Validation before manual review](https://github.com/Efeblk/week6-habit-tracker/pull/4)

---

## Part I — Deterministic Guardrails

Configured in commit [`e187779`](https://github.com/Efeblk/week6-habit-tracker/commit/e1877796b1b89c30486d10a7fe70b9995de8f6e5) via [`pyproject.toml`](pyproject.toml), [`requirements-dev.txt`](requirements-dev.txt), and [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### Commands

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check .          # Lint: pycodestyle (E/W), pyflakes (F), import sort (I), bugbear (B), pyupgrade (UP)
black --check .       # Format: enforces 100-char line length and consistent formatting
pytest                # Functional regression suite (non-zero exit fails CI on any failing test)
```

### What they catch (and what they cannot)
- **`ruff check .`** catches unused imports/variables, unsorted imports, common Python bugbear pitfalls, and style violations immediately.
- **`black --check .`** prevents formatting drift so PR diffs only contain meaningful changes.
- **`pytest`** verifies endpoint behavior and fails the build (exit code 1) whenever a test fails; GitHub Actions runs all three steps sequentially on every push and pull request.
- **Limitation:** None of these deterministic checks can detect missing test cases, subtle time-dependent flakiness, or whether a feature matches product intent.

---

## Part II — Two Features & Manual vs. AI Review Comparison

### Task 1 — Habit Streak (`GET /habits/{id}/streak`)
- **PR #1:** https://github.com/Efeblk/week6-habit-tracker/pull/1
- **Agent one-shot commit:** [`41ae22c`](https://github.com/Efeblk/week6-habit-tracker/commit/41ae22c1db72eebd4210d4ad19080e33507e0b4c)
- **Manual review fixes commit:** [`df1738c`](https://github.com/Efeblk/week6-habit-tracker/commit/df1738ce9ac72d25e818a1f557decae786d4d8ff)
- **Comparison PR (agent-only commit):** https://github.com/Efeblk/week6-habit-tracker/pull/3

**What manual review caught:**
1. **Midnight boundary flakiness:** Both `main.py` and `test_main.py` called `date.today()` directly. If a test run crossed midnight, the app and test could compute different dates and fail randomly. Fixed by extracting `today()` in `main.py` and pinning `FIXED_TODAY = date(2026, 10, 2)` via a `monkeypatch` fixture in tests.
2. **Test coverage gaps:** The agent's original tests passed, but missed month boundaries, a single check-in today, a missing today (yesterday-only streak = 0), future check-ins, and a habit with zero check-ins. Added dedicated tests for each (9 tests total).
3. **API tradeoff documented:** Explicitly noted the literal "up to and including today" rule (yesterday-only check-in yields streak 0) and server-local timezone assumption.

**What CodeRabbit produced (PR #1 & PR #3):**
- On **PR #1** (after review fixes) and **PR #3** (the raw agent commit `41ae22c` *before* review fixes), CodeRabbit posted **"No actionable comments were generated in the recent review"** and rated Merge Risk as **Minimal**.
- CodeRabbit **missed the `date.today()` midnight test flakiness** and the missing edge-case tests on PR #3.
- Where CodeRabbit added value: its **Security Architecture Review** summarized the blast radius, confirmed parameterized SQL queries, and explicitly noted that the API has no application-level authentication or tenant ownership checks (a pre-existing system property that manual review did not call out).

---

### Task 2 — Input Validation (`POST /habits` & `POST /habits/{id}/checkin`)
- **PR #2:** https://github.com/Efeblk/week6-habit-tracker/pull/2
- **Agent one-shot commit:** [`e2edde5`](https://github.com/Efeblk/week6-habit-tracker/commit/e2edde51e6fb43c1062bdb479e8c909cddcf717a)
- **Manual review fixes commit:** [`9e92af3`](https://github.com/Efeblk/week6-habit-tracker/commit/9e92af36fc646b190e9ee18d085e458be1660ee5)
- **Comparison PR (agent-only commit):** https://github.com/Efeblk/week6-habit-tracker/pull/4

**What manual review caught:**
1. **Untested behavior:** The agent trimmed whitespace from habit names in `HabitIn.validate_name` without any test asserting that `"  Read  "` is persisted as `"Read"`.
2. **Non-canonical ISO date test gaps:** The agent's validator already round-tripped `parsed.isoformat() != v` (rejecting non-`YYYY-MM-DD` strings accepted by Python 3.11+ `date.fromisoformat`), and tested `20260922`, but grouped bad inputs together and never tested ISO week dates (`2026-W39-2`), single-digit months (`2026-9-22`), leading spaces, or valid leap days (`2028-02-29`). Split these into `@pytest.mark.parametrize` cases and added a leap-day test (17 tests total).
3. **Maintainability:** Extracted the duplicated validation error string into a shared `BAD_DAY_MESSAGE` constant.

**What CodeRabbit produced (PR #2 & PR #4):**
- On both **PR #2** and **PR #4** (the raw agent commit `e2edde5`), CodeRabbit posted **"No actionable comments were generated in the recent review"** and rated Merge Risk as **Minimal**.
- CodeRabbit **missed the untested trimming behavior and missing parametrized edge cases** on PR #4.
- Where CodeRabbit added value: its **Security Architecture Review** accurately verified that validation happens at the Pydantic request-model boundary with SQL parameter binding intact, and flagged that retrying a `POST /habits/{id}/checkin` request still creates duplicate rows because there is no idempotency key or `(habit_id, day)` uniqueness constraint.

---

### Comparison Summary

| Dimension | Manual Review | CodeRabbit (AI Review) |
|---|---|---|
| **Where it was better** | Caught non-deterministic `date.today()` midnight flakiness in PR #1/#3; spotted untested name trimming and missing parametrized date cases (`2026-W39-2`, `2026-9-22`, leading space, leap day) in PR #2/#4; improved test structure and constant reuse. | Produced clear, fast PR walkthroughs and release notes; systematically checked security blast radius, SQL parameter binding, missing auth/tenant boundaries, and non-idempotent POST retries. |
| **Where it was worse** | Slower and more tedious; did not systematically document pre-existing architectural traits like missing auth/ownership checks. | Generated **zero actionable line comments** even on the unreviewed agent-only commits (PR #3 and PR #4), missing both the midnight test bug and the test-coverage gaps. |

---

## What I Learned

Working on the habit-tracker API showed me how deterministic guardrails and LLM reviews complement each other: linters (`ruff`, `black`) and `pytest` filter out obvious syntax, formatting, and regression issues upfront, freeing reviewers to focus on logic and edge cases. However, seeing all tests pass despite a hidden midnight boundary bug—and realizing that `fromisoformat` silently accepts ISO week formats like `2026-W39-2` which the agent's round-trip check handled but never tested—highlighted the gap between green checks and thorough behavioral verification. Because CodeRabbit produced useful architecture summaries but missed both the midnight bug and those test gaps even on the unreviewed commits, I am comfortable using AI review as a fast sanity check for high-level risk and boilerplate summaries, not as a substitute for careful manual review of subtle domain logic, date handling, or test depth.
