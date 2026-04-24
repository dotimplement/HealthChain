# Maintainers Guide

Internal reference for maintainers. Not contributor-facing.

## Governance

HealthChain is run as a [benevolent dictatorship](https://producingoss.com/en/benevolent-dictator.html). @jenniferjiangkells makes the final call on roadmap, architecture, and what gets merged. This isn't a committee — if there's disagreement, I decide.

## Current maintainers

- @jenniferjiangkells — lead maintainer, roadmap, architecture, core reviews
- @adamkells — PR triage, housekeeping, developer advocate for AI/ML contributors

**Division of responsibility:** @jenniferjiangkells owns what gets built and when. Co-maintainers owns first-pass triage and community touchpoints. When in doubt, ask me before merging or closing anything non-obvious.

---

## What's in scope for external contribution right now

Only issues labelled [`help wanted`](https://github.com/healthchainai/HealthChain/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22). Everything else is either maintainer-only or not ready for external pickup. If someone opens a PR against an issue without `help wanted`, close it politely and redirect to the issue.

---

## PR triage — close criteria

Close without detailed review if any of these apply:

- **No linked `help wanted` issue** — close, ask them to find or open an issue first
- **Didn't comment on the issue before opening the PR** — close, ask them to follow the process
- **Touches `healthchain/` core code without maintainer alignment** — close, redirect to a Discussion or comment on the issue
- **Looks AI-generated without clear human context** — see below
- **PR description is generic** ("fixes the issue", "adds the feature") with no explanation of choices — ask one pointed question; if they can't answer it, close it
- **Scope creep** — PR does more than the linked issue describes — ask them to split it or revert to scope

When closing, use a short, non-judgmental message. Template:

> Thanks for the contribution! This one doesn't meet our current contribution criteria — [specific reason]. Feel free to [redirect action]. Happy to answer questions in the issue or on Discord.

---

## Handling AI-generated PRs

Signs to watch for:

- Generic commit messages ("Update file.py", "Fix issue")
- PR description that summarises the code but doesn't explain _why_
- No prior comment on the issue
- Code that passes tests but misses context (e.g. touches things outside the stated scope)

**What to do:** Ask one specific question about a non-obvious decision in the PR. A human who wrote the code can answer it. Someone who generated it usually can't or gives a generic response. If no satisfactory answer, close with the template above.

We don't ban AI-assisted PRs — we require that the contributor can explain and own every decision.

---

## Developer advocate role (AI/ML devs)

Primary touchpoint for the [cookbook contributor issue (#208)](https://github.com/healthchainai/HealthChain/issues/208) and AI/ML dev questions in Discord.

**Responsibilities:**

- Read use case comments on #208 and flag promising ones to @jenniferjiangkells
- Answer basic setup and FHIR questions in Discord / Discussions
- First-pass review on cookbook PRs (structure, completeness, runs end-to-end) — flag to @jenniferjiangkells for final merge
- Keep an eye on whether cookbook docs stay in sync with code changes

**You don't need to know the full roadmap for this.** If someone asks about future features or roadmap, redirect to GitHub Discussions or Discord and tag me.

---

## Merging

- **Cookbooks and docs**: co-maintainers can merge after @jenniferjiangkells approves, or independently for obviously correct small fixes (typos, broken links)
- **Tests**: co-maintainers can merge straightforward additions after confirming tests pass
- **Anything in `healthchain/`**: @jenniferjiangkells reviews and merges
- **When unsure**: leave a comment tagging @jenniferjiangkells, don't merge
