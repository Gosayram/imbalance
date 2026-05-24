from __future__ import annotations

SKIP_DIRS = frozenset({
	'.git',
	'__pycache__',
	'node_modules',
	'.venv',
	'venv',
	'dist',
	'build',
	'.tox',
	'.eggs',
	'*.egg-info',
})

SOURCE_EXTS = frozenset({
	'.py',
	'.pyi',
	'.pyx',
	'.ts',
	'.tsx',
	'.js',
	'.jsx',
	'.go',
	'.rs',
	'.java',
	'.c',
	'.cpp',
	'.h',
	'.hpp',
})

_EXT_TO_LANG = {
	'.py': 'python',
	'.pyi': 'python',
	'.pyx': 'python',
	'.ts': 'typescript',
	'.tsx': 'typescript',
	'.js': 'javascript',
	'.jsx': 'javascript',
	'.go': 'go',
	'.rs': 'rust',
	'.java': 'java',
	'.c': 'c',
	'.cpp': 'cpp',
	'.h': 'c',
	'.hpp': 'cpp',
}