from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def compress_context(text: str, target_tokens: int) -> str:
	try:
		from llmlingua import PromptCompressor

		compressor = PromptCompressor()
		result = compressor.compress_prompt(text, target_token=target_tokens)
		compressed = result.get('compressed_prompt', text)
		logger.info('Compressed %d → %d tokens', len(text.split()), len(compressed.split()))
		return compressed
	except ImportError:
		logger.debug('llmlingua not installed, using truncation')
		return _truncate(text, target_tokens)
	except Exception as exc:
		logger.warning('Compression failed: %s, using truncation', exc)
		return _truncate(text, target_tokens)


def _truncate(text: str, target_tokens: int) -> str:
	words = text.split()
	if len(words) <= target_tokens:
		return text
	return ' '.join(words[:target_tokens])
