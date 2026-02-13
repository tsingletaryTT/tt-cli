# tt-cli Project Status

**Date:** 2026-01-11
**Version:** 0.3.0 (Phase 3 Complete)
**Status:** Workflow automation and configuration complete, 121/121 tests passing

---

## What We Built (Phase 1 Complete ✅)

### Core Infrastructure

✅ **Zero-dependency CLI framework**
- Uses only Python stdlib (no external packages for core)
- Argparse for command parsing
- Clean command/subcommand structure
- Entry point: `tt` command

✅ **Hybrid venv/uv environment management**
- Detects and uses `uv` when available (10-100x faster)
- Falls back gracefully to standard `venv`
- Automatic Python version management (with uv)
- Smart conflict handling (TT-Forge vs tt-metal)

✅ **Hardware detection utilities**
- Wraps tt-smi for device information
- Multi-device support
- Blackhole vs Wormhole architecture detection
- MESH_DEVICE auto-configuration

### Working Commands

✅ **`tt status`** - Comprehensive system status
- Hardware detection (device count, type, firmware)
- Environment status (variables, issues, warnings)
- Model inventory
- JSON output for scripting
- Beautiful human-readable format

✅ **`tt env`** - Environment management
- `tt env list` - Show all environments (metal, vllm, forge, xla)
- `tt env use <name>` - Switch environments with conflict handling
- `tt env check` - Validate current environment
- `tt env fix` - Auto-fix common issues (OpenMPI, TT_METAL_HOME)
- `tt env setup <name>` - Create new environment
- `tt env install-uv` - Bootstrap uv for speed

✅ **`tt device`** - Device management
- `tt device info` - Show device details (temp, power, PCI bus)
- `tt device test` - Test all devices with TTNN
- `tt device reset` - Reset devices via tt-smi
- `tt device clear` - Full cleanup (kill processes, clear shm)

✅ **`tt model`** - Model management
- `tt model list` - List installed models
- `tt model info <name>` - Show model details (arch, size, config)
- `tt model check <name>` - Validate model files

### Project Structure

```
~/tt-cli/
├── tt/
│   ├── core/
│   │   └── cli.py          # Main CLI entry point (300 lines)
│   ├── commands/
│   │   ├── status.py       # Status command (150 lines)
│   │   ├── env.py          # Environment commands (200 lines)
│   │   ├── device.py       # Device commands (180 lines)
│   │   ├── model.py        # Model commands (150 lines)
│   │   └── serve.py        # Server commands (stub)
│   ├── utils/
│   │   ├── hardware.py     # Hardware detection (200 lines)
│   │   └── envmanager.py   # Environment management (250 lines)
│   ├── integrations/       # (empty, for Phase 2)
│   └── tui/
│       └── app.py          # TUI stub
├── setup.py
├── README.md
└── docs/
    ├── quickstart.md
    └── status.md (this file)
└── requirements.txt
```

**Total code:** ~1,500 lines of production-quality Python

### Installation & Usage

```bash
# Install
cd ~/tt-cli
pip install -e .

# Use
tt status
tt env list
tt env use vllm
tt device info
tt model list
```

---

## Phase 2 Complete ✅

### Priority 1: Server Management ✅ COMPLETE

