"""
Model management commands
Download, list, validate models

NEW: Now includes search and spec-based model discovery using live data
from tt-inference-server.
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


def detect_tt_cache(model_path: Path) -> dict:
    """
    Detect TT-optimized weight cache in model directory.

    This function checks for TT hardware-specific tensor caches that have been
    pre-converted for optimal performance on Tenstorrent devices.

    Args:
        model_path: Path to model directory

    Returns:
        Dict with cache info:
        {
            'has_cache': bool,
            'device': str,  # e.g., "P150x4", "T3K"
            'cache_path': Path,
            'tensor_count': int,
            'cache_size_mb': int,
        }
    """
    result = {
        'has_cache': False,
        'device': None,
        'cache_path': None,
        'tensor_count': 0,
        'cache_size_mb': 0,
    }

    # Check for common device cache directories
    # These are the standard directory names used by TT model conversion tools
    device_dirs = ['P150x4', 'T3K', 'P150x8', 'TG', 'P150', 'N150', 'N300', 'P300C']

    for device_name in device_dirs:
        # Check for tensor_cache_bfp8 directory (standard TT cache format)
        device_cache = model_path / device_name / 'tensor_cache_bfp8'
        if device_cache.exists() and device_cache.is_dir():
            # Found TT cache! Check for tensor files
            tensor_files = list(device_cache.glob('*.tensorbin'))

            if tensor_files:
                result['has_cache'] = True
                result['device'] = device_name
                result['cache_path'] = device_cache
                result['tensor_count'] = len(tensor_files)

                # Calculate cache size
                total_bytes = sum(f.stat().st_size for f in tensor_files)
                result['cache_size_mb'] = int(total_bytes / (1024 * 1024))

                break  # Use first found cache

    return result


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
    List installed models and optionally show available models from tt-inference-server specs.

    Shows models in ~/models directory, including HuggingFace cache format.
    Indicates which model is used in the active stack (if any).

    NEW: Supports --device flag to also show available models from specs.
    """
    models_dir = Path.home() / 'models'
    show_available = hasattr(args, 'device') and args.device
    device_filter = args.device if show_available else None

    print()

    # Show installed models
    if models_dir.exists():
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

        if models:
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

            print(f"📦 Installed Models ({len(models)})")
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
        else:
            print("No models installed locally")
            print()
    else:
        print("Models directory not found: ~/models")
        print()

    # Show available models from specs if --device is specified
    if show_available:
        try:
            from tt.utils import model_specs, hardware

            print(f"🌐 Available Models for {device_filter} (from tt-inference-server)")
            print("=" * 70)
            print()

            results = model_specs.find_compatible_models(device_filter, verbose=False)

            if results:
                print(f"Found {len(results)} compatible model(s):")
                print()

                for spec in sorted(results, key=lambda x: x.get('model_name', '')):
                    model_name = spec.get('model_name', 'unknown')

                    # Get key parameters
                    device_model_spec = spec.get('device_model_spec', {})
                    vllm_args = device_model_spec.get('vllm_args', {})
                    max_len = vllm_args.get('max_model_len', 'N/A')

                    print(f"  • {model_name}")
                    print(f"    Max context: {max_len} tokens")
                    print()

                print("To get details: tt model spec-info <model-name>")
                print("To download: tt model get <model-name>")
                print()
            else:
                print(f"No models found for {device_filter}")
                print()
                print("Try:")
                print("  • tt model search <query> to search all models")
                print("  • tt model list (without --device) to see installed models")
                print()

        except Exception as e:
            print(f"⚠️  Could not fetch available models: {e}")
            print()

    if not show_available and not (models_dir.exists() and models):
        print("Download models with: tt model get <name>")
        print("Or see available models: tt model list --device P150X4")
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

    # Check for TT cache
    cache_info = detect_tt_cache(model_path)
    if cache_info['has_cache']:
        print("TT Hardware Cache:")
        print(f"  Device: {cache_info['device']}")
        print(f"  Path: {cache_info['cache_path']}")
        print(f"  Tensors: {cache_info['tensor_count']}")
        print(f"  Size: {cache_info['cache_size_mb']} MB")
        print(f"  ✓ Model is TT-optimized for {cache_info['device']}")
        print()
    else:
        print("TT Hardware Cache: Not found")
        print("  This model has not been converted for TT hardware.")
        print("  It will run slower or may not work on TT devices.")
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


