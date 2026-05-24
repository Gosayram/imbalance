from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

CONFIG_FILE = 'imbalance.toml'


@dataclass(frozen=True)
class InheritConfig:
	kb_name: str
	weight: float = 0.5


@dataclass(frozen=True)
class NotificationConfig:
	enabled: bool = True
	queue_size_threshold: int = 5
	kb_stale_days: int = 14
	circuit_breaker_open: bool = True


@dataclass(frozen=True)
class ProjectConfig:
	name: str
	version: str
	store: str | None = None
	store_path: Path | None = None
	budget_tokens: int = 2000
	cache_ttl_sec: int = 1800
	dedup_threshold: float = 0.92
	max_graph_hops: int = 1
	max_related: int = 5
	confidence_weight: float = 0.05
	conflict_mode: str = 'warn'
	inherit: InheritConfig | None = None
	notifications: NotificationConfig = NotificationConfig()


@dataclass(frozen=True)
class Project:
	root: Path
	config_path: Path
	config: ProjectConfig
	data_dir: Path

	@property
	def name(self) -> str:
		return self.config.name

	@property
	def kb_dir(self) -> Path:
		if self.config.store_path is not None:
			return self.config.store_path
		store_name = self.config.store or self.config.name
		return self.data_dir / 'kb' / store_name

	@property
	def db_path(self) -> Path:
		return self.kb_dir / 'kb.db'

	@classmethod
	def from_toml(cls, path: Path, data_dir: Path | None = None) -> Project:
		raw = tomllib.loads(path.read_text(encoding='utf-8'))
		project = raw.get('project', {})
		kb = raw.get('kb', {})
		retrieval = raw.get('retrieval', {})
		quality = retrieval.get('quality', {})
		kb_inherit = kb.get('inherit', {})
		notifications = raw.get('notifications', {})

		name = project.get('name')
		if not name:
			raise ValueError(f'{path} must define [project].name')

		inherit = None
		if kb_inherit and 'from' in kb_inherit:
			inherit = InheritConfig(
				kb_name=str(kb_inherit['from']),
				weight=float(kb_inherit.get('weight', 0.5)),
			)

		store_path = os.getenv('IMBALANCE_KB_PATH') or kb.get('store_path')
		notif = NotificationConfig(
			enabled=bool(notifications.get('enabled', True)),
			queue_size_threshold=int(notifications.get('queue_size_threshold', 5)),
			kb_stale_days=int(notifications.get('kb_stale_days', 14)),
			circuit_breaker_open=bool(notifications.get('circuit_breaker_open', True)),
		)
		config = ProjectConfig(
			name=name,
			version=str(project.get('version', '1')),
			store=kb.get('store'),
			store_path=Path(store_path).expanduser() if store_path else None,
			budget_tokens=int(retrieval.get('budget_tokens', 2000)),
			cache_ttl_sec=int(retrieval.get('cache_ttl_sec', 1800)),
			dedup_threshold=float(quality.get('dedup_threshold', 0.92)),
			max_graph_hops=int(quality.get('max_graph_hops', 1)),
			max_related=int(quality.get('max_related', 5)),
			confidence_weight=float(quality.get('confidence_weight', 0.05)),
			conflict_mode=str(quality.get('conflict_mode', 'warn')),
			inherit=inherit,
			notifications=notif,
		)
		return cls(
			root=path.parent,
			config_path=path,
			config=config,
			data_dir=data_dir or default_data_dir(),
		)


def default_data_dir() -> Path:
	if override := os.getenv('IMBALANCE_DATA_DIR'):
		return Path(override).expanduser()
	return Path(user_data_dir('imbalance')).expanduser()


def find_project_config(start: Path | None = None) -> Path | None:
	current = (start or Path.cwd()).resolve()
	for parent in [current, *current.parents]:
		candidate = parent / CONFIG_FILE
		if candidate.exists():
			return candidate
	return None


def load_project(start: Path | None = None) -> Project:
	config_path = find_project_config(start)
	if config_path is None:
		global_config = Path(user_config_dir('imbalance')) / CONFIG_FILE
		if not global_config.exists():
			raise FileNotFoundError(
				f'Could not find {CONFIG_FILE} above {start or Path.cwd()} '
				f'or fallback config at {global_config}'
			)
		config_path = global_config
	return Project.from_toml(config_path)
