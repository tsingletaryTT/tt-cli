"""
Workflow commands for tt-cli.

Provides commands to run common workflows like setup, benchmarks, and evaluations.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional

from tt.utils import envmanager, hardware


# Define available workflows
WORKFLOWS = {
    'setup': {
        'name': 'Development Setup',
        'description': 'Set up development environment with uv and create virtual environments',
        'steps': [
            'Check for uv installation',
            'Install uv if not present (optional)',
            'Create tt-metal virtual environment',
            'Create vllm virtual environment',
            'Verify environment setup',
        ],
    },
    'test-model': {
        'name': 'Model Testing',
        'description': 'Complete model testing workflow: download, validate, serve, test',
        'steps': [
            'Download model from HuggingFace (if not present)',
            'Validate model files',
            'Start vLLM server',
            'Run basic inference test',
            'Stop server',
        ],
        'requires': ['model'],
    },
    'benchmark': {
        'name': 'Model Benchmarking',
        'description': 'Run performance benchmarks on a model',
        'steps': [
            'Validate model exists',
            'Start vLLM server with optimal settings',
            'Run throughput benchmark',
            'Run latency benchmark',
            'Generate report',
            'Stop server',
        ],
        'requires': ['model'],
    },
    'eval': {
        'name': 'Model Evaluation',
        'description': 'Run evaluation suites (MMLU, HellaSwag, etc.)',
        'steps': [
            'Validate model exists',
            'Check evaluation dataset availability',
            'Start vLLM server',
            'Run evaluation suite',
            'Generate accuracy report',
            'Stop server',
        ],
        'requires': ['model', 'eval_suite'],
    },
}


def list_workflows(args: argparse.Namespace) -> int:
    """
    List available workflows.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 = success)
    """
    if args.json:
        workflows_list = [
            {
                'id': wf_id,
                'name': wf['name'],
                'description': wf['description'],
                'requires': wf.get('requires', []),
            }
            for wf_id, wf in WORKFLOWS.items()
        ]
        print(json.dumps({'workflows': workflows_list}, indent=2))
    else:
        print("Available Workflows:")
        print()
        for wf_id, wf in WORKFLOWS.items():
            print(f"  {wf_id}")
            print(f"    {wf['name']} - {wf['description']}")
            if 'requires' in wf:
                print(f"    Requires: {', '.join(wf['requires'])}")
            print()

    return 0


def info(args: argparse.Namespace) -> int:
    """
    Show detailed information about a workflow.

    Args:
        args: Command arguments with workflow name

    Returns:
        Exit code (0 = success)
    """
    workflow_name = args.name

    if workflow_name not in WORKFLOWS:
        print(f"❌ Workflow '{workflow_name}' not found")
        print()
        print("Available workflows:")
        for wf_id in WORKFLOWS.keys():
            print(f"  - {wf_id}")
        return 1

    wf = WORKFLOWS[workflow_name]

    print(f"{wf['name']}")
    print("=" * len(wf['name']))
    print()
    print(f"Description: {wf['description']}")
    print()

    if 'requires' in wf:
        print(f"Requires: {', '.join(wf['requires'])}")
        print()

    print("Steps:")
    for i, step in enumerate(wf['steps'], 1):
        print(f"  {i}. {step}")
    print()

    print(f"Run with: tt workflow run {workflow_name}")
    if 'requires' in wf:
        print(f"Example: tt workflow run {workflow_name} --model Qwen3-0.6B")
    print()

    return 0


def run(args: argparse.Namespace) -> int:
    """
    Run a workflow.

    Args:
        args: Command arguments with workflow name and options

    Returns:
        Exit code (0 = success)
    """
    workflow_name = args.name

    if workflow_name not in WORKFLOWS:
        print(f"❌ Workflow '{workflow_name}' not found")
        print()
        print("Available workflows:")
        for wf_id in WORKFLOWS.keys():
            print(f"  - {wf_id}")
        return 1

    wf = WORKFLOWS[workflow_name]

    # Check required arguments
    if 'requires' in wf:
        for req in wf['requires']:
            if not hasattr(args, req) or getattr(args, req) is None:
                print(f"❌ Error: Workflow '{workflow_name}' requires --{req}")
                print()
                print(f"Example: tt workflow run {workflow_name} --{req} <value>")
                return 1

    # Dry run mode - just show what would be done
    if args.dry_run:
        print(f"Dry run: {wf['name']}")
        print()
        print("Would execute the following steps:")
        for i, step in enumerate(wf['steps'], 1):
            print(f"  {i}. {step}")
        print()
        return 0

    # Execute workflow
    print(f"Running workflow: {wf['name']}")
    print()

    try:
        if workflow_name == 'setup':
            return run_setup_workflow()
        elif workflow_name == 'test-model':
            quick = getattr(args, 'quick', False)
            return run_test_model_workflow(args.model, quick=quick)
        elif workflow_name == 'benchmark':
            return run_benchmark_workflow(args.model)
        elif workflow_name == 'eval':
            return run_eval_workflow(args.model, args.eval_suite)
        else:
            print(f"⚠️  Workflow '{workflow_name}' not yet implemented")
            return 1

    except KeyboardInterrupt:
        print()
        print("❌ Workflow interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return 1


def run_setup_workflow() -> int:
    """
    Run the development setup workflow.

    Returns:
        Exit code (0 = success)
    """
    print("Step 1/5: Checking for uv installation...")

    has_uv = envmanager.has_uv()
    if has_uv:
        print("✓ uv is installed")
    else:
        print("⚠️  uv not found")
        print()
        print("uv provides 10-100x faster environment operations.")
        print("Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        print()
        print("Continuing with standard venv...")

    print()
    print("Step 2/5: Checking environment status...")

    env_status = envmanager.check_environment()
    if env_status['status'] == 'ok':
        print("✓ Environment is configured correctly")
    else:
        print(f"⚠️  Found {len(env_status.get('issues', []))} issues")
        for issue in env_status.get('issues', []):
            print(f"  - {issue}")

    print()
    print("Step 3/5: Checking for environment fixes...")

    fixes, env_vars = envmanager.fix_environment()
    if fixes:
        print(f"✓ Applied {len(fixes)} fixes")
        for fix in fixes:
            print(f"  - {fix}")
    else:
        print("✓ No fixes needed")

    print()
    print("Step 4/5: Verifying hardware detection...")

    hw = hardware.detect_hardware()
    if hw:
        print(f"✓ Detected {hw['count']} x {hw['primary_type']} device(s)")
    else:
        print("⚠️  No hardware detected (tt-smi not available or no devices)")

    print()
    print("Step 5/5: Setup complete!")
    print()
    print("Next steps:")
    print("  1. Activate an environment: tt env use metal")
    print("  2. List models: tt model list")
    print("  3. Check system status: tt status")
    print()

    return 0


def test_model_inference(model: str, port: int = 8000, timeout: int = 30) -> bool:
    """
    Test model inference with a simple request.

    Args:
        model: Model name
        port: Server port
        timeout: Request timeout in seconds

    Returns:
        True if test passed, False otherwise
    """
    import time
    import urllib.request
    import urllib.error

    # Wait for server to be ready
    print("  Waiting for server to be ready...")
    max_wait = 60  # seconds
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            req = urllib.request.Request(f"http://localhost:{port}/v1/models")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print("  ✓ Server is ready")
                    break
        except (urllib.error.URLError, ConnectionRefusedError):
            time.sleep(2)
    else:
        print("  ❌ Server did not become ready in time")
        return False

    # Test inference
    print("  Running inference test...")
    try:
        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }).encode('utf-8')

        req = urllib.request.Request(
            f"http://localhost:{port}/v1/chat/completions",
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                result = json.loads(response.read())
                if 'choices' in result and len(result['choices']) > 0:
                    print("  ✓ Inference test passed")
                    return True
    except Exception as e:
        print(f"  ❌ Inference test failed: {e}")
        return False

    return False


def run_test_model_workflow(model: str, quick: bool = False) -> int:
    """
    Run the model testing workflow.

    Args:
        model: Model name
        quick: If True, only validate model without starting server

    Returns:
        Exit code (0 = success)
    """
    from tt.commands import model as model_cmd
    from tt.commands import serve

    print(f"🧪 Testing Model: {model}")
    print("=" * 60)
    print()

    # Step 1: Check if model exists and is valid
    print("Step 1/5: Validating model files...")

    # Use Path to find model
    models_dir = Path.home() / "models"
    model_path = models_dir / model

    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print()
        print(f"Download with: tt model get {model}")
        return 1

    # Validate model
    check_args = argparse.Namespace(name=model)
    result = model_cmd.check(check_args)

    if result != 0:
        print("❌ Model validation failed")
        return 1

    print()

    # Quick mode - just validate, don't start server
    if quick:
        print("✓ Model validation complete (quick mode)")
        print()
        print("To run full test with inference: tt workflow run test-model --model", model)
        return 0

    # Step 2: Start vLLM server
    print("Step 2/5: Starting vLLM server...")

    serve_args = argparse.Namespace(
        model=model,
        port=8000,
        max_model_len=None,
        tensor_parallel=None,
        detach=True,
        models_dir=str(models_dir),
        pid_dir=None,
    )

    result = serve.start(serve_args)

    if result != 0:
        print("❌ Failed to start server")
        return 1

    print()

    try:
        # Step 3: Wait and test inference
        print("Step 3/5: Testing inference...")

        inference_ok = test_model_inference(model, port=8000, timeout=30)

        if not inference_ok:
            print("❌ Inference test failed")
            return 1

        print()

        # Step 4: Check server status
        print("Step 4/5: Verifying server status...")

        status_args = argparse.Namespace(
            json=False,
            pid_dir=None,
        )
        serve.status(status_args)

        print()

    finally:
        # Step 5: Stop server (always runs, even if test failed)
        print("Step 5/5: Stopping server...")

        stop_args = argparse.Namespace(
            model=model,
            pid_dir=None,
        )

        serve.stop(stop_args)
        print()

    print("✓ Model test workflow complete!")
    print()

    return 0


def run_benchmark_workflow(model: str) -> int:
    """
    Run the model benchmarking workflow.

    Args:
        model: Model name

    Returns:
        Exit code (0 = success)
    """
    import time
    import urllib.request
    import urllib.error
    from datetime import datetime

    from tt.commands import model as model_cmd
    from tt.commands import serve

    print(f"📊 Benchmarking Model: {model}")
    print("=" * 70)
    print()

    # Step 1: Validate model exists
    print("Step 1/6: Validating model...")

    models_dir = Path.home() / "models"
    model_path = models_dir / model

    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print()
        print(f"Download with: tt model get {model}")
        return 1

    print(f"✓ Model found: {model_path}")
    print()

    # Step 2: Check if server is already running
    print("Step 2/6: Checking server status...")

    port = 8000
    server_running = False
    server_model_id = None
    try:
        req = urllib.request.Request(f"http://localhost:{port}/v1/models")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                server_running = True
                # Get the actual model ID from the server
                models_data = json.loads(response.read())
                if 'data' in models_data and len(models_data['data']) > 0:
                    server_model_id = models_data['data'][0]['id']
                print(f"✓ Server already running on port {port}")
                if server_model_id:
                    print(f"  Model ID: {server_model_id}")
    except (urllib.error.URLError, ConnectionRefusedError):
        print(f"⚠️  No server running on port {port}")

    # Start server if not running
    server_started_by_us = False
    if not server_running:
        print()
        print("Step 3/6: Starting vLLM server...")

        serve_args = argparse.Namespace(
            model=model,
            port=port,
            max_model_len=None,
            tensor_parallel=None,
            detach=True,
            models_dir=str(models_dir),
            pid_dir=None,
        )

        result = serve.start(serve_args)

        if result != 0:
            print("❌ Failed to start server")
            return 1

        server_started_by_us = True

        # Wait for server to be ready
        print("  Waiting for server to be ready...")
        max_wait = 180  # 3 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                req = urllib.request.Request(f"http://localhost:{port}/v1/models")
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        print("  ✓ Server is ready")
                        break
            except (urllib.error.URLError, ConnectionRefusedError):
                time.sleep(5)
        else:
            print("  ❌ Server did not become ready in time")
            if server_started_by_us:
                # Clean up
                stop_args = argparse.Namespace(model=model, pid_dir=None)
                serve.stop(stop_args)
            return 1

        print()
    else:
        print()
        print("Step 3/6: Using existing server...")
        print()

    try:
        # Determine the model ID to use in requests
        # If server is running, use its model ID; otherwise use full path
        if server_model_id:
            request_model_id = server_model_id
        else:
            request_model_id = str(model_path)

        # Step 4: Run latency benchmark
        print("Step 4/6: Running latency benchmark...")
        print("  Testing single request latency...")

        latencies = []
        test_prompts = [
            "Hello, how are you?",
            "What is the capital of France?",
            "Explain quantum computing in simple terms.",
            "Write a haiku about coding.",
            "What is 2 + 2?",
        ]

        for i, prompt in enumerate(test_prompts):
            try:
                data = json.dumps({
                    "model": request_model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.7,
                }).encode('utf-8')

                req = urllib.request.Request(
                    f"http://localhost:{port}/v1/chat/completions",
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )

                start = time.time()
                with urllib.request.urlopen(req, timeout=60) as response:
                    elapsed = time.time() - start
                    result = json.loads(response.read())

                    if 'choices' in result and len(result['choices']) > 0:
                        latencies.append(elapsed)
                        tokens_generated = result['usage']['completion_tokens']
                        print(f"  Request {i+1}/{len(test_prompts)}: {elapsed:.2f}s ({tokens_generated} tokens)")
            except Exception as e:
                print(f"  ❌ Request {i+1} failed: {e}")

        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            print()
            print(f"  ✓ Average latency: {avg_latency:.2f}s")
            print(f"    Min: {min_latency:.2f}s, Max: {max_latency:.2f}s")
        else:
            print("  ❌ No successful latency tests")

        print()

        # Step 5: Run throughput benchmark
        print("Step 5/6: Running throughput benchmark...")
        print("  Testing concurrent request handling...")

        # Simple throughput test with concurrent requests
        import concurrent.futures

        def make_request(prompt_idx):
            try:
                data = json.dumps({
                    "model": request_model_id,
                    "messages": [{"role": "user", "content": f"Generate a story about prompt {prompt_idx}"}],
                    "max_tokens": 100,
                    "temperature": 0.7,
                }).encode('utf-8')

                req = urllib.request.Request(
                    f"http://localhost:{port}/v1/chat/completions",
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )

                start = time.time()
                with urllib.request.urlopen(req, timeout=120) as response:
                    elapsed = time.time() - start
                    result = json.loads(response.read())
                    tokens_generated = result['usage']['completion_tokens']
                    return {"success": True, "elapsed": elapsed, "tokens": tokens_generated}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Run 4 concurrent requests
        num_concurrent = 4
        print(f"  Running {num_concurrent} concurrent requests...")

        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_concurrent)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        total_elapsed = time.time() - start_time

        successful = [r for r in results if r['success']]
        if successful:
            total_tokens = sum(r['tokens'] for r in successful)
            throughput = total_tokens / total_elapsed
            print(f"  ✓ Completed {len(successful)}/{num_concurrent} requests")
            print(f"    Total time: {total_elapsed:.2f}s")
            print(f"    Total tokens: {total_tokens}")
            print(f"    Throughput: {throughput:.2f} tokens/s")
        else:
            print(f"  ❌ No successful throughput tests")

        print()

        # Step 6: Generate report
        print("Step 6/6: Benchmark Summary")
        print("=" * 70)
        print()
        print(f"Model: {model}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if latencies:
            print("Latency Metrics:")
            print(f"  Average: {avg_latency:.2f}s")
            print(f"  Min: {min_latency:.2f}s")
            print(f"  Max: {max_latency:.2f}s")
            print()

        if successful:
            print("Throughput Metrics:")
            print(f"  Concurrent requests: {num_concurrent}")
            print(f"  Throughput: {throughput:.2f} tokens/s")
            print()

        hw = hardware.detect_hardware()
        if hw:
            print("Hardware:")
            print(f"  Device: {hw['count']}x {hw['primary_type']}")
            print(f"  MESH_DEVICE: {hardware.get_mesh_device()}")
            print()

        print("✓ Benchmark complete!")
        print()

    finally:
        # Clean up - only stop server if we started it
        if server_started_by_us:
            print("Stopping server...")
            stop_args = argparse.Namespace(model=model, pid_dir=None)
            serve.stop(stop_args)
            print()

    return 0


def run_eval_workflow(model: str, eval_suite: str) -> int:
    """
    Run the model evaluation workflow.

    Args:
        model: Model name
        eval_suite: Evaluation suite name

    Returns:
        Exit code (0 = success)
    """
    print(f"Evaluating model: {model}")
    print(f"Evaluation suite: {eval_suite}")
    print()
    print("⚠️  Evaluation workflow not yet implemented")
    print()

    return 1


def list_available_evals() -> List[str]:
    """
    List available evaluation suites.

    Returns:
        List of evaluation suite names
    """
    return ['mmlu', 'hellaswag', 'truthfulqa', 'winogrande', 'arc']