def search(args):
    """
    Search for models in tt-inference-server specs.

    NEW command that searches live model specifications from tt-inference-server.
    This shows what models are officially supported on your hardware.
    """
    from tt.utils import model_specs, hardware

    query = args.query
    device_filter = args.device

    print()
    print(f"🔍 Searching for: {query}")
    print()

    # Detect hardware if no device filter specified
    if not device_filter:
        hw = hardware.detect_hardware()
        if hw:
            device_filter = hardware.get_mesh_device()
            print(f"Hardware detected: {device_filter}")
        else:
            print("No hardware detected - showing all models")
        print()

    # Search models
    try:
        results = model_specs.search_models(query, device_filter, verbose=True)
    except Exception as e:
        print(f"❌ Error searching models: {e}")
        return 1

    if not results:
        print(f"No models found matching '{query}'")
        if device_filter:
            print(f"  For device: {device_filter}")
        print()
        print("Try:")
        print("  • Use a more general search term")
        print("  • Use --device to search for other hardware")
        print("  • Run 'tt model list' to see all available models")
        return 0

    print(f"Found {len(results)} model(s):")
    print()

    # Group by device type
    by_device = {}
    for spec in results:
        device = spec.get('device_type', 'unknown')
        if device not in by_device:
            by_device[device] = []
        by_device[device].append(spec)

    # Display grouped results
    for device, specs in sorted(by_device.items()):
        print(f"📦 {device}:")
        for spec in specs:
            model_name = spec.get('model_name', 'unknown')
            spec_id = spec.get('spec_id', 'unknown')

            # Get key parameters
            device_model_spec = spec.get('device_model_spec', {})
            vllm_args = device_model_spec.get('vllm_args', {})
            max_len = vllm_args.get('max_model_len', 'N/A')

            print(f"  • {model_name}")
            print(f"    Max context: {max_len} tokens")
            print(f"    Spec ID: {spec_id}")
        print()

    print("To get details:")
    print(f"  tt model spec-info <model-name>")
    print()
    print("To run a model:")
    print(f"  tt run <model-name>")
    print()

    return 0


