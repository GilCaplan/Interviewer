#!/usr/bin/env python3
"""
Model Download Script for Docker Build
Downloads Llama 3.2 1B Instruct model for local inference
"""

import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download, login

def download_model():
    """Download Llama model during Docker build"""
    
    # Configuration
    model_name = os.environ.get('LOCAL_MODEL_NAME', 'meta-llama/Llama-3.2-1B-Instruct')
    model_path = os.environ.get('LOCAL_MODEL_PATH', './models/llama-1b-instruct')
    hf_token = os.environ.get('HUGGINGFACE_TOKEN')
    
    print(f"🔄 Starting model download: {model_name}")
    print(f"📁 Target path: {model_path}")
    
    # Create model directory
    Path(model_path).mkdir(parents=True, exist_ok=True)
    
    # Authenticate with HuggingFace if token provided
    if hf_token:
        try:
            login(hf_token)
            print("✅ HuggingFace authentication successful")
        except Exception as e:
            print(f"⚠️ HuggingFace authentication failed: {e}")
            print("Continuing with public access...")
    else:
        print("ℹ️ No HuggingFace token provided - using public access")
    
    # Model files to download
    model_files = [
        "config.json",
        "generation_config.json",
        "model.safetensors",
        "tokenizer.json", 
        "tokenizer_config.json",
        "special_tokens_map.json",
        "tokenizer.model"  # If available
    ]
    
    # Download each file
    downloaded_files = []
    for file_name in model_files:
        try:
            print(f"📥 Downloading {file_name}...")
            downloaded_path = hf_hub_download(
                repo_id=model_name,
                filename=file_name,
                local_dir=model_path,
                local_dir_use_symlinks=False
            )
            downloaded_files.append(file_name)
            print(f"   ✅ Downloaded {file_name}")
            
        except Exception as e:
            print(f"   ⚠️ Could not download {file_name}: {e}")
            # Some files might not exist for all models, continue
            continue
    
    # Verify download
    essential_files = ["config.json", "tokenizer.json", "model.safetensors"]
    missing_essential = [f for f in essential_files if f not in downloaded_files]
    
    if missing_essential:
        print(f"❌ Failed to download essential files: {missing_essential}")
        return False
    else:
        print(f"✅ Model download completed successfully!")
        print(f"📊 Downloaded {len(downloaded_files)} files")
        print(f"💾 Model ready at: {model_path}")
        return True

if __name__ == "__main__":
    try:
        success = download_model()
        if success:
            print("🎉 Model download completed successfully!")
            sys.exit(0)
        else:
            print("❌ Model download failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)