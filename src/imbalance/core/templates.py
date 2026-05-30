from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionTemplate:
	"""Template for wiki sections."""
	section: str
	title: str
	fields: list[str]
	description: str


ADR_TEMPLATE = SectionTemplate(
	section='decisions',
	title='Architecture Decision Record',
	fields=[
		'title: Decision title',
		'rationale: Why this decision was made',
		'alternatives: Other options considered',
		'consequences: Impact of this decision',
	],
	description='Use for architectural decisions that affect the project.',
)

ISSUES_TEMPLATE = SectionTemplate(
	section='issues',
	title='Known Issue / Bug',
	fields=[
		'symptom: What goes wrong',
		'root_cause: Why it happens',
		'workaround: Temporary fix',
		'fix_ref: Link to permanent fix (PR/commit)',
	],
	description='Use for known bugs, workarounds, and their resolutions.',
)

STACK_TEMPLATE = SectionTemplate(
	section='stack',
	title='Technology Stack',
	fields=[
		'language: Primary language',
		'framework: Main framework',
		'database: Database system',
		'infra: Infrastructure tools',
	],
	description='Use for documenting the technology stack.',
)

CONTEXT_TEMPLATE = SectionTemplate(
	section='context',
	title='Current Context',
	fields=[
		'focus: Current focus area',
		'blockers: Current blockers',
		'next: What to do next',
	],
	description='Use for current sprint/task context.',
)


TEMPLATES: dict[str, SectionTemplate] = {
	'adr': ADR_TEMPLATE,
	'decision': ADR_TEMPLATE,
	'issue': ISSUES_TEMPLATE,
	'bug': ISSUES_TEMPLATE,
	'stack': STACK_TEMPLATE,
	'context': CONTEXT_TEMPLATE,
}


def get_template(name: str) -> SectionTemplate | None:
	"""Get template by name."""
	return TEMPLATES.get(name.lower())


def render_template(template: SectionTemplate, **kwargs: str) -> str:
	"""Render a template with provided values."""
	lines = [f'# {template.title}', '']
	for field in template.fields:
		field_name = field.split(':')[0]
		value = kwargs.get(field_name, '')
		if value:
			lines.append(f'**{field_name}:** {value}')
		else:
			lines.append(f'**{field_name}:** _TODO_')
	lines.append('')
	lines.append(f'> {template.description}')
	return '\n'.join(lines)


# Agent file generator functions

CLAUDE_MD_TEMPLATES = {
	'python-backend': '''# {project_name} — Claude Code Instructions

## imbalance KB

Session start: /imbalance-load
Decisions: save_fact() immediately
Session end: /imbalance-flush
Context budget: 2000 tokens

## Python Backend

- Use FastAPI for API endpoints
- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for public methods
''',
	'frontend-react': '''# {project_name} — Claude Code Instructions

## imbalance KB

Session start: /imbalance-load
Decisions: save_fact() immediately
Session end: /imbalance-flush
Context budget: 2000 tokens

## Frontend React

- Use functional components with hooks
- Follow React best practices
- Use TypeScript for type safety
- Write unit tests for components
''',
	'devops': '''# {project_name} — Claude Code Instructions

## imbalance KB

Session start: /imbalance-load
Decisions: save_fact() immediately
Session end: /imbalance-flush
Context budget: 2000 tokens

## DevOps

- Use Terraform for infrastructure
- Follow GitOps practices
- Use Docker for containerization
- Implement CI/CD pipelines
''',
	'data-science': '''# {project_name} — Claude Code Instructions

## imbalance KB

Session start: /imbalance-load
Decisions: save_fact() immediately
Session end: /imbalance-flush
Context budget: 2000 tokens

## Data Science

- Use Jupyter notebooks for exploration
- Follow data versioning practices
- Use MLflow for experiment tracking
- Document model assumptions
''',
}


def generate_claude_md(template: str, project_name: str) -> str:
	"""Generate CLAUDE.md content from template."""
	if template not in CLAUDE_MD_TEMPLATES:
		raise ValueError(f'Unknown template: {template}. Available: {", ".join(CLAUDE_MD_TEMPLATES.keys())}')
	return CLAUDE_MD_TEMPLATES[template].format(project_name=project_name)


def generate_agents_md(project_name: str) -> str:
	"""Generate AGENTS.md content."""
	return f'''# {project_name} — Agent Instructions

## Memory Protocol

1. **Session start**: Call `get_context` with current task
2. **During work**: Call `save_fact` for key decisions
3. **Session end**: Call `flush_session` to persist

## MCP Tools

- `get_context(query, budget_tokens)` — Load relevant context
- `save_fact(content, section, tags)` — Save knowledge
- `flush_session(summary, decisions, next_steps)` — End session
- `get_status()` — Check KB status

## Budget

Default: 2000 tokens per context load.
Use scope filters to narrow results.
'''


def generate_cursor_mdc(project_name: str) -> str:
	"""Generate .cursor/rules/imbalance.mdc content."""
	return f'''---
description: imbalance knowledge base integration
alwaysApply: true
---

# {project_name} — Cursor Rules

## MCP server

Server running at http://localhost:4731/mcp/sse

## Memory Protocol

1. **Session start**: Call `get_context` with current task
2. **During work**: Call `save_fact` for key decisions
3. **Session end**: Call `flush_session` to persist

## Context Budget

Default: 2000 tokens per context load.
'''


def generate_gemini_md(project_name: str) -> str:
	"""Generate GEMINI.md content."""
	return f'''# {project_name} — Gemini CLI Instructions

## Memory Protocol

1. **Session start**: Call `get_context` with current task
2. **During work**: Call `save_fact` for key decisions
3. **Session end**: Call `flush_session` to persist

## MCP Tools

- `get_context(query, budget_tokens)` — Load relevant context
- `save_fact(content, section, tags)` — Save knowledge
- `flush_session(summary, decisions, next_steps)` — End session

## Budget

Default: 2000 tokens per context load.
'''


def generate_copilot_section(project_name: str) -> str:
	"""Generate .github/copilot-instructions.md section."""
	return f'''## imbalance KB — {project_name}

### get-context

Call `get_context` MCP tool with current task description.
Budget: 2000 tokens.

### save-fact

Call `save_fact` MCP tool after key decisions.
Sections: decisions, context, stack, issues.

### flush-session

Call `flush_session` MCP tool at session end.
Include summary, decisions, and next steps.
'''
