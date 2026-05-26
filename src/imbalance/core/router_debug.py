from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

FIXTURE_DIR = Path(__file__).parent.parent.parent.parent / 'tests' / 'fixtures' / 'responses'


class FakeLLMRouter:
    """
    Activated via IMBALANCE_MOCK_LLM=1.
    Returns fixture responses from tests/fixtures/responses/.
    Logs all prompts to /tmp/imbalance-prompts/ for inspection.
    """

    def __init__(self) -> None:
        self._prompt_dir = Path('/tmp/imbalance-prompts')
        self._prompt_dir.mkdir(exist_ok=True)
        self._call_count = 0

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 600,
        model: str | None = None,
    ) -> str:
        self._call_count += 1

        # Save prompt for debugging
        prompt_file = self._prompt_dir / f'{int(time.time())}_{self._call_count}.txt'
        prompt_file.write_text(prompt, encoding='utf-8')
        logger.debug(f'Saved prompt to {prompt_file}')

        # Try to return fixture response
        fixture = FIXTURE_DIR / 'flush_delta.json'
        if fixture.exists():
            return fixture.read_text(encoding='utf-8')

        # Fallback: minimal valid response
        return json.dumps({
            'decisions': [],
            'facts': [{'content': f'[FAKE] prompt was {len(prompt)} chars', 'tags': ['debug']}],
            'issues': [],
            'next_steps': ['[FAKE] next step'],
            'current_focus': '[FAKE] development mode',
        })

    def reset(self) -> None:
        """Reset call count for testing."""
        self._call_count = 0


def create_fake_router() -> FakeLLMRouter | None:
    """Create FakeLLMRouter if IMBALANCE_MOCK_LLM=1, else None."""
    if os.environ.get('IMBALANCE_MOCK_LLM', '').strip() in ('1', 'true', 'yes'):
        logger.info('Using FakeLLMRouter (IMBALANCE_MOCK_LLM=1)')
        return FakeLLMRouter()
    return None
