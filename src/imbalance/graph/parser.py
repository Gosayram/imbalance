from __future__ import annotations

import ast
import re

from imbalance.graph._constants import _EXT_TO_LANG
from imbalance.graph.models import Symbol

_PATTERN_CACHE: dict[str, list[tuple[str, re.Pattern]]] = {}


def _get_patterns(language: str) -> list[tuple[str, re.Pattern]]:
	if language in _PATTERN_CACHE:
		return _PATTERN_CACHE[language]

	if language == 'python':
		_PATTERN_CACHE[language] = [
			('function', re.compile(r'^\s*def\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)),
			('class', re.compile(r'^\s*class\s+(\w+)', re.MULTILINE)),
			('async_function', re.compile(r'^\s*async\s+def\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)),
		]
	elif language == 'typescript':
		_PATTERN_CACHE[language] = [
			('function', re.compile(r'^\s*function\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)),
			('class', re.compile(r'^\s*class\s+(\w+)', re.MULTILINE)),
			('interface', re.compile(r'^\s*interface\s+(\w+)', re.MULTILINE)),
			('method', re.compile(r'^\s*(\w+)\s*\(([^)]*)\)\s*:', re.MULTILINE)),
		]
	elif language == 'javascript':
		_PATTERN_CACHE[language] = [
			('function', re.compile(r'^\s*function\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)),
			('class', re.compile(r'^\s*class\s+(\w+)', re.MULTILINE)),
			('method', re.compile(r'^\s*(\w+)\s*\(([^)]*)\)\s*:', re.MULTILINE)),
			(
				'arrow',
				re.compile(r'^\s*(?:const|let|var)\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>', re.MULTILINE),
			),
		]
	elif language == 'go':
		_PATTERN_CACHE[language] = [
			('function', re.compile(r'^\s*func\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)),
			(
				'method',
				re.compile(
					r'^\s*func\s+\(([^)]+\s*\*?\s*(\w+))\)(\s*(\w+))?\s*\(([^)]*)\)', re.MULTILINE
				),
			),
			('type', re.compile(r'^\s*type\s+(\w+)\s+(?:struct|interface)', re.MULTILINE)),
		]
	else:
		_PATTERN_CACHE[language] = []

	return _PATTERN_CACHE[language]


class PythonASTParser:
	def parse(self, source: bytes, file_path: str) -> tuple[Symbol, ...]:
		try:
			tree = ast.parse(source)
		except SyntaxError:
			return ()

		symbols: list[Symbol] = []
		for node in ast.walk(tree):
			if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
				name = node.name
				args = [a.arg for a in node.args.args]
				signature = f'def {name}({", ".join(args)})'
				symbols.append(
					Symbol(
						name=name,
						kind='async_function'
						if isinstance(node, ast.AsyncFunctionDef)
						else 'function',
						file_path=file_path,
						line=node.lineno or 1,
						end_line=node.end_lineno or node.lineno or 1,
						signature=signature,
						language='python',
					)
				)
			elif isinstance(node, ast.ClassDef):
				symbols.append(
					Symbol(
						name=node.name,
						kind='class',
						file_path=file_path,
						line=node.lineno or 1,
						end_line=node.end_lineno or node.lineno or 1,
						signature=f'class {node.name}',
						language='python',
					)
				)
		return tuple(symbols)


class CompiledPatternParser:
	def parse(self, source: bytes, file_path: str, language: str) -> tuple[Symbol, ...]:
		try:
			src = source.decode('utf-8')
		except UnicodeDecodeError:
			return ()

		symbols: list[Symbol] = []
		for kind, pattern in _get_patterns(language):
			for match in pattern.finditer(src):
				name = match.group(1)
				symbols.append(
					Symbol(
						name=name,
						kind=kind,
						file_path=file_path,
						line=src[: match.start()].count('\n') + 1,
						end_line=src[: match.end()].count('\n') + 1,
						signature=match.group(0).strip(),
						language=language,
					)
				)
		return tuple(symbols)


class FileParser:
	def __init__(self) -> None:
		self._ast_parser = PythonASTParser()
		self._pattern_parser = CompiledPatternParser()

	def parse(self, file_path: str) -> tuple[Symbol, ...]:
		from pathlib import Path

		p = Path(file_path)
		ext = p.suffix.lower()
		language = _EXT_TO_LANG.get(ext, 'unknown')

		try:
			source = p.read_bytes()
		except OSError:
			return ()

		if language == 'python':
			result = self._ast_parser.parse(source, file_path)
			if result:
				return result

		if language in ('typescript', 'javascript', 'go'):
			return self._pattern_parser.parse(source, file_path, language)

		return ()
