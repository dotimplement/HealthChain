# Contributing

Thanks for your interest in contributing to HealthChain!

## ✅ Before you open a pull request

**We review every PR ourselves. If it would take us less time to write the change with Claude code than to review your PR, we'll close it. No hard feelings.** The bar isn't correctness, it's context: we need to understand _why_ you made the choices you made, not just that the tests pass. A short explanation in the PR description goes a long way.

PRs must meet these basics or may be closed without detailed review:

- [ ] Linked to an open [`help wanted`](https://github.com/healthchainai/HealthChain/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) issue, and you commented on it before starting
- [ ] Small and focused on a single change
- [ ] All tests pass locally; new functionality has tests and docs
- [ ] PR description explains _why_ you made the choices you made
- [ ] Not sure about scope? Open a [GitHub Discussion](https://github.com/healthchainai/HealthChain/discussions) first

## 🤖 AI assistance

We use AI tools ourselves and don't discourage contributors from doing the same. But contributors are responsible for every line they submit.

- You must be able to explain every decision and trade-off in your PR.
- Generic, low-context PRs that look generated will be closed. One pointed question should be easy to answer if you wrote the code.
- Maintainers reserve the right to close AI-generated PRs without detailed review.

## 🤝 For integrators, companies, and partners

If you are exploring HealthChain for use in your product or organization, or want to co‑design an integration or partnership, [send an email](mailto:jenniferjiangkells@gmail.com?subject=HealthChain) — that's the fastest way to get a response.

For technical questions, ideas, or deployment discussions, use [GitHub Discussions](https://github.com/healthchainai/HealthChain/discussions) — keeps a public record and others can benefit from the answers.

**We're particularly interested in:**

- Pilot deployments and production integrations
- Research collaborations and case studies

## 🐛 Reporting issues

Found a bug? Have a suggestion?

- **Bug reports**: Clearly describe the issue, steps to reproduce, expected outcome, actual outcome, and any relevant logs or screenshots.
- **Feature requests**: Describe the problem you face, not just your proposed solution. Include user stories, constraints, and any alternatives considered.

For broad, exploratory ideas, prefer [GitHub Discussions](https://github.com/healthchainai/HealthChain/discussions) over opening issues.

## 📚 Improving documentation

Good documentation is critical in healthcare. You can help by fixing inaccuracies, clarifying concepts, and keeping examples current.

When writing docs:

- Prefer clear, concise language with headings and lists for structure.
- Include code snippets or configuration examples where helpful.
- Call out assumptions, limitations, and safety‑relevant behaviour explicitly.

To work on the documentation site locally:

```shell
uv sync --group docs
uv run mkdocs serve
```

### Writing cookbooks

Cookbooks are often the first thing a developer runs. These principles keep them effective:

- **Reduce time-to-running**: Every prerequisite you can eliminate is a developer you don't lose. Pre-bake demo data and models; collapse advanced setup into `??? details` blocks.
- **Lead with the problem**: The intro should say what pain it solves — "you trained a model on CSVs, now you need to deploy against FHIR data" — not just what the code does.
- **Show HealthChain's unique value**: Each cookbook should have a moment that would be 50+ lines of custom code without HealthChain. Don't bury it.

#### Cookbook structure

Start from the templates — copy and fill them in:

- `cookbook/000-template.py` → your runnable script
- `docs/cookbook/000-template.md` → your documentation page

Each cookbook has three parts:

1. **A runnable Python script** in `cookbook/` — e.g. `cookbook/my_use_case.py`. Pre-bake any data or setup so it works out of the box.
2. **A documentation page** in `docs/cookbook/` — e.g. `docs/cookbook/my_use_case.md`. The narrative page on the docs site, walking through what the script does and why.
3. **Two registration steps** so it appears on the docs site:

   **Add a line to `mkdocs.yml`** under the existing Cookbook section (around line 27):

   ```yaml
   - My Use Case: cookbook/my_use_case.md
   ```

   **Add a card to `docs/cookbook/index.md`** in the cookbook grid — copy an existing card and update the href, title, description, and `data-tags`. Available tags: `beginner`, `intermediate`, `advanced`, `genai`, `ml`, `cdshooks`, `fhir-gateway`, `interop`, `zero-setup`.

Use `healthchain seed medplum` to set up local test data — see the [sandbox docs](https://healthchainai.github.io/HealthChain/reference/utilities/sandbox/) and [CLI reference](https://healthchainai.github.io/HealthChain/cli/) for setup.

## 💻 Writing code

Check [`help wanted`](https://github.com/healthchainai/HealthChain/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) for issues open for external contribution. Only issues with this label are actively looking for contributors — comment before starting.

You can contribute code by:

- **Fixing bugs**: Pick issues labelled [`Issue: Bug 🐛`](https://github.com/healthchainai/HealthChain/issues?q=is%3Aissue+is%3Aopen+label%3A%22Issue%3A+Bug+%F0%9F%90%9B%22) and reference the issue number in your PR.
- **Implementing features**: Only pick up issues labelled `help wanted`. Comment on the issue with your approach before opening a PR.
- **Improving tests**: Increase coverage, add regression tests for fixed bugs.

For anything touching `core`, `Stage: Research 🔬`, or `Stage: Design 🎨` labelled issues — these require maintainer alignment before implementation. Comment on the issue or open a [Discussion](https://github.com/healthchainai/HealthChain/discussions) first.

## ⚙️ How to contribute code

This project uses `uv` for dependency management. See the [uv documentation](https://docs.astral.sh/uv/) for more information.

1. [Fork the repository](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) to your own GitHub account.
2. Clone your fork locally.
3. Run `uv sync --all-extras --dev` to install all development dependencies.
4. Run `uv run pytest` to ensure tests pass.
5. Create a new branch for your change:
   ```shell
   git checkout -b my-feature-branch
   ```
6. Install pre‑commit hooks:
   ```shell
   pre-commit install
   ```
7. Make your changes and commit with descriptive messages.
8. Push your changes and open a pull request on the main repository.

## 🧪 Testing

All new functionality must include tests, and all existing tests must pass.

- Add or update unit/integration tests to cover your changes.
- Run `uv run pytest` before opening or updating a PR.
- If tests are flaky or slow, mention this in the PR.

## 🔍 Pull request expectations

- Use a clear, descriptive title and explain what the PR does and why.
- Link the related issue (e.g. `Closes #123`).
- Describe how you tested your changes and any known limitations.

## 💬 Community

For quick questions and community discussion, join our [Discord](https://discord.gg/UQC6uAepUz). For anything requiring a considered response — technical design, pilot discussions, partnerships — [GitHub Discussions](https://github.com/healthchainai/HealthChain/discussions) or [email](mailto:jenniferjiangkells@gmail.com?subject=HealthChain) will get a faster reply.
