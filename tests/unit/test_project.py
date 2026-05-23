from pathlib import Path

from imbalance.core.project import find_project_config


def test_find_project_config_in_current_dir(tmp_path: Path) -> None:
	(tmp_path / "imbalance.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

	assert find_project_config(tmp_path) == tmp_path / "imbalance.toml"


def test_find_project_config_walks_up(tmp_path: Path) -> None:
	(tmp_path / "imbalance.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
	deep = tmp_path / "src" / "imbalance" / "core"
	deep.mkdir(parents=True)

	assert find_project_config(deep) == tmp_path / "imbalance.toml"


def test_find_project_config_prefers_nearest(tmp_path: Path) -> None:
	(tmp_path / "imbalance.toml").write_text("[project]\nname='root'\n", encoding="utf-8")
	service = tmp_path / "services" / "auth"
	service.mkdir(parents=True)
	(service / "imbalance.toml").write_text("[project]\nname='auth'\n", encoding="utf-8")

	assert find_project_config(service) == service / "imbalance.toml"
