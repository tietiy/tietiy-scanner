# scanner/telegram_poll_runner.py
# Standalone runner for Telegram command polling.
# Called by telegram_poll.yml every 30 minutes.
# Loads meta + history + ltp_prices from output/
# then calls poll_and_respond().
# ─────────────────────────────────────────────────────

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(
    os.path.dirname(__file__)))

from telegram_bot import poll_and_respond

_ROOT   = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
_OUTPUT = os.path.join(_ROOT, 'output')


def _load(filename):
    path = os.path.join(_OUTPUT, filename)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f'[poll_runner] Cannot load '
              f'{filename}: {e}')
        return {}


def main():
    print('[poll_runner] Starting...')

    meta       = _load('meta.json')
    ltp_prices = _load('ltp_prices.json')

    history_data = _load('signal_history.json')
    history      = history_data.get('history', []) \
                   if history_data else []

    if not meta:
        print('[poll_runner] No meta.json — '
              'bot will respond with limited data')

    count = poll_and_respond(
        meta        = meta,
        history     = history,
        ltp_prices  = ltp_prices,
        window_minutes = 35,
    )

    print(f'[poll_runner] Done — '
          f'{count} commands processed')


if __name__ == '__main__':
    main()
