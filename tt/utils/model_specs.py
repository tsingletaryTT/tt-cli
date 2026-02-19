"""
Model specifications fetcher for tt-cli.

This module fetches and caches model compatibility data from tt-inference-server's
official GitHub repository. This ensures tt-cli always has up-to-date, validated
model configurations instead of relying on hardcoded heuristics.

Key features:
- Fetches live data from tt-inference-server GitHub repo
- Caches locally for 1 hour to minimize network requests
- Supports offline operation using last cached version
- Provides compatibility lookup by model name and hardware type
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

# Official source of truth for model compatibility
GITHUB_SPECS_URL = "https://raw.githubusercontent.com/tenstorrent/tt-inference-server/main/model_specs_output.json"

# Cache configuration
CACHE_DIR = Path.home() / ".tt" / "cache"
CACHE_FILE = CACHE_DIR / "model_specs.json"
CACHE_TIMESTAMP = CACHE_DIR / "model_specs_timestamp.txt"
CACHE_MAX_AGE = 3600  # 1 hour in seconds


def fetch_model_specs(force_refresh: bool = False, verbose: bool = False) -> Dict[str, Dict]:
    """
    Fetch model specifications from GitHub or cache.

    This is the core function that provides live model compatibility data.
    It fetches from tt-inference-server's GitHub repo and caches locally.

    Args:
        force_refresh: If True, bypass cache and fetch fresh data
        verbose: If True, print status messages

    Returns:
        Dictionary mapping spec IDs to model specifications

    Raises:
        RuntimeError: If fetch fails and no cache is available
    """
    # Check cache validity
    if not force_refresh and CACHE_FILE.exists() and CACHE_TIMESTAMP.exists():
        try:
            cache_age = time.time() - float(CACHE_TIMESTAMP.read_text().strip())
            if cache_age < CACHE_MAX_AGE:
                if verbose:
                    age_minutes = int(cache_age / 60)
                    print(f"🗂️  Using cached model specs ({age_minutes}m old)")
                return json.loads(CACHE_FILE.read_text())
        except (ValueError, json.JSONDecodeError) as e:
            # Cache is corrupted, fetch fresh data
            if verbose:
                print(f"⚠️  Cache corrupted, fetching fresh data")

    # Fetch from GitHub
    try:
        if verbose:
            print(f"🌐 Fetching model specs from tt-inference-server...")

        # Add User-Agent header to avoid GitHub rate limiting
        request = Request(
            GITHUB_SPECS_URL,
            headers={'User-Agent': 'tt-cli/0.1.0'}
        )

        with urlopen(request, timeout=10) as response:
            specs = json.loads(response.read().decode('utf-8'))

        # Update cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(specs, indent=2))
        CACHE_TIMESTAMP.write_text(str(time.time()))

        if verbose:
            print(f"✓ Fetched {len(specs)} model specifications")

        return specs

    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        # Network error - try to use cached version
        if CACHE_FILE.exists():
            if verbose:
                print(f"⚠️  Network error, using cached specs: {e}")
            try:
                return json.loads(CACHE_FILE.read_text())
            except json.JSONDecodeError:
                pass

        # No cache available and network failed
        raise RuntimeError(
            f"Cannot fetch model specs from GitHub and no cache available.\n"
            f"Error: {e}\n"
            f"URL: {GITHUB_SPECS_URL}\n"
            f"Check your internet connection or try again later."
        )


def find_compatible_models(hardware_type: str, verbose: bool = False) -> List[Dict]:
    """
    Find all models compatible with specified hardware type.

    Automatically handles P300C → P150 compatibility (P300C can run P150 models).

    Args:
        hardware_type: Hardware type (e.g., "P150X4", "N300", "T3K")
        verbose: If True, print status messages

    Returns:
        List of compatible model specifications
    """
    specs = fetch_model_specs(verbose=verbose)
    compatible = []

    # Normalize hardware type (remove 'x' from P150X4 -> P150x4 for consistent matching)
    hw_normalized = hardware_type.upper()

    for spec_id, spec in specs.items():
        spec_device = spec.get('device_type', '').upper()

        # Direct match
        if spec_device == hw_normalized:
            compatible.append({
                'spec_id': spec_id,
                'match_reason': 'exact',
                **spec
            })
        # Handle P300C → P150 compatibility
        # P300C hardware can run P150 models
        elif hw_normalized == 'P300C' and spec_device == 'P150':
            compatible.append({
                'spec_id': spec_id,
                'match_reason': 'p300c_p150_compatible',
                **spec
            })
        # Handle P150x4 variations (P150X4, P150x4)
        elif 'x4' in hw_normalized.lower() and 'x4' in spec_device.lower():
            if hw_normalized.replace('X', 'x') == spec_device.replace('X', 'x'):
                compatible.append({
                    'spec_id': spec_id,
                    'match_reason': 'exact',
                    **spec
                })

    return compatible


def get_model_spec(model_name: str, hardware_type: str, verbose: bool = False) -> Optional[Dict]:
    """
    Get specific model specification for hardware type.

    Performs fuzzy matching on model names to handle variations:
    - "llama-3.1-8b" matches "meta-llama/Llama-3.1-8B"
    - "qwen3" matches "Qwen/Qwen3-0.6B"

    Args:
        model_name: Model name (can be partial or fuzzy)
        hardware_type: Hardware type (e.g., "P150X4", "N300")
        verbose: If True, print status messages

    Returns:
        Model specification dict, or None if not found
    """
    compatible = find_compatible_models(hardware_type, verbose=verbose)

    if not compatible:
        return None

    # Normalize search term for matching
    model_lower = model_name.lower()

    # Try exact match on model_name field first
    for spec in compatible:
        spec_model_name = spec.get('model_name', '').lower()
        if spec_model_name == model_lower:
            return spec

    # Try matching the last part after '/' (e.g., "Llama-3.1-8B" from "meta-llama/Llama-3.1-8B")
    for spec in compatible:
        spec_model_name = spec.get('model_name', '')
        if '/' in spec_model_name:
            short_name = spec_model_name.split('/')[-1].lower()
            if short_name == model_lower:
                return spec

    # Try fuzzy match (contains)
    for spec in compatible:
        spec_model_name = spec.get('model_name', '').lower()
        # Check if search term is in model name or vice versa
        if model_lower in spec_model_name or spec_model_name.split('/')[-1].lower() in model_lower:
            return spec

    return None


def search_models(query: str, hardware_type: Optional[str] = None, verbose: bool = False) -> List[Dict]:
    """
    Search for models matching query string.

    Args:
        query: Search query (fuzzy match on model names)
        hardware_type: Optional hardware filter
        verbose: If True, print status messages

    Returns:
        List of matching model specifications
    """
    specs = fetch_model_specs(verbose=verbose)

    query_lower = query.lower()
    results = []

    for spec_id, spec in specs.items():
        model_name = spec.get('model_name', '').lower()

        # Check if query matches
        if query_lower in model_name or model_name in query_lower:
            # Filter by hardware if specified
            if hardware_type:
                spec_device = spec.get('device_type', '').upper()
                hw_normalized = hardware_type.upper()

                # Check compatibility
                if spec_device == hw_normalized:
                    results.append({'spec_id': spec_id, **spec})
                elif hw_normalized == 'P300C' and spec_device == 'P150':
                    results.append({'spec_id': spec_id, **spec})
            else:
                results.append({'spec_id': spec_id, **spec})

    return results


def get_cache_info() -> Dict:
    """
    Get information about the model specs cache.

    Returns:
        Dictionary with cache status information
    """
    if not CACHE_FILE.exists():
        return {
            'exists': False,
            'age_seconds': None,
            'age_human': 'No cache',
            'path': str(CACHE_FILE),
        }

    try:
        cache_age = time.time() - float(CACHE_TIMESTAMP.read_text().strip())
        age_minutes = int(cache_age / 60)
        age_hours = cache_age / 3600

        if age_hours >= 1:
            age_human = f"{age_hours:.1f}h old"
        else:
            age_human = f"{age_minutes}m old"

        is_fresh = cache_age < CACHE_MAX_AGE

        return {
            'exists': True,
            'age_seconds': cache_age,
            'age_human': age_human,
            'is_fresh': is_fresh,
            'path': str(CACHE_FILE),
            'max_age_seconds': CACHE_MAX_AGE,
        }
    except (ValueError, FileNotFoundError):
        return {
            'exists': True,
            'age_seconds': None,
            'age_human': 'Unknown age',
            'is_fresh': False,
            'path': str(CACHE_FILE),
        }


def clear_cache():
    """
    Clear the model specs cache.

    Forces fresh fetch on next request.
    """
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
    if CACHE_TIMESTAMP.exists():
        CACHE_TIMESTAMP.unlink()


def get_supported_hardware_types() -> List[str]:
    """
    Get list of all hardware types with model support.

    Returns:
        Sorted list of hardware types (e.g., ["N150", "N300", "P150X4", ...])
    """
    specs = fetch_model_specs()
    hardware_types = set()

    for spec in specs.values():
        device_type = spec.get('device_type', '')
        if device_type:
            hardware_types.add(device_type)

    return sorted(hardware_types)