✅ **`tt serve start`** - Full vLLM server management
- ✅ Hardware detection and optimal parameter selection
- ✅ Model spec matching (device count → tensor parallelism)
- ✅ Generate optimal vLLM commands with MESH_DEVICE, TT_METAL_ARCH_NAME
- ✅ Start server in background (detached mode) or foreground
- ✅ Save PID for management (~/.tt/servers/*.pid)
- ✅ Log file management (~/.tt/servers/logs/*.log)

✅ **`tt stop`** - Stop running servers
- ✅ Load server state from PID files
- ✅ Send SIGTERM to PIDs with graceful shutdown
- ✅ Force kill if not responding
- ✅ Clean up PID files

✅ **`tt serve status`** - Server monitoring
- ✅ List all running servers
- ✅ Show PID, port, CPU, memory (if psutil available)
- ✅ Clean up stale PID files
- ✅ JSON output support

✅ **`tt restart`** - Restart servers
- ✅ Combine stop + start

**Actual time:** ~16 hours

### Priority 2: Model Downloads ✅ COMPLETE

✅ **`tt model download`** - Download from HuggingFace
- ✅ Use huggingface_hub API
- ✅ Show progress bar during download
- ✅ Validate after download (--validate flag)
- ✅ Handle authentication (--token flag, HF_TOKEN env var)
- ✅ Handle gated models
- ✅ Force re-download (--force flag)
- ✅ Smart repo ID parsing (org/model → local name)

**Actual time:** ~8 hours

---

## Phase 3 Complete ✅

### Priority 1: Workflow Automation ✅ COMPLETE

✅ **`tt workflow`** - Automated workflows
- ✅ `tt workflow list` - List available workflows
- ✅ `tt workflow info <name>` - Show workflow details
- ✅ `tt workflow run <name>` - Execute workflow
- ✅ **setup workflow** - Development environment setup
- ✅ **test-model workflow** - Complete model testing (download, validate, serve, test inference, stop)
- ✅ **--quick mode** - Fast validation without server startup
- ✅ **--dry-run mode** - Preview workflow steps
- ✅ **benchmark workflow** - Performance testing (stub for future)
- ✅ **eval workflow** - Run evaluation suites (stub for future)

**Actual time:** ~12 hours

### Priority 2: Configuration Management ✅ COMPLETE

✅ **Configuration file support**
- ✅ `~/.ttconfig` YAML/JSON config support
- ✅ `tt config get <key>` - Get configuration value (dot notation)
- ✅ `tt config set <key> <value>` - Set configuration value
- ✅ `tt config list [--json]` - List all configuration
- ✅ `tt config reset` - Reset to defaults
- ✅ Defaults for models_dir, server ports, etc.
- ✅ Optional PyYAML dependency (falls back to JSON)

**Actual time:** ~8 hours

### Priority 3: TT Hardware Compatibility ✅ COMPLETE

✅ **DeepSeek-R1-Distill-Llama-70B testing on P300**
- ✅ Fixed tensor-parallel-size handling (TT uses MESH_DEVICE instead)
- ✅ Auto-detect HF_MODEL environment variable
- ✅ Auto-detect vLLM Python environment
- ✅ Set TT_METAL_HOME and PYTHONPATH automatically
- ✅ Successfully loaded 70B model on 2-chip P300 (Blackhole)
- ✅ Tensor cache generation working
- ✅ Multi-chip mesh device initialization working

**Actual time:** ~4 hours

---

## What's Next (Phase 4)

### Priority 1: Production Testing

🚧 **Hardware Testing** (In Progress)
- [x] Test DeepSeek-R1-Distill-Llama-70B on P300
- [ ] Test with Llama models
- [ ] Test with Qwen models
- [ ] Multi-device stress testing
- [ ] Concurrent server testing

### Priority 2: Distribution & Polish

🔜 **PyPI Release**
- [ ] Package for PyPI
- [ ] Release automation
- [ ] Version management
- [ ] Changelog generation

🔜 **TUI Interface**
- [ ] textual + rich integration
- [ ] Interactive status dashboard
- [ ] Server monitoring view
- [ ] Log streaming

---

## Technical Decisions Made

### ✅ Python over Rust (for now)

**Why Python:**
- Built 1,500 lines in ~2 hours (vs weeks in Rust)
- Zero dependencies possible (stdlib)
- Direct access to tt-metal Python APIs
- Community knows Python better
- Most tools are I/O-bound, not CPU-bound

**When to reconsider Rust:**
- If startup time becomes an issue (currently ~100ms)
- If users demand single-binary distribution
- If performance profiling shows bottlenecks
- Realistically: Year 2, after validating UX

### ✅ Hybrid venv/uv Approach

**Why hybrid:**
- Works everywhere (venv is built-in)
- Fast when available (uv auto-detected)
- Aligns with tt-inference-server (already uses uv)
- No barriers to entry

**Implementation:**
```python
def create_venv(path, python_version=None):
    if has_uv() and python_version:
        # Use uv for specific Python versions
        subprocess.run(f"uv venv --python={python_version} {path}")
    else:
        # Fallback to standard venv
        subprocess.run(f"python3 -m venv {path}")
```

### ✅ Zero Dependencies for Core

**Why:**
- Immediate usability (no pip install needed)
- Reduces attack surface
- Faster installation
- More portable

**Trade-offs:**
- No fancy CLI frameworks (using argparse)
- Manual color codes (no colorama)
- Stdlib HTTP/JSON (no requests library)

**Worth it:** Yes. Core functionality works everywhere instantly.

---

## Metrics

### Scripts Eliminated (So Far)

| Script Type | Lines | Status |
|-------------|-------|--------|
| Environment activation | ~50 | ✅ Eliminated (`tt env use`) |
| Environment setup | ~80 | ✅ Eliminated (`tt env setup`) |
| Hardware detection | ~40 | ✅ Eliminated (`tt device info`) |
| Device testing | ~100 | ✅ Eliminated (`tt device test`) |
| **Total** | **~270** | **✅ Replaced with `tt`** |

### Eliminated in Phase 2 ✅

| Script Type | Lines | Status |
|-------------|-------|--------|
| Server start | ~200 | ✅ Eliminated (`tt serve start`) |
| Server stop/restart | ~50 | ✅ Eliminated (`tt stop/restart`) |
| Model downloads | ~60 | ✅ Eliminated (`tt model download`) |
| **Total** | **~310** | **✅ Phase 2 Complete** |

### Eliminated in Phase 3 ✅

| Script Type | Lines | Status |
|-------------|-------|--------|
| Workflow automation | ~250 | ✅ Eliminated (`tt workflow`) |
| Config management | ~50 | ✅ Eliminated (`tt config`) |
| **Total** | **~300** | **✅ Phase 3 Complete** |

### Total Scripts Eliminated

**~880 lines of throwaway scripts** replaced with unified `tt` command.

### User Experience Impact

**Before (with scripts):**
- Maintain 8+ throwaway scripts
- Remember which script does what
- Debug environment issues for hours
- Manual variable management

**After (with `tt`):**
- Zero scripts to maintain
- One command interface
- Auto-fixing environment issues
- Smart defaults everywhere

**Time savings (estimated):**
- Setup tasks: 10x faster
- Environment switching: 20x faster
- Error recovery: 30x faster

---

## Known Issues & Limitations

### Environment Persistence

**Issue:** Environment changes don't persist across shell sessions.

**Why:** Each `tt` command runs in a subshell - can't modify parent shell's environment.

**Solutions:**
1. **Manual:** Add to `~/.bashrc` (already documented)
2. **Eval pattern:** `eval "$(tt env use vllm --export)"` (Phase 2)
3. **Shell integration:** Source script that wraps `tt` (Phase 3)

**Status:** Documented in docs/quickstart.md, eval pattern coming in Phase 2

### Server Management ✅ IMPLEMENTED

**Status:** Complete! Full server lifecycle management implemented with PID tracking, log files, and hardware-aware parameter optimization.

### No TUI Yet

**Issue:** `tt-tui` command just prints message.

**Why:** Phase 3 feature (after core commands stable).

**Timeline:** Weeks 5-6

---

## Testing

### Automated Testing ✅ COMPLETE

✅ **Unit tests** - 71 tests covering:
- `test_hardware.py` - Hardware detection logic (21 tests)
- `test_envmanager.py` - Environment management (29 tests)
- `test_config.py` - Configuration management (17 tests)
- `test_cli.py` - CLI parsing (4 tests)

✅ **Integration tests** - 50 tests covering:
- `test_commands.py` - All command flows (17 tests)
- `test_model_download.py` - Model download scenarios (12 tests)
- `test_serve.py` - Server management (12 tests)
- `test_workflow.py` - Workflow automation (13 tests)

**Total: 121/121 tests passing** ✓

```bash
pytest
# ============================== 121 passed in 0.08s ==============================
```

### Manual Testing Done ✅

```bash
# Status
tt status              # ✅ Works
tt status --json       # ✅ Works

# Environment
tt env list            # ✅ Works (shows 4 environments)
tt env use vllm        # ✅ Works (sets variables)
tt env check           # ✅ Works (finds issues)
tt env fix             # ✅ Works (fixes LD_LIBRARY_PATH)

# Device
tt device info         # ⚠️  Requires tt-smi
tt device test         # ⚠️  Requires TTNN + hardware

# Model
tt model list          # ✅ Works (4 models: DeepSeek-R1, Llama-3.1-8B, Llama-3.3-70B, Qwen3-0.6B)
tt model info Qwen3-0.6B  # ✅ Works (shows config)
tt model check Qwen3-0.6B # ✅ Works (validates files)
tt model download <model> # ✅ Works (downloads from HuggingFace)

# Server Management
tt serve start <model>     # ✅ Works (starts vLLM)
tt serve status            # ✅ Works (shows running servers)
tt stop <model>            # ✅ Works (stops server)
tt restart <model>         # ✅ Works (restarts server)

# Workflow Automation
tt workflow list           # ✅ Works (shows 4 workflows)
tt workflow info setup     # ✅ Works (shows workflow details)
tt workflow run setup      # ✅ Works (runs setup workflow)
tt workflow run test-model --model Qwen3-0.6B --quick  # ✅ Works

# Configuration
tt config list             # ✅ Works (shows config)
tt config get models_dir   # ✅ Works (gets value)
tt config set models_dir ~/my-models  # ✅ Works (sets value)
tt config reset            # ✅ Works (resets config)

# Hardware Testing (P300 Blackhole)
tt serve start DeepSeek-R1-Distill-Llama-70B --detach  # ✅ Works (loads 70B model)
```

### CI/CD (Phase 3)

🚧 **GitHub Actions** - Automated testing on push

---

## Performance

### Startup Time

```bash
time tt status
# Real: 0.120s (acceptable for human-run commands)
```

### Installation Size

```bash
du -sh ~/tt-cli
# 100K (source code only, no dependencies!)

pip show tt-cli
# Size: ~50KB installed
```

### Memory Usage

```bash
ps aux | grep "tt status"
# ~25MB RSS (minimal for Python)
```

**Conclusion:** Performance is fine for human-run CLI commands. I/O time (tt-smi, file reads) dominates CPU time.

---

## Next Steps

### Current Sprint (Phase 3)

1. **Workflow Integration** 🚧 IN PROGRESS
   - Integrate with tt-inference-server workflows
   - Bootstrap uv for fast environment setup
   - Run evals, benchmarks, tests
   - Generate reports

2. **Test with Real Hardware**
   - Test server start/stop with DeepSeek-R1-Distill-Llama-70B
   - Validate hardware detection on production systems
   - Stress test with multiple concurrent servers

3. **Configuration File Support**
   - `~/.ttconfig` for user preferences
   - Per-project `.tt.config` for repo-specific settings
   - Default model/environment configurations

### Future Phases

**Phase 4: Polish & Distribution**
1. TUI implementation (textual + rich)
2. PyPI packaging and distribution
3. VSCode extension integration
4. Documentation and tutorials

**Phase 5: Community**
1. Plugin system
2. Community contributions
3. Additional hardware support

---

## Success Criteria

### MVP (Phase 1) ✅ COMPLETE

- [x] Core CLI framework working
- [x] Zero dependencies
- [x] Basic commands implemented
- [x] Environment management working
- [x] Device management working
- [x] Installation tested

### Phase 2 Goals ✅ COMPLETE

- [x] Server management working (start/stop/restart)
- [x] Model downloads working
- [x] 88/88 automated tests passing
- [x] Hardware detection and optimization
- [x] Comprehensive documentation

### Phase 3 Goals ✅ COMPLETE

- [x] Workflow automation implemented (4 workflows)
- [x] Configuration management implemented
- [x] 121/121 automated tests passing
- [x] Tested on real hardware (P300 Blackhole, DeepSeek-R1-70B)
- [x] TT hardware compatibility fixes
- [x] Comprehensive COOKBOOK with 52 recipes

### Phase 4 Goals

- [ ] TUI implemented
- [ ] PyPI published
- [ ] Plugin system
- [ ] 20+ GitHub stars
- [ ] Community contributions
- [ ] "Just use `tt`" becomes standard advice

---

## Resources

- **Code:** `~/tt-cli/`
- **Docs:** `README.md`, `docs/quickstart.md`
- **Vision:** `~/tt-vscode-toolkit/TT_CLI_VISION.md`
- **tt-jukebox:** `~/tt-vscode-toolkit/vendor/tt-jukebox/`

## Contact

Questions? Check:
1. `tt --help`
2. `QUICKSTART.md`
3. Open an issue on GitHub

---

**Status: Phase 3 Complete! 121/121 tests passing. Workflow automation, configuration management, and TT hardware compatibility implemented. Ready for production testing!** 🎉
