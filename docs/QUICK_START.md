# tt-cli Quick Start Guide

## Simplest Way to Run a Model

```bash
tt run llama-3.1-8b
```

That's it! The command will:
- ✅ Auto-detect your hardware
- ✅ Fetch official specs from tt-inference-server
- ✅ Find or download the model
- ✅ Check your environment
- ✅ Start the server with optimal parameters

## Common Use Cases

### Search for Available Models

```bash
# Search for models compatible with your hardware
tt model search llama

# Search for specific hardware
tt model search qwen --device P150X4
```

### Get Model Details

```bash
# Show detailed spec info
tt model spec-info llama-3.1-8b

# Shows:
# - Required commits (tt-metal, vllm)
# - vLLM parameters
# - Environment variables
# - Compatibility status
```

### Run with Custom Settings

```bash
# Override port
tt run llama-3.1-8b --port 9000

# Override context length
tt run llama-3.1-8b --max-model-len 131072

# Force run even with environment warnings
tt run llama-3.1-8b --force
```

### Using the Traditional Workflow

The old commands still work:

```bash
# Start server with explicit control
tt serve start llama-3.1-8b

# With custom parameters
tt serve start llama-3.1-8b --max-model-len 65536 --port 8001

# Stop server
tt stop llama-3.1-8b

# Check status
tt serve status
```

## Understanding the Output

When you run `tt run llama-3.1-8b`, you'll see:

```
🚀 Running model: llama-3.1-8b

🔍 Detecting hardware...
✓ Hardware: 4x P300C
  MESH_DEVICE: P150X4

🌐 Fetching model specs from tt-inference-server...
✓ Found spec: Llama-3.1-8B
  Spec ID: id_tt-transformers_Llama-3.1-8B_p150x4
  Device: P150X4

📁 Looking for model files...
✓ Found model: /home/user/models/Llama-3.1-8B

🔧 Checking environment compatibility...
✓ Environment matches spec requirements

🚀 Starting vLLM server with official parameters...

Parameters from spec:
  max_model_len: 65536
  max_num_seqs: 32
  block_size: 64
  MESH_DEVICE: P150X4

Command:
  python -m vllm.entrypoints.openai.api_server --model /home/user/models/Llama-3.1-8B ...
```

## Troubleshooting

### Environment Mismatch Warning

If you see:
```
⚠️  Environment differs from spec:
  tt-metal:
    Current:  abc1234
    Required: ae65ee5
```

**Options:**
1. Update your environment to match (recommended):
   ```bash
   cd ~/tt-metal
   git checkout ae65ee5
   # rebuild...
   ```

2. Run anyway with --force (may not work correctly):
   ```bash
   tt run llama-3.1-8b --force
   ```

### Model Not Found

If the model isn't found locally:
```bash
# Download from HuggingFace
tt model get meta-llama/Llama-3.1-8B-Instruct
```

Then run:
```bash
tt run llama-3.1-8b
```

### No Hardware Detected

Make sure:
1. Devices are powered on
2. tt-smi is working: `tt-smi -s`
3. Firmware is up to date: `tt firmware current`

## Tips

### 1. Use Search to Discover Models

Before downloading a large model, check if it's supported:
```bash
tt model search llama --device P150X4
```

### 2. Check Spec Before Running

See what parameters will be used:
```bash
tt model spec-info llama-3.1-8b
```

### 3. Override Parameters

The spec gives you good defaults, but you can override:
```bash
tt run llama-3.1-8b --max-model-len 131072 --max-num-seqs 64
```

### 4. Use Stacks for Complex Configs

For advanced configurations, stacks are still useful:
```bash
tt stack create my-config --from-json config.json
tt stack use my-config
tt serve start
```

## What's Different from Before?

### Old Way (Multiple Steps)
```bash
# 1. Choose metal version
tt metal use v0.66.0-rc7

# 2. Set up stack
tt stack use llama-3.1-8b-p150x4

# 3. Start server
tt serve start
```

### New Way (One Command)
```bash
tt run llama-3.1-8b
```

**Why it's better:**
- ✅ Fewer steps
- ✅ Always uses official specs (not guesses)
- ✅ Auto-updates when Tenstorrent publishes new specs
- ✅ Shows you exactly what it's doing

## Advanced Features

### Cache Management

Specs are cached for 1 hour. To force refresh:
```python
from tt.utils import model_specs
model_specs.clear_cache()
```

### Check Cache Status
```python
from tt.utils import model_specs
info = model_specs.get_cache_info()
print(f"Cache age: {info['age_human']}")
```

### Get All Supported Hardware
```python
from tt.utils import model_specs
hw_types = model_specs.get_supported_hardware_types()
print(hw_types)
# ['N150', 'N300', 'P150X4', 'T3K', ...]
```

## FAQ

**Q: Where do the specs come from?**
A: From tt-inference-server's official GitHub repository. They're maintained by Tenstorrent and updated regularly.

**Q: What if I'm offline?**
A: tt-cli uses the last cached version (even if older than 1 hour).

**Q: Can I still use my custom configurations?**
A: Yes! Stacks, command-line overrides, and environment variables all still work.

**Q: What if my model isn't in the specs?**
A: tt-cli falls back to safe defaults with a warning. You can still use command-line arguments to set parameters manually.

**Q: Does this replace stacks?**
A: No, it complements them. Use `tt run` for simple cases, stacks for complex configurations.

**Q: How often are specs updated?**
A: Tenstorrent updates them in tt-inference-server. Your tt-cli fetches the latest version automatically (cached for 1 hour).

## Getting Help

```bash
# Show all commands
tt --help

# Show help for specific command
tt run --help
tt model search --help
tt model spec-info --help
```

For issues:
- Check hardware: `tt device info`
- Check environment: `tt env check`
- Check status: `tt status`

## Summary

**For most users, you only need:**
```bash
tt run <model-name>
```

**Everything else is optional!** The tool will guide you if something needs attention.
