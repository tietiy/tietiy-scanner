"""Brain CLI — Tier 1 command surface (status / rules / explain / trace).

See doc/brain_design_v1.md §7 for command spec.
Step 2 stub: argparse skeleton wired; subcommands return placeholder text.

Usage: python -m scanner.brain.brain_cli <subcommand>
"""
import argparse
import sys


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(prog='brain')
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status', help='derived-view summary (Tier 1)')
    sub.add_parser('rules', help='show active rules (Tier 1)')
    sub.add_parser('explain', help='explain a proposal (Tier 1)')
    sub.add_parser('trace', help='reasoning trace for a proposal (Tier 1)')

    args = parser.parse_args(argv)
    print(f'[brain {args.cmd}] not yet implemented')
    return 0


if __name__ == '__main__':
    sys.exit(main())
