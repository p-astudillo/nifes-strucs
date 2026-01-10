"""
PAZ Application Entry Point.

This module allows running PAZ as a module: python -m paz

Usage:
    python -m paz          # Run desktop GUI (default)
    python -m paz --gui    # Run desktop GUI
    python -m paz --api    # Run API server only
"""

import sys


def main() -> int:
    """Main entry point for PAZ application."""
    args = sys.argv[1:]

    # Check for API mode
    if "--api" in args:
        from paz.app import run_app
        return run_app()

    # Default: run desktop GUI
    from paz.presentation.main_window import run_main_window
    return run_main_window()


if __name__ == "__main__":
    sys.exit(main())
