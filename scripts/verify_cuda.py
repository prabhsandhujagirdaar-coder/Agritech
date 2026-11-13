#!/usr/bin/env python3
"""
AgriChain AI - PyTorch & CUDA Hardware Verification Script
===========================================================
Validates Python runtime, PyTorch build, CUDA driver integration,
NVIDIA RTX 4050 GPU detection, and hardware tensor allocation.
"""

import sys
import platform
import time

def main():
    print("=" * 70)
    print("AGRICHAIN AI — PYTORCH & CUDA VERIFICATION REPORT")
    print("=" * 70)

    # 1. Host & Python Environment
    print(f"Platform            : {platform.platform()}")
    print(f"Python Executable   : {sys.executable}")
    print(f"Python Version      : {platform.python_version()} ({platform.python_implementation()})")
    print("-" * 70)

    # 2. PyTorch Package Information
    try:
        import torch
    except ImportError as e:
        print(f"ERROR: Failed to import torch: {e}")
        sys.exit(1)

    try:
        import torchvision
        tv_version = torchvision.__version__
    except ImportError:
        tv_version = "Not installed"

    print(f"PyTorch Version     : {torch.__version__}")
    print(f"Torchvision Version : {tv_version}")
    print(f"PyTorch Debug Build : {torch.version.debug}")
    print(f"CUDA Built With     : {torch.version.cuda}")
    print(f"cuDNN Version       : {torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else 'N/A'}")
    print("-" * 70)

    # 3. CUDA Availability & Hardware Detection
    cuda_available = torch.cuda.is_available()
    print(f"torch.cuda.is_available() : {cuda_available}")

    if not cuda_available:
        print("\n[WARNING] CUDA is NOT accessible from PyTorch.")
        print("Tensors will execute in CPU mode.")
        sys.exit(1)

    device_count = torch.cuda.device_count()
    current_device = torch.cuda.current_device()
    device_name = torch.cuda.get_device_name(current_device)
    device_capability = torch.cuda.get_device_capability(current_device)
    total_memory_bytes = torch.cuda.get_device_properties(current_device).total_memory
    total_memory_gb = total_memory_bytes / (1024 ** 3)

    print(f"CUDA Device Count   : {device_count}")
    print(f"Current Device ID   : {current_device}")
    print(f"Device Name         : {device_name}")
    print(f"Compute Capability  : {device_capability[0]}.{device_capability[1]}")
    print(f"Total Dedicated VRAM: {total_memory_gb:.2f} GB ({total_memory_bytes:,} bytes)")
    print("-" * 70)

    # 4. GPU Tensor Allocation & Arithmetic Execution
    print("Running GPU Tensor Allocation & Arithmetic Verification...")
    start_time = time.perf_counter()

    # Allocate two 2048 x 2048 float32 matrices directly on CUDA
    matrix_dim = 2048
    a = torch.randn(matrix_dim, matrix_dim, dtype=torch.float32, device="cuda")
    b = torch.randn(matrix_dim, matrix_dim, dtype=torch.float32, device="cuda")

    # Matrix multiplication on Tensor Cores
    c = torch.matmul(a, b)

    # Nonlinear element-wise activation + sum reduction
    result = torch.relu(c).sum()

    # Synchronize to guarantee execution has completed on the GPU
    torch.cuda.synchronize()
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    allocated_mem_mb = torch.cuda.memory_allocated(current_device) / (1024 ** 2)
    cached_mem_mb = torch.cuda.memory_reserved(current_device) / (1024 ** 2)

    print(f"Tensor Shape        : {c.shape}")
    print(f"Tensor Device       : {c.device}")
    print(f"Tensor Data Type    : {c.dtype}")
    print(f"Checksum / Sum Value: {result.item():.4f}")
    print(f"Execution Latency   : {elapsed_ms:.2f} ms")
    print(f"Active GPU Memory   : {allocated_mem_mb:.2f} MB")
    print(f"Reserved GPU Memory : {cached_mem_mb:.2f} MB")
    print("=" * 70)
    print("STATUS: VERIFICATION SUCCESSFUL — GPU ACCELERATION ACTIVE & OPERATIONAL")
    print("=" * 70)

if __name__ == "__main__":
    main()
