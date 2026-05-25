from __future__ import annotations

TEMPLATES = {
	'python-backend': """\
# {project} — AI Context

## Memory
- Use `imbalance save-fact` for decisions, patterns, and constraints.
- Scope hints: `decisions`, `stack`, `patterns`, `constraints`
- Use `imbalance get-context` before starting work to load project context.

## Workflow
1. Check context: `imbalance get-context "current task"`
2. Make changes
3. Save key decisions: `imbalance save-fact "decision content" --section decisions --tags auth,db`
4. Report usage: `imbalance report-context-usage` periodically

## Conventions
- Python {python_version}+, type hints required
- Tests: pytest with fixtures
- Lint: ruff check
""",
	'frontend-react': """\
# {project} — AI Context

## Memory
- Use `imbalance save-fact` for component patterns, design decisions, API contracts.
- Scope hints: `decisions`, `patterns`, `api`, `design`
- Frontend state patterns go in `patterns/` section.

## Workflow
1. Check context: `imbalance get-context "component name"`
2. Build components following existing patterns
3. Save API contract changes: `imbalance save-fact "..." --section api`
4. Report usage: `imbalance report-context-usage`

## Conventions
- React with TypeScript
- Component file naming: PascalCase
- State management: check `patterns/` for project-specific approach
""",
	'devops': """\
# {project} — AI Context

## Memory
- Use `imbalance save-fact` for infra decisions, runbooks, incident logs.
- Scope hints: `decisions`, `infra`, `incidents`, `runbooks`
- Document all config changes in `decisions/` section.

## Workflow
1. Check context: `imbalance get-context "service name"`
2. Make infra changes
3. Log changes: `imbalance save-fact "..." --section infra --tags deploy,scaling`
4. After incidents: `imbalance save-fact "..." --section incidents`

## Conventions
- Infrastructure as Code (Terraform/Pulumi)
- All secrets via vault/env, never in config files
- Document runbooks in `runbooks/` section
""",
	'data-science': """\
# {project} — AI Context

## Memory
- Use `imbalance save-fact` for experiment results, model decisions, data schemas.
- Scope hints: `decisions`, `experiments`, `data`, `models`
- Report context usage frequently (long notebooks).

## Workflow
1. Check context: `imbalance get-context "experiment name"`
2. Run experiments
3. Log results: `imbalance save-fact "..." --section experiments --tags model,v2`
4. Report usage: `imbalance report-context-usage` every 30 minutes

## Conventions
- Notebooks for exploration, scripts for production
- Track model versions in `models/` section
- Data schema changes go in `data/` section
""",
}

# Universal AGENTS.md content
AGENTS_MD_CONTENT = """\
# {project} — AI Context for Agents

## Memory Protocol
At session start: call `get_context` with task description.
After each decision: call `save_fact` immediately.
At session end: call `flush_session`.
Token budget: 2000.

## Workflow
1. `imbalance get-context "current task"` — load relevant context
2. Make changes to codebase
3. `imbalance save-fact "decision content" --section decisions --tags auth` — record key decisions
4. `imbalance report-context-usage` — monitor token budget

## Sections Available
- `decisions/` — architecture, tech choices
- `stack/` — frameworks, versions, dependencies
- `patterns/` — code patterns, conventions
- `constraints/` — limitations, requirements
- `context/` — general project state
"""


# Agent-specific generators
def generate_agents_md(project_name: str) -> str:
	"""Generate AGENTS.md content (cross-agent standard)."""
	return AGENTS_MD_CONTENT.format(project=project_name)


def generate_claude_md(template: str, project_name: str = 'Project') -> str:
	import sys

	if template not in TEMPLATES:
		available = ', '.join(TEMPLATES.keys())
		raise ValueError(f'Unknown template: {template}. Available: {available}')
	python_version = f'{sys.version_info.major}.{sys.version_info.minor}'
	return TEMPLATES[template].format(project=project_name, python_version=python_version)


def generate_cursor_mdc(project_name: str) -> str:
	"""Generate .cursor/rules/imbalance.mdc content."""
	return f"""---
description: imbalance knowledge base integration for {project_name}
alwaysApply: true
---

# imbalance KB

At session start: call `get_context` with current task.
After each significant decision: `save_fact`.
At session end: `flush_session`.

MCP server: running at http://localhost:4731/mcp/sse
Project: auto-detected from cwd.
"""


def generate_gemini_md(project_name: str) -> str:
	"""Generate GEMINI.md content."""
	return AGENTS_MD_CONTENT.format(project=project_name)


def generate_copilot_section(project_name: str) -> str:
	"""Generate copilot instructions section."""
	return """<!-- imbalance -->
# imbalance KB Integration

At session start: `imbalance get-context "task"`
After decisions: `imbalance save-fact "content" --section decisions`
At session end: `imbalance flush-session`
<!-- /imbalance -->
"""
