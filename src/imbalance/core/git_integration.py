from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def git_commit_after_flush(repo_root: Path, message: str) -> bool:
	if not os.getenv('IMBALANCE_GIT_COMMIT'):
		return False
	try:
		subprocess.run(
			['git', 'add', '-A'], cwd=repo_root, check=True, capture_output=True,
		)
		subprocess.run(
			['git', 'commit', '-m', message, '--allow-empty'],
			cwd=repo_root,
			check=True,
			capture_output=True,
		)
		logger.info('Git commit: %s', message)
		return True
	except FileNotFoundError:
		logger.debug('git not found, skipping commit')
		return False
	except subprocess.CalledProcessError as exc:
		logger.warning('git commit failed: %s', exc.stderr.decode() if exc.stderr else exc)
		return False
