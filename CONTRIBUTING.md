# Contributing

Thank you for your interest in contributing to HealthChain!

Before you start, please read this guide to understand how to propose changes, open pull requests, and collaborate effectively.

## ✅ Before you open a pull request
To keep reviews efficient and maintain project quality, PRs must meet these basics (or may be closed without in‑depth review):

- [ ] Small, focused on a single change or issue
- [ ] Links to at least one [`GitHub Issue`](https://github.com/dotimplement/HealthChain/issues) or [`RFC`](https://github.com/dotimplement/HealthChain/tree/main/docs/rfcs) (Request for Comments) with context and trade‑offs explained in the description
- [ ] All tests pass locally; new functionality has tests and docs
- [ ] For `core`, `Stage: Research 🔬`, or `Stage: Design 🎨` labels: has accepted RFC
- [ ] Not sure about scope? Open a [GitHub Discussion](https://github.com/dotimplement/HealthChain/discussions) first

## Contributing health & domain expertise

Real‑world experience from healthcare, public health, and digital health products is crucial for making HealthChain useful and safe.

You can contribute domain expertise by:

- Opening [`Issues`](https://github.com/dotimplement/HealthChain/issues) or [`Discussions`](https://github.com/dotimplement/HealthChain/discussions) that describe real workflows, data models (e.g. FHIR resources), regulatory or security constraints, and integration needs.
- Commenting on `Stage: Research 🔬` and `Stage: Design 🎨` issues with context from clinical practice, informatics, or implementation experience.
- Co‑authoring RFCs that capture requirements for consent, auditing, interoperability, and safety‑related behaviors.

When you open a domain‑focused issue, please include:

- Context (setting, jurisdiction, type of organization).
- The problem you are trying to solve.
- Any relevant standards (FHIR profiles, policies, regulations) and links.

## 🤝 For integrators, companies, and partners

If you are exploring HealthChain for use in your product or organization, or want to co‑design an integration or partnership:

**For substantial partnerships or integrations:**
- Shoot me an [email](mailto:jenniferjiangkells@gmail.com?subject=HealthChain)
- Join our [weekly office hours](https://meet.google.com/zwh-douu-pky) (Thursdays 4.30pm - 5.30pm GMT) for direct Q&A
- Join the [Discord](https://discord.gg/UQC6uAepUz) `#production-users` channel

**For feature collaborations:**
Once we've aligned on a collaboration, we'll track it using GitHub issues with stage labels:
- **Stage: Research 🔬** = Gathering requirements and exploring the problem space
- **Stage: Design 🎨** = Designing the solution (often via RFC for core features)
- Co-authored RFCs welcome for features you're willing to help build/maintain

**For exploratory technical discussions:**
Use [GitHub Discussions](https://github.com/dotimplement/HealthChain/discussions) to brainstorm architecture options and gather community input.

**We're particularly interested in:**
- Pilot deployments and production integrations
- Co-maintained adapters for specific EHR systems
- Sponsored features with committed engineering resources
- Research collaborations and case studies

## 🐛 Reporting Issues

Found a bug? Have a suggestion for a new feature? You can help us improve by:

- **Submitting Bug Reports**: Clearly describe the issue, steps to reproduce, expected outcome, actual outcome, and any relevant logs or screenshots.
- **Suggesting Enhancements**: Describe the problem you face, not only your proposed solution. Include user stories, constraints, and any alternatives considered.

For broad, exploratory ideas or "is this a good idea?" questions, please prefer [GitHub Discussions](https://github.com/dotimplement/HealthChain/discussions) over large PRs.

- Use the `Ideas` category for high‑level proposals.
- Link any related Discussion from the corresponding issue if applicable.
- Once there is a concrete proposal, move to an RFC PR so we have a stable, version‑controlled record of the design.

## 📚 Improving Documentation

Good documentation is critical in healthcare. You can help by:

- **Updating Existing Documentation**: Fixing inaccuracies, clarifying concepts, and keeping examples and setup instructions current.
- **Creating New Documentation**: Writing guides, tutorials, implementation notes, or health‑domain explainers that help others adopt and safely operate HealthChain.

When writing docs:

- Prefer clear, concise language and use headings and lists for structure.
- Include code snippets or configuration examples where helpful.
- Call out assumptions, limitations, and safety‑relevant behaviour explicitly.

## 💻 Writing Code

>**New to HealthChain?** Look for [`good first issue`](https://github.com/dotimplement/HealthChain/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) and [`help wanted`](https://github.com/dotimplement/HealthChain/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) labels.

**Check the [project board](https://github.com/orgs/dotimplement/projects/1/views/1)** to see current priorities and what's actively being worked on.

You can contribute code by:

- **Fixing Bugs**: Pick issues labelled [`Issue: Bug 🐛`](https://github.com/dotimplement/HealthChain/issues?q=is%3Aissue+is%3Aopen+label%3A%22Issue%3A+Bug+%F0%9F%90%9B%22) and reference the issue number in your commits and PR.
- **Implementing Features**: For non‑trivial features, start with an issue or Discussion to confirm scope and fit, and use the RFC process for anything touching core areas.
- **Improving Tests**: Increase coverage, add regression tests for fixed bugs, and improve reliability of existing test suites.

### Core Changes and RFCs

Some changes have a large impact on security, architecture, and stability. These are gated by an RFC (Request for Comments) process and specific labels:

- `Stage: Research 🔬`: The problem and constraints are being explored; we are collecting context and options, not implementations.
- `Stage: Design 🎨`: The problem is understood and we are working towards a concrete design; implementation is not yet agreed.
- `core`: High‑impact or security‑sensitive changes (e.g. authentication, authorization, data model, API contracts, persistence, deployment architecture).

For issues with any of these labels:

- An agreed RFC is required before implementation PRs are opened.
- Implementation PRs must link to the accepted RFC and follow the agreed approach.
- PRs that bypass this process may be closed without detailed review.

For larger changes, especially related to authentication/authorization, persistence, public API, or deployment/operations:

- Check for an existing `Stage: Research 🔬`, `Stage: Design 🎨`, or `core` issue.
- Comment on the issue or start a [`GitHub Discussion`](https://github.com/dotimplement/HealthChain/discussions) if the problem or approach is unclear.
- Follow the [`RFC process`](#how-to-create-an-rfc) before opening an implementation PR.

**Quick reference:**
- 🔴 **RFC required**: Auth, specification implementation (SMART on FHIR, CDS Hooks, etc.), security, persistence, API contracts
- 🟡 **Discussion recommended**: New gateways/pipelines, significant I/O loaders, breaking changes
- 🟢 **No RFC needed**: Bug fixes, docs, tests, small refactors

## 📋 How to Create an RFC

For `Stage: Research 🔬`, `Stage: Design 🎨`, and `core` issues, RFCs are used to agree on the approach before writing significant code.

RFCs live in this repository under `docs/rfcs/`. To propose an RFC:

1. Pick an open issue with a stage/core label, or open a new issue describing the problem and context.
2. Copy `docs/rfcs/000-template.md` to `docs/rfcs/NNN-short-title.md` (replace `NNN` with the next number and `short-title` with a short description).
3. Fill in the template with problem, goals, proposed design, risks, and impact.
4. Open a pull request titled `RFC: <Short title>`, linking to the related issue (and any Discussions).
5. Maintainers and contributors will review, ask questions, and suggest changes.
6. Once there is consensus, a maintainer will set the `Status` to `Accepted` or `Rejected` and merge or close the PR.

### After an RFC is Accepted

- You (or another contributor) can open implementation PRs that state `Implements RFC NNN: <title>` and link back to the RFC.
- If an implementation PR diverges from the accepted RFC in a significant way, we may ask for a follow‑up RFC or additional design discussion.

## 💬 Join our Discord

If you are:

- Evaluating HealthChain for your organisation or product
- A clinician, informatician, or health data specialist
- Interested in co‑designing features, integrations, or pilots

…join our [Discord](https://discord.gg/UQC6uAepUz) community for quick questions and discussions. This is often the easiest way to discuss integrations, deployment questions, and partnership ideas before formalizing them in issues or RFCs.

## ⚙️ How to Contribute Code

This project uses `uv` for dependency management. See the [uv documentation](https://docs.astral.sh/uv/) for more information.

1. [Fork the repository to your own GitHub account](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo).
2. Clone your fork locally.
3. Run `uv sync --all-extras --dev` to install all development dependencies.
4. Run `uv run pytest` to ensure tests pass.
5. Create a new branch for your change:

    ```shell
    git checkout -b my-feature-branch
    ```
6. Install pre‑commit hooks (after installing [pre-commit](https://pre-commit.com/)):
    ```shell
    pre-commit install
    ```
7. Make your changes and commit them with descriptive messages:

    ```shell
    git commit -m "Add new feature to do X"
    ```
8. Push your changes to your fork:

    ```shell
    git push origin my-feature-branch
    ```
9.  Open a pull request on the main repository.

### Contributing to Documentation

To work on the documentation site ([MkDocs](https://www.mkdocs.org/)):

- Install the doc dependencies:

    ```shell
    uv sync --group docs
    ```
- Run the docs site locally:

    ```shell
    uv run mkdocs serve
    ```
When contributing docs:

- Use clear headings and subheadings.
- Prefer examples and concrete scenarios, especially for health workflows and integrations.
- Keep style consistent and use active voice.

## 🧪 Testing

All new functionality must include tests, and all existing tests must pass.

- Add or update unit/integration tests to cover your changes.
- Run `uv run pytest` before opening or updating a PR.
- If tests are flaky or slow, mention this in the PR so maintainers can help improve them.


## 🔍 Pull request expectations

When opening a PR:

- Ensure your changes follow the style guide and pass all tests.
- Use a clear, descriptive title and explain what the PR does and why.
- Link related issues and RFCs (e.g. Closes #123, Implements RFC 004).
- Describe how you tested your changes and any known limitations or follow‑ups.


## 🤖 Tooling and AI Assistance

We welcome and encourage the use of AI tools to support development, but contributors remain responsible for the changes they submit.

- Make sure you understand every line of code and can explain the design and trade‑offs.
- All code changes must be understood and reviewed by humans.
- Maintainers reserve the right to close low-context, unexplained, AI-generated PRs without detailed review.

For broader project context, see the [CLAUDE.md](CLAUDE.MD) file.
