"""
Terminal User Interface for tt-cli
Optional - requires textual and rich
"""

def main():
    """Launch TUI interface."""
    try:
        from textual.app import App
    except ImportError:
        print()
        print("TUI dependencies not installed")
        print()
        print("Install with:")
        print("  pip install 'tt-cli[tui]'")
        print()
        print("Or manually:")
        print("  pip install textual rich")
        print()
        return 1

    print()
    print("⚠️  TUI not yet implemented")
    print()
    print("The TUI will provide an interactive interface for:")
    print("  • Hardware status monitoring")
    print("  • Model browsing and selection")
    print("  • Server management")
    print("  • Environment switching")
    print()
    print("Coming in Phase 2!")
    print()

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
