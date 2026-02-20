"""
String similarity utilities for command suggestions.
Uses difflib from Python standard library - zero additional dependencies.

This module provides fuzzy string matching to help users recover from typos
when entering CLI commands, similar to modern CLI tools like slack, brew, gh, etc.
"""

import difflib
from typing import List, Optional


def find_similar_command(invalid: str, valid_choices: List[str], cutoff: float = 0.6) -> Optional[str]:
    """
    Find the most similar valid command to an invalid input.

    Uses the Ratcliff/Obershelp algorithm (via difflib.get_close_matches) to find
    the best match. This is the same algorithm used by many modern CLI tools.

    Args:
        invalid: The invalid command entered by user
        valid_choices: List of valid command names
        cutoff: Minimum similarity ratio (0.0 to 1.0), default 0.6
                Higher values require closer matches

    Returns:
        Most similar command if similarity >= cutoff, else None

    Examples:
        >>> find_similar_command('stat', ['status', 'start', 'stop'])
        'status'
        >>> find_similar_command('lst', ['list', 'last', 'lost'])
        'list'
        >>> find_similar_command('xyz', ['status', 'start', 'stop'])
        None
    """
    matches = difflib.get_close_matches(invalid, valid_choices, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def find_multiple_suggestions(invalid: str, valid_choices: List[str], n: int = 3, cutoff: float = 0.6) -> List[str]:
    """
    Find multiple similar commands for suggestions.

    Useful when you want to show the user several possible corrections,
    not just the single best match.

    Args:
        invalid: The invalid command entered by user
        valid_choices: List of valid command names
        n: Maximum number of suggestions to return
        cutoff: Minimum similarity ratio (0.0 to 1.0)

    Returns:
        List of similar commands (up to n items), sorted by similarity

    Examples:
        >>> find_multiple_suggestions('sta', ['status', 'start', 'stop', 'stack'])
        ['start', 'status', 'stack']
        >>> find_multiple_suggestions('s', ['status', 'start'], n=1)
        ['status']  # or ['start'], depending on which scores higher
    """
    return difflib.get_close_matches(invalid, valid_choices, n=n, cutoff=cutoff)
