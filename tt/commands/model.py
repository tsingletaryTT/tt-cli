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
    """List installed models."""
    models_dir = Path.home() / 'models'

    print()

    if not models_dir.exists():
        print("Models directory not found: ~/models")
        print()
        print("Create it with: mkdir -p ~/models")
        print()
        return 1

    models = [d for d in models_dir.iterdir() if d.is_dir()]

    if not models:
        print("No models installed")
        print()
        print("Download models with: tt model get <name>")
        print()
        return 0

    print(f"Installed Models ({len(models)})")
    print("=" * 70)
    print()

    for model in sorted(models):
        # Get model size
        size = sum(f.stat().st_size for f in model.rglob('*') if f.is_file())
        size_gb = size / (1024 ** 3)

        print(f"  {model.name}")
        print(f"    Path: {model}")
        print(f"    Size: {size_gb:.1f} GB")
        print()

    return 0


def info(args):
    """Show model information."""
    model_name = args.name

    models_dir = Path.home() / 'models'
    model_path = models_dir / model_name

    print()

    if not model_path.exists():
        print(f"Model not found: {model_name}")
        print()
        print(f"Expected location: {model_path}")
        print()
        print("List installed models: tt model list")
        print()
        return 1

    # Show basic info
    print(f"Model: {model_name}")
    print("=" * 70)
    print()
    print(f"Location: {model_path}")

    # Check for config.json
    config_file = model_path / 'config.json'
    if config_file.exists():
        import json
        with open(config_file) as f:
            config = json.load(f)

        print(f"Architecture: {config.get('architectures', ['unknown'])[0]}")
        print(f"Hidden size: {config.get('hidden_size', 'unknown')}")
        print(f"Layers: {config.get('num_hidden_layers', 'unknown')}")
        print(f"Vocab size: {config.get('vocab_size', 'unknown')}")

    # Calculate size
    size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
    size_gb = size / (1024 ** 3)
    print(f"Total size: {size_gb:.1f} GB")

    print()

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