def spec_info(args):
    """
    Show detailed model spec information from tt-inference-server.

    NEW command that displays the full official specification for a model,
    including all parameters, environment variables, and commit requirements.
    """
    from tt.utils import model_specs, hardware, compatibility

    model_name = args.model
    device_filter = args.device

    print()
    print(f"📋 Model Spec Information: {model_name}")
    print()

    # Detect hardware if no device specified
    if not device_filter:
        hw = hardware.detect_hardware()
        if hw:
            device_filter = hardware.get_mesh_device()
            print(f"Hardware detected: {device_filter}")
        else:
            print("⚠️  No hardware detected")
            print("   Specify --device to see specs for specific hardware")
            return 1

    print()

    # Get spec
    try:
        spec = model_specs.get_model_spec(model_name, device_filter, verbose=True)
    except Exception as e:
        print(f"❌ Error fetching spec: {e}")
        return 1

    if not spec:
        print(f"❌ No spec found for '{model_name}' on {device_filter}")
        print()
        print("Try:")
        print(f"  tt model search {model_name}")
        return 1

    # Display spec information
    full_name = spec.get('model_name', model_name)
    spec_id = spec.get('spec_id', 'unknown')
    device_type = spec.get('device_type', 'unknown')

    print(f"Model: {full_name}")
    print(f"Spec ID: {spec_id}")
    print(f"Device: {device_type}")
    print()

    # Version information
    print("Required versions:")
    print(f"  tt-metal: {spec.get('tt_metal_commit', 'unknown')}")
    print(f"  tt-vllm:  {spec.get('vllm_commit', 'unknown')}")
    print()

    # Check compatibility with current environment
    print("Environment compatibility:")
    compat = compatibility.check_environment_compatibility(spec, verbose=False)

    if compat['all_match']:
        print("  ✓ Your environment matches this spec")
    else:
        print("  ⚠️  Your environment differs:")
        if not compat['metal_match']:
            print(f"    tt-metal: {compat['metal_current']} → {compat['metal_required']}")
        if not compat['vllm_match']:
            print(f"    tt-vllm:  {compat['vllm_current']} → {compat['vllm_required']}")

    print()

    # vLLM arguments
    device_model_spec = spec.get('device_model_spec', {})
    vllm_args = device_model_spec.get('vllm_args', {})

    print("vLLM parameters:")
    print(f"  max_model_len: {vllm_args.get('max_model_len', 'N/A')}")
    print(f"  max_num_seqs:  {vllm_args.get('max_num_seqs', 'N/A')}")
    print(f"  block_size:    {vllm_args.get('block_size', 'N/A')}")
    print()

    # Environment variables
    env_vars = device_model_spec.get('env_vars', {})
    if env_vars:
        print("Environment variables:")
        for key, value in env_vars.items():
            print(f"  {key}: {value}")
        print()

    # Override TT config
    override_config = device_model_spec.get('override_tt_config', {})
    if override_config:
        print("TT Config overrides:")
        for key, value in override_config.items():
            print(f"  {key}: {value}")
        print()

    print("To run this model:")
    print(f"  tt run {model_name}")
    if not compat['all_match']:
        print("  (use --force to run anyway with environment mismatch)")
    print()

    return 0


# ============================================================================
# Cache Management Commands
# ============================================================================

def cache_list(args: argparse.Namespace) -> int:
    """
    List TT cache files for a model.

    Args:
        args: Command arguments with model name

    Returns:
        Exit code (0 = success)
    """
    model_name = args.model
    models_dir = Path(args.models_dir) if hasattr(args, 'models_dir') and args.models_dir else DEFAULT_MODELS_DIR

    # Find model
    model_path = find_model_path(model_name, models_dir)

    if not model_path:
        print(f"❌ Model not found: {model_name}")
        print()
        print(f"Searched in: {models_dir}")
        return 1

    print(f"Model: {model_path.name}")
    print(f"Path: {model_path}")
    print()

    # Detect caches
    device_dirs = ['P150x4', 'T3K', 'P150x8', 'TG', 'P150', 'N150', 'N300', 'P300C']
    found_caches = []

    for device_name in device_dirs:
        device_cache = model_path / device_name / 'tensor_cache_bfp8'
        if device_cache.exists() and device_cache.is_dir():
            tensor_files = list(device_cache.glob('*.tensorbin'))
            if tensor_files:
                total_bytes = sum(f.stat().st_size for f in tensor_files)
                size_mb = int(total_bytes / (1024 * 1024))

                found_caches.append({
                    'device': device_name,
                    'path': device_cache,
                    'files': len(tensor_files),
                    'size_mb': size_mb,
                })

    if not found_caches:
        print("No TT caches found")
        print()
        print("To build a cache:")
        print(f"  tt model cache build {model_name}")
        return 0

    print("TT Caches:")
    print()
    print(f"{'DEVICE':<10}  {'FILES':<8}  {'SIZE':<10}  {'PATH'}")
    print("-" * 80)

    for cache in found_caches:
        print(f"{cache['device']:<10}  {cache['files']:<8}  {cache['size_mb']}MB{' ':<6}  {cache['path']}")

    print()
    print(f"Total: {len(found_caches)} cache(s)")

    return 0


