"""
Setup script for Graph Neural Network dependencies
Installs PyTorch Geometric for graph-based learning
"""

import subprocess
import sys
import torch

def install_pytorch_geometric():
    """Install PyTorch Geometric with CUDA support"""
    
    print("Installing PyTorch Geometric...")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    # Get CUDA version
    if torch.cuda.is_available():
        cuda_version = torch.version.cuda
        print(f"CUDA version: {cuda_version}")
        
        # Install with CUDA support
        packages = [
            "torch-geometric",
            "torch-scatter",
            "torch-sparse",
            "torch-cluster",
            "torch-spline-conv"
        ]
        
        for package in packages:
            print(f"\nInstalling {package}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package,
                "-f", "https://data.pyg.org/whl/torch-2.9.0+cu126.html"
            ])
    else:
        # CPU-only installation
        print("Installing CPU-only version...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "torch-geometric"
        ])
    
    print("\n✓ PyTorch Geometric installed successfully!")


if __name__ == "__main__":
    try:
        install_pytorch_geometric()
    except Exception as e:
        print(f"\n✗ Installation failed: {e}")
        print("\nTry manual installation:")
        print("pip install torch-geometric")
        sys.exit(1)
