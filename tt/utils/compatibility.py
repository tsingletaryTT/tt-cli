"""
Environment compatibility checking for tt-cli.

This module checks whether the current environment (tt-metal, tt-vllm commits)
matches the requirements specified in model specifications. This helps users
understand when their environment may not match tested configurations.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_git_commit(repo_path: Path) -> Optional[str]:
    """
    Get current git commit hash for a repository.

    Args:
        repo_path: Path to git repository

    Returns:
        Short commit hash (7 chars), or None if not a git repo
    """
    if not repo_path.exists():
        return None

    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short=7', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode == 0:
            return result.stdout.strip()

        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_current_tt_metal_commit() -> Optional[str]:
    """
    Get current tt-metal commit.

    Looks for tt-metal in common locations:
    - ~/tt-metal
    - ~/code/tt-metal
    - $TT_METAL_HOME

    Returns:
        Short commit hash, or None if not found
    """
    import os

    # Try TT_METAL_HOME env var first
    if 'TT_METAL_HOME' in os.environ:
        metal_path = Path(os.environ['TT_METAL_HOME'])
        commit = get_git_commit(metal_path)
        if commit:
            return commit

    # Try common locations
    common_paths = [
        Path.home() / 'tt-metal',
        Path.home() / 'code' / 'tt-metal',
    ]

    for path in common_paths:
        commit = get_git_commit(path)
        if commit:
            return commit

    return None


def get_current_vllm_commit() -> Optional[str]:
    """
    Get current tt-vllm commit.

    Looks for tt-vllm in common locations:
    - ~/vllm
    - ~/tt-vllm
    - ~/code/vllm
    - ~/code/tt-vllm

    Returns:
        Short commit hash, or None if not found
    """
    common_paths = [
        Path.home() / 'vllm',
        Path.home() / 'tt-vllm',
        Path.home() / 'code' / 'vllm',
        Path.home() / 'code' / 'tt-vllm',
    ]

    for path in common_paths:
        commit = get_git_commit(path)
        if commit:
            return commit

    return None


def normalize_commit(commit: str) -> str:
    """
    Normalize commit hash for comparison.

    Handles:
    - Full hashes vs short hashes
    - Lowercase vs uppercase

    Args:
        commit: Commit hash (any length)

    Returns:
        Normalized commit (lowercase, 7 chars if possible)
    """
    if not commit:
        return ""

    # Take first 7 characters and lowercase
    return commit.lower().strip()[:7]


def commits_match(commit1: str, commit2: str) -> bool:
    """
    Check if two commit hashes match.

    Handles different hash lengths (short vs full).

    Args:
        commit1: First commit hash
        commit2: Second commit hash

    Returns:
        True if commits match (or either is None/empty)
    """
    if not commit1 or not commit2:
        return True  # Can't verify, assume okay

    # Normalize both commits
    c1 = normalize_commit(commit1)
    c2 = normalize_commit(commit2)

    # Compare
    return c1 == c2


def check_environment_compatibility(required_spec: Dict, verbose: bool = False) -> Dict:
    """
    Compare current environment against required spec.

    Checks:
    - tt-metal commit
    - tt-vllm commit

    Args:
        required_spec: Model specification with required commits
        verbose: If True, print detailed information

    Returns:
        Compatibility report dict with:
        - metal_match: bool
        - vllm_match: bool
        - metal_current: str
        - metal_required: str
        - vllm_current: str
        - vllm_required: str
        - warnings: List[str]
        - recommendations: List[str]
    """
    # Get current commits
    current_metal = get_current_tt_metal_commit()
    current_vllm = get_current_vllm_commit()

    # Get required commits from spec
    required_metal = required_spec.get('tt_metal_commit', '')
    required_vllm = required_spec.get('vllm_commit', '')

    # Check matches
    metal_match = commits_match(current_metal, required_metal)
    vllm_match = commits_match(current_vllm, required_vllm)

    # Build compatibility report
    warnings = []
    recommendations = []

    if not metal_match:
        warnings.append(
            f"tt-metal commit mismatch: current={current_metal or 'unknown'}, "
            f"required={normalize_commit(required_metal)}"
        )
        recommendations.append(
            f"Consider checking out tt-metal commit {normalize_commit(required_metal)}"
        )

    if not vllm_match:
        warnings.append(
            f"tt-vllm commit mismatch: current={current_vllm or 'unknown'}, "
            f"required={normalize_commit(required_vllm)}"
        )
        recommendations.append(
            f"Consider checking out tt-vllm commit {normalize_commit(required_vllm)}"
        )

    if verbose and warnings:
        print("\n⚠️  Environment compatibility warnings:")
        for warning in warnings:
            print(f"   {warning}")
        print("\n💡 Recommendations:")
        for rec in recommendations:
            print(f"   {rec}")

    return {
        'metal_match': metal_match,
        'vllm_match': vllm_match,
        'metal_current': current_metal or 'unknown',
        'metal_required': normalize_commit(required_metal),
        'vllm_current': current_vllm or 'unknown',
        'vllm_required': normalize_commit(required_vllm),
        'warnings': warnings,
        'recommendations': recommendations,
        'all_match': metal_match and vllm_match,
    }


def format_compatibility_report(compat: Dict) -> str:
    """
    Format compatibility report for display.

    Args:
        compat: Compatibility dict from check_environment_compatibility()

    Returns:
        Formatted multi-line string
    """
    lines = []

    # Overall status
    if compat['all_match']:
        lines.append("✓ Environment matches spec requirements")
    else:
        lines.append("⚠️  Environment differs from spec requirements")

    # Details
    lines.append("")
    lines.append("tt-metal:")
    if compat['metal_match']:
        lines.append(f"  ✓ {compat['metal_current']}")
    else:
        lines.append(f"  Current:  {compat['metal_current']}")
        lines.append(f"  Required: {compat['metal_required']}")

    lines.append("")
    lines.append("tt-vllm:")
    if compat['vllm_match']:
        lines.append(f"  ✓ {compat['vllm_current']}")
    else:
        lines.append(f"  Current:  {compat['vllm_current']}")
        lines.append(f"  Required: {compat['vllm_required']}")

    # Recommendations
    if compat['recommendations']:
        lines.append("")
        lines.append("Recommendations:")
        for rec in compat['recommendations']:
            lines.append(f"  • {rec}")

    return '\n'.join(lines)


def get_environment_info() -> Dict:
    """
    Get current environment information.

    Returns:
        Dict with current commits and paths
    """
    return {
        'tt_metal_commit': get_current_tt_metal_commit(),
        'vllm_commit': get_current_vllm_commit(),
    }
