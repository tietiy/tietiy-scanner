# .github/workflows/wave5_m08.yml
# Purpose: Run scripts/wave5_m08_migration.py with manual
#          trigger. Two modes: dry_run / execute.
#
# Kills fix-table item M-08 — consolidate _esc across
# 4 files (gap_report, heartbeat, deep_debugger,
# diagnostic) into canonical import from telegram_bot.
#
# Follows the same pattern as wave2.yml:
#   - workflow_dispatch only (no schedule)
#   - auto-commit on success
#   - Telegram notification
#   - Rollback on any syntax failure

name: "🔧 Wave 5.1 | M-08 _esc consolidation | Manual"

on:
  workflow_dispatch:
    inputs:
      mode:
        description: 'Run mode'
        required: true
        default: 'dry_run'
        type: choice
        options:
          - dry_run
          - execute

jobs:
  wave5_m08:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GH_TOKEN }}
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Show mode
        run: |
          echo "═══════════════════════════════════════════"
          echo "WAVE 5.1 M-08 — mode: ${{ inputs.mode }}"
          echo "═══════════════════════════════════════════"

      - name: Run migration script
        id: migrate
        env:
          PYTHONPATH: ${{ github.workspace }}:${{ github.workspace }}/scanner
        run: |
          if [ "${{ inputs.mode }}" = "dry_run" ]; then
            python scripts/wave5_m08_migration.py --dry-run --json
          else
            python scripts/wave5_m08_migration.py --execute --json
          fi

      - name: Commit changes (execute mode only)
        if: inputs.mode == 'execute' && success()
        env:
          GITHUB_TOKEN: ${{ secrets.GH_TOKEN }}
        run: |
          git config user.name  "TIE TIY Bot"
          git config user.email "bot@tietiy.com"

          git add scanner/ doc/ quarantine/ || true

          if git diff --cached --quiet; then
            echo "No changes to commit — migration was a no-op"
            exit 0
          fi

          COMMIT_MSG="Wave 5.1: Consolidate _esc helpers (M-08)

          Automated migration via scripts/wave5_m08_migration.py:
          - _esc deleted from 4 files (gap_report, heartbeat,
            deep_debugger, diagnostic)
          - Replaced with canonical 'from telegram_bot import _esc'
          - Full backup in quarantine/wave5_<timestamp>/
          - Audit log in doc/wave5_m08_log_<timestamp>.md"

          git commit -m "$COMMIT_MSG"

          for i in 1 2 3; do
            git pull --rebase origin main && \
            git push origin HEAD:main && \
            echo "Push succeeded on attempt $i" && \
            break
            echo "Push attempt $i failed — retrying in 10s..."
            sleep 10
          done

      - name: Telegram notification
        if: always()
        env:
          TELEGRAM_TOKEN:   ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          MODE="${{ inputs.mode }}"
          OUTCOME="${{ steps.migrate.outcome }}"

          if [ "$OUTCOME" = "success" ]; then
            if [ "$MODE" = "dry_run" ]; then
              MSG="🔍 Wave 5.1 DRY RUN complete%0A%0ACheck logs for planned changes.%0AIf approved, re-run with mode=execute."
            else
              MSG="✅ Wave 5.1 EXECUTE complete%0A%0A_esc consolidated.%0AM-08 killed.%0ARun Master Check to confirm green."
            fi
          else
            MSG="❌ Wave 5.1 ${MODE} FAILED%0A%0ACheck Actions logs.%0AIf execute mode: files rolled back automatically.%0ABackup preserved in quarantine/."
          fi

          curl -s -X POST \
            "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${MSG}" || true
