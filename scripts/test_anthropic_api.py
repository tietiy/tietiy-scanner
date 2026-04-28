"""B-3 prereq: minimal Anthropic Messages API test call.

Purpose: verify ANTHROPIC_API_KEY + SDK install + opus-4-7 model id
are all working before Brain Step 5 (brain_reason.py) wires real
gates. This file documents the exact SDK init + call pattern that
Step 5 will copy.

Usage: .venv/bin/python scripts/test_anthropic_api.py
       (loads ANTHROPIC_API_KEY from .env via python-dotenv)
Exit 0 on success ("pong" returned); exit 1 otherwise with diagnostic.
"""
import os
import sys

MODEL  = 'claude-opus-4-7'
PROMPT = "Reply with the single word 'pong' and nothing else."


def main():
    try:
        from dotenv import load_dotenv
    except ImportError:
        print('[test_anthropic] python-dotenv not installed.')
        print('[test_anthropic] Run: .venv/bin/pip install python-dotenv')
        return 1

    load_dotenv()

    key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not key:
        print('[test_anthropic] ANTHROPIC_API_KEY not set.')
        print('[test_anthropic] Add to .env at repo root or shell env. Aborting.')
        return 1

    try:
        from anthropic import Anthropic
    except ImportError:
        print('[test_anthropic] anthropic SDK not installed.')
        print('[test_anthropic] Run: .venv/bin/pip install anthropic')
        return 1

    client = Anthropic()
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=10,
            messages=[{'role': 'user', 'content': PROMPT}],
        )
    except Exception as e:
        print(f'[test_anthropic] API call failed: '
              f'{type(e).__name__}: {e}')
        return 1

    text = msg.content[0].text.strip() if msg.content else ''
    print(f'[test_anthropic] model={msg.model} '
          f'in={msg.usage.input_tokens} '
          f'out={msg.usage.output_tokens} '
          f'stop={msg.stop_reason}')
    print(f'[test_anthropic] response: {text!r}')

    if text.lower() == 'pong':
        print('[test_anthropic] PASS')
        return 0
    print(f'[test_anthropic] FAIL: expected "pong", got {text!r}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
