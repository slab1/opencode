#!/usr/bin/env python3
"""CLI entry point for opencode_improvement.

Usage:
    python3 -m opencode_improvement audit
    python3 -m opencode_improvement report [--agent NAME] [--last-n 50]
    python3 -m opencode_improvement analyze --agent NAME
    python3 -m opencode_improvement suggest --agent NAME
"""
from opencode_improvement import main
main()
