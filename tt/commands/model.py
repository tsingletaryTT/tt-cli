"""
Model management commands
Download, list, validate models
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Tuple, Optional


# Default models directory
DEFAULT_MODELS_DIR = Path.home() / "models"


def parse_model_repo(model_str: str) -> Tuple[str, str]:
    """
    Parse HuggingFace model repository string.

    Args:
        model_str: Model string (e.g., "Qwen/Qwen3-0.6B", "gpt2")

    Returns:
        Tuple of (repo_id, local_name)
    """
    if '/' in model_str:
        # Format: org/model-name
        parts = model_str.split('/')
        repo_id = model_str
        local_name = parts[-1]
    else:
        # Simple name without org
        repo_id = model_str
        local_name = model_str

    return repo_id, local_name


def normalize_local_name(model_str: str) -> str:
    """
    Normalize HuggingFace model string to local directory name.

    Args:
        model_str: Model string (e.g., "Qwen/Qwen3-0.6B")

    Returns:
        Local directory name (e.g., "Qwen3-0.6B")
    """
    _, local_name = parse_model_repo(model_str)
    return local_name


def hf_cache_name(repo_id: str) -> str:
    """
    Convert HuggingFace repo ID to cache directory name.

    Args:
        repo_id: HuggingFace repository ID (e.g., "meta-llama/Llama-3.1-8B-Instruct")

    Returns:
        Cache directory name (e.g., "models--meta-llama--Llama-3.1-8B-Instruct")
    """
    return "models--" + repo_id.replace("/", "--")


def find_model_path(model_str: str, models_dir: Path = DEFAULT_MODELS_DIR) -> Optional[Path]:
    """
    Find the actual model path, checking multiple locations.

    Checks in order:
    1. Direct path (if absolute)
    2. Simple name (e.g., "Qwen3-0.6B")
    3. HF cache format (e.g., "models--Qwen--Qwen3-0.6B/snapshots/*/")
    4. Full repo format (e.g., "Qwen/Qwen3-0.6B" → checks cache)

    Args:
        model_str: Model identifier
        models_dir: Base models directory

    Returns:
        Path to model directory with config.json, or None if not found
    """
    models_dir = Path(models_dir).expanduser()

    # 1. Check if it's an absolute path
    if Path(model_str).is_absolute():
        p = Path(model_str)
        if p.exists() and (p / "config.json").exists():
            return p

    # 2. Check simple name (direct directory)
    simple_path = models_dir / model_str
    if simple_path.exists() and (simple_path / "config.json").exists():
        return simple_path

    # 3. Check HF cache format with snapshots
    # Handle both "models--org--name" and "org/name"
    if "/" in model_str:
        cache_name = hf_cache_name(model_str)
    else:
        cache_name = model_str

    cache_path = models_dir / cache_name

    if cache_path.exists():
        # Look for snapshots directory
        snapshots_dir = cache_path / "snapshots"
        if snapshots_dir.exists():
            # Get the most recent snapshot (or first one found)
            snapshots = list(snapshots_dir.iterdir())
            if snapshots:
                # Sort by modification time, newest first
                snapshots.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                snapshot_path = snapshots[0]

                if (snapshot_path / "config.json").exists():
                    return snapshot_path

    # 4. Try to find any matching cache directory
    # Search for "models--*--{model_name}" pattern
    _, local_name = parse_model_repo(model_str)

    for item in models_dir.iterdir():
        if item.is_dir() and item.name.endswith("--" + local_name):
            snapshots_dir = item / "snapshots"
            if snapshots_dir.exists():
                snapshots = list(snapshots_dir.iterdir())
                if snapshots:
                    snapshots.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    snapshot_path = snapshots[0]

                    if (snapshot_path / "config.json").exists():
                        return snapshot_path

    return None


def download_from_huggingface(repo_id: str, local_dir: Path, token: Optional[str] = None) -> Path:
    """
    Download model from HuggingFace Hub.

    Args:
        repo_id: HuggingFace repository ID
        local_dir: Local directory to download to
        token: Optional HuggingFace token for gated models

    Returns:
        Path to downloaded model

    Raises:
        ImportError: If huggingface_hub not installed
        Exception: If download fails
    """
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import HfHubHTTPError
    except ImportError:
        raise ImportError(
            "huggingface_hub is required for model downloads.\n"
            "Install with: pip install huggingface_hub"
        )

    try:
        print(f"📥 Downloading from HuggingFace Hub: {repo_id}")
        print(f"   Destination: {local_dir}")
        print()

        # Download with progress
        downloaded_path = snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
            token=token,
            resume_download=True,
            local_dir_use_symlinks=False,
        )

        return Path(downloaded_path)

    except HfHubHTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Repository not found: {repo_id}")
        elif e.response.status_code == 401:
            raise ValueError(f"Authentication required. Repository may be gated: {repo_id}")
        else:
            raise
    except Exception as e:
        raise Exception(f"Download failed: {e}")


def validate_model_files(model_path: Path) -> bool:
    """
    Validate that model has required files.

    Args:
        model_path: Path to model directory

    Returns:
        True if valid, False otherwise
    """
    # Check for config.json
    if not (model_path / 'config.json').exists():
        print("  ✗ Missing config.json")
        return False

    # Check for weight files
    weight_files = list(model_path.glob('*.safetensors')) + list(model_path.glob('*.bin'))
    if not weight_files:
        print("  ✗ No weight files found")
        return False

    return True


def download(args: argparse.Namespace) -> int:
    """
    Download model from HuggingFace.

    Args:
        args: Command arguments with model, models_dir, validate, token, force

    Returns:
        Exit code (0 = success)
    """
    repo_id, local_name = parse_model_repo(args.model)

    # Determine models directory
    if hasattr(args, 'models_dir') and args.models_dir is not None:
        models_dir = Path(args.models_dir)
    else:
        models_dir = DEFAULT_MODELS_DIR
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / local_name

    # Check if model already exists
    if model_path.exists() and not args.force:
        print(f"ℹ️  Model already exists: {model_path}")
        print()
        print("To re-download, use: tt model download <model> --force")
        print()
        return 0

    # Get HuggingFace token if provided
    token = args.token if hasattr(args, 'token') else None
    if not token:
        # Check environment variable
        token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')

    # Download model
    try:
        downloaded_path = download_from_huggingface(repo_id, model_path, token)

        print()
        print(f"✓ Download complete: {downloaded_path}")
        print()

        # Validate if requested
        if args.validate:
            print("Validating model files...")
            if validate_model_files(downloaded_path):
                print("✓ Model validation passed")
                print()
                return 0
            else:
                print("✗ Model validation failed")
                print()
                return 1

        return 0

    except ImportError as e:
        print(f"❌ {e}")
        print()
        return 1
    except ValueError as e:
        print(f"❌ {e}")
        print()
        if 'Authentication required' in str(e):
            print("For gated models, provide a HuggingFace token:")
            print("  tt model download <model> --token <your-token>")
            print()
            print("Or set environment variable:")
            print("  export HF_TOKEN=<your-token>")
            print()
        return 1
    except ConnectionError as e:
        print(f"❌ Network error: {e}")
        print()
        print("Check your internet connection and try again.")
        print()
        return 1
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print()
        return 1


def get(args: argparse.Namespace) -> int:
    """
    Alias for download command.

    Args:
        args: Command arguments

    Returns:
        Exit code from download()
    """
    return download(args)


def list_models(args):
    """
    List installed models.

    Shows models in ~/models directory, including HuggingFace cache format.
    Indicates which model is used in the active stack (if any).
    """
    models_dir = Path.home() / 'models'

    print()

    if not models_dir.exists():
        print("Models directory not found: ~/models")
        print()
        print("Create it with: mkdir -p ~/models")
        print()
        return 1

    # Find all models (including HF cache)
    models = []
    seen_names = set()

    for item in models_dir.iterdir():
        if not item.is_dir():
            continue

        # Skip .locks directory
        if item.name.startswith('.'):
            continue

        # Handle HF cache format (models--org--name)
        if item.name.startswith('models--'):
            snapshots_dir = item / "snapshots"
            if snapshots_dir.exists():
                snapshots = list(snapshots_dir.iterdir())
                if snapshots:
                    # Use most recent snapshot
                    snapshots.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    model_path = snapshots[0]

                    if (model_path / "config.json").exists():
                        # Extract model name from cache directory
                        # models--org--name -> org/name
                        parts = item.name.replace('models--', '').split('--')
                        if len(parts) >= 2:
                            model_name = '/'.join(parts)
                            if model_name not in seen_names:
                                models.append((model_name, model_path, item))
                                seen_names.add(model_name)
        else:
            # Direct directory
            if (item / "config.json").exists():
                model_name = item.name
                if model_name not in seen_names:
                    models.append((model_name, item, item))
                    seen_names.add(model_name)

    if not models:
        print("No models installed")
        print()
        print("Download models with: tt model download <name>")
        print()
        return 0

    # Check active stack
    active_stack = None
    stack_model = None
    try:
        from tt.utils import stack as stackutils
        active_stack = stackutils.get_active_stack()
        if active_stack:
            stack_config = stackutils.get_stack(active_stack)
            if stack_config:
                stack_model = stack_config.get('model')
    except:
        pass

    print(f"Installed Models ({len(models)})")
    print("=" * 70)
    print()

    for model_name, model_path, cache_dir in sorted(models, key=lambda x: x[0]):
        # Get model size
        size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
        size_gb = size / (1024 ** 3)

        # Check if this is the active stack model
        is_active_stack = (stack_model and model_name == stack_model)
        marker = " ✓ (active stack)" if is_active_stack else ""

        print(f"  {model_name}{marker}")
        print(f"    Path: {model_path}")
        print(f"    Size: {size_gb:.1f} GB")
        print()

    if active_stack and stack_model:
        print(f"Active stack '{active_stack}' uses: {stack_model}")
        print()

    return 0


def info(args):
    """
    Show detailed model information.

    Resolves model path intelligently (handles HF cache, direct paths, etc.)
    and shows configuration details.
    """
    model_name = args.name

    print()

    # Use find_model_path to resolve the model
    model_path = find_model_path(model_name)

    if not model_path:
        print(f"❌ Model not found: {model_name}")
        print()
        print("Searched:")
        print(f"  • Direct: ~/models/{model_name}")
        print(f"  • HF cache: ~/models/{hf_cache_name(model_name)}")
        print()
        print("List installed models: tt model list")
        print()
        return 1

    # Show basic info
    print(f"Model: {model_name}")
    print("=" * 70)
    print()
    print(f"Location: {model_path}")
    print()

    # Check for config.json
    config_file = model_path / 'config.json'
    if config_file.exists():
        import json
        with open(config_file) as f:
            config = json.load(f)

        print("Configuration:")
        print(f"  Architecture: {config.get('architectures', ['unknown'])[0]}")
        print(f"  Hidden size: {config.get('hidden_size', 'unknown')}")
        print(f"  Layers: {config.get('num_hidden_layers', 'unknown')}")
        print(f"  Vocab size: {config.get('vocab_size', 'unknown')}")

        # Show model type
        if 'model_type' in config:
            print(f"  Model type: {config['model_type']}")

        # Show max position embeddings (context length)
        if 'max_position_embeddings' in config:
            print(f"  Max context: {config['max_position_embeddings']} tokens")

        print()

    # Check for tokenizer
    tokenizer_files = list(model_path.glob('tokenizer*'))
    if tokenizer_files:
        print(f"Tokenizer: ✓ Found ({len(tokenizer_files)} files)")
    else:
        print("Tokenizer: ✗ Not found")

    # Check for weights
    safetensors = list(model_path.glob('*.safetensors'))
    bin_files = list(model_path.glob('*.bin'))

    if safetensors:
        print(f"Weights: ✓ SafeTensors format ({len(safetensors)} files)")
    elif bin_files:
        print(f"Weights: ✓ PyTorch format ({len(bin_files)} files)")
    else:
        print("Weights: ✗ Not found")

    print()

    # Calculate size
    # Get parent cache directory for accurate size
    cache_dir = model_path
    while cache_dir.name != 'models' and cache_dir.parent != cache_dir:
        if cache_dir.parent.name == 'models':
            break
        if 'models--' in cache_dir.parent.name:
            cache_dir = cache_dir.parent
        else:
            break

    size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
    size_gb = size / (1024 ** 3)
    print(f"Total size: {size_gb:.1f} GB")
    print()

    # Check if used in any stacks
    try:
        from tt.utils import stack as stackutils
        stacks = stackutils.get_stacks()
        using_stacks = [name for name, cfg in stacks.items() if cfg.get('model') == model_name]

        if using_stacks:
            print("Used in stacks:")
            for stack_name in using_stacks:
                is_active = stack_name == stackutils.get_active_stack()
                marker = " (active)" if is_active else ""
                print(f"  • {stack_name}{marker}")
            print()
    except:
        pass

    return 0


def check(args):
    """Validate model files."""
    model_name = args.name

    models_dir = Path.home() / 'models'
    model_path = models_dir / model_name

    print()
    print(f"Checking model: {model_name}")
    print()

    if not model_path.exists():
        print(f"✗ Model not found: {model_path}")
        print()
        return 1

    # Check for required files
    required_files = ['config.json']
    optional_files = ['tokenizer.json', 'tokenizer_config.json']

    all_good = True

    print("Required files:")
    for filename in required_files:
        filepath = model_path / filename
        if filepath.exists():
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} (missing)")
            all_good = False

    print()
    print("Optional files:")
    for filename in optional_files:
        filepath = model_path / filename
        if filepath.exists():
            print(f"  ✓ {filename}")
        else:
            print(f"  ⚠️  {filename} (missing, may cause issues)")

    print()

    # Check for model weights
    weight_files = list(model_path.glob('*.safetensors')) + list(model_path.glob('*.bin'))
    if weight_files:
        print(f"✓ Found {len(weight_files)} weight file(s)")
    else:
        print("✗ No weight files found (.safetensors or .bin)")
        all_good = False

    print()

    if all_good:
        print("✓ Model appears valid")
        return 0
    else:
        print("✗ Model validation failed")
        print()
        print("Try re-downloading the model:")
        print(f"  tt model get {model_name}")
        print()
        return 1
