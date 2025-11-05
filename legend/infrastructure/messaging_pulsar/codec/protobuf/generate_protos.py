#!/usr/bin/env python3
"""
Script to generate Protocol Buffer Python code from .proto definitions
Run this script whenever message.proto is modified
"""

import os
import subprocess
from pathlib import Path


def generate_protos():
    """Generate the Python protobuf code from .proto files"""
    # Get the current directory (where this script is located)
    current_dir = Path(__file__).parent.absolute()
    
    # Find all .proto files in the current directory
    proto_files = list(current_dir.glob("*.proto"))
    
    if not proto_files:
        print("No .proto files found in", current_dir)
        return
    
    # Generate Python code for each .proto file
    for proto_file in proto_files:
        proto_path = str(proto_file)
        print(f"Generating Python code for {proto_path}")
        
        subprocess.run([
            "python", "-m", "grpc_tools.protoc",
            # Path to the .proto files
            f"--proto_path={current_dir}",
            # Output directory for the generated Python code
            f"--python_out={current_dir}",
            # The .proto file to compile
            proto_path
        ], check=True)
        
        print(f"Successfully generated Python code for {proto_path}")

if __name__ == "__main__":
    generate_protos() 