def cache_clear(args: argparse.Namespace) -> int:
    """
    Clear TT cache for a model.

    Args:
        args: Command arguments with model name and optional device

    Returns:
        Exit code (0 = success)
    """
    import shutil

    model_name = args.model
    models_dir = Path(args.models_dir) if hasattr(args, 'models_dir') and args.models_dir else DEFAULT_MODELS_DIR
    device_filter = args.device if hasattr(args, 'device') and args.device else None

    # Find model
    model_path = find_model_path(model_name, models_dir)

    if not model_path:
        print(f"❌ Model not found: {model_name}")
        return 1

    print(f"Model: {model_path.name}")
    print()

    # Find caches to clear
    device_dirs = ['P150x4', 'T3K', 'P150x8', 'TG', 'P150', 'N150', 'N300', 'P300C']
    to_clear = []

    for device_name in device_dirs:
        if device_filter and device_name != device_filter:
            continue

        device_cache = model_path / device_name / 'tensor_cache_bfp8'
        if device_cache.exists() and device_cache.is_dir():
            tensor_files = list(device_cache.glob('*.tensorbin'))
            if tensor_files:
                total_bytes = sum(f.stat().st_size for f in tensor_files)
                size_mb = int(total_bytes / (1024 * 1024))

                to_clear.append({
                    'device': device_name,
                    'path': device_cache,
                    'files': len(tensor_files),
                    'size_mb': size_mb,
                })

    if not to_clear:
        if device_filter:
            print(f"No TT cache found for device: {device_filter}")
        else:
            print("No TT caches found")
        return 0

    # Show what will be cleared
    print("Caches to clear:")
    for cache in to_clear:
        print(f"  {cache['device']}: {cache['files']} files, {cache['size_mb']}MB")
    print()

    total_size = sum(c['size_mb'] for c in to_clear)
    print(f"⚠️  This will delete {total_size}MB of cached data")

    # Confirm unless --yes flag
    if not (hasattr(args, 'yes') and args.yes):
        response = input("Confirm? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled")
            return 0

    print()

    # Clear caches
    for cache in to_clear:
        print(f"Clearing {cache['device']}...")
        try:
            shutil.rmtree(cache['path'])
            print(f"✓ Cleared {cache['device']}")
        except Exception as e:
            print(f"❌ Error clearing {cache['device']}: {e}")

    print()
    print(f"✓ Cleared {len(to_clear)} cache(s)")

    return 0


def cache_build(args: argparse.Namespace) -> int:
    """
    Build TT cache for a model.

    Args:
        args: Command arguments with model name

    Returns:
        Exit code (0 = success)
    """
    model_name = args.model
    models_dir = Path(args.models_dir) if hasattr(args, 'models_dir') and args.models_dir else DEFAULT_MODELS_DIR

    # Find model
    model_path = find_model_path(model_name, models_dir)

    if not model_path:
        print(f"❌ Model not found: {model_name}")
        return 1

    print(f"Model: {model_path.name}")
    print(f"Path: {model_path}")
    print()

    # Check if cache already exists
    cache_info = detect_tt_cache(model_path)
    if cache_info['has_cache']:
        print(f"⚠️  Cache already exists: {cache_info['device']}")
        print(f"   {cache_info['tensor_count']} files, {cache_info['cache_size_mb']}MB")
        print()

        if not (hasattr(args, 'force') and args.force):
            print("Use --force to rebuild")
            return 1

        print("Rebuilding cache...")
        print()

    print("❌ Cache building is not yet implemented")
    print()
    print("TT cache building requires:")
    print("  1. Model loaded in TT-Metal/vLLM")
    print("  2. First inference run to generate cache")
    print("  3. Cache is automatically saved to model directory")
    print()
    print("To build a cache:")
    print(f"  1. Run: tt run {model_name}")
    print(f"  2. Wait for first inference to complete")
    print(f"  3. Cache will be saved automatically")
    print()
    print("Then check with:")
    print(f"  tt model cache ls {model_name}")

    return 1
