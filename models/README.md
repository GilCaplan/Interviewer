# Local LLM Models Directory

This directory stores locally downloaded LLM models for offline inference.

## Supported Models

- **Llama 3.2 1B Instruct** - Primary local model for question generation
- **Model Path**: `./llama-1b-instruct/`
- **Size**: ~1GB
- **Source**: meta-llama/Llama-3.2-1B-Instruct

## Automatic Download

Models are automatically downloaded when:
1. `USE_LOCAL_MODEL=true` in `.env`
2. `HUGGINGFACE_TOKEN` is provided (optional, for gated models)
3. Model is not already present locally

## Manual Download

If you prefer to download manually:

```bash
# Install dependencies
pip install transformers torch huggingface-hub

# Download model (requires HuggingFace account for Llama models)
python -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
model_name = 'meta-llama/Llama-3.2-1B-Instruct'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer.save_pretrained('./llama-1b-instruct')
model.save_pretrained('./llama-1b-instruct')
"
```

## Storage Requirements

- **Llama 3.2 1B**: ~1GB disk space
- **Additional overhead**: ~500MB for tokenizers and config files

## Docker Considerations

When building Docker images:
- Models are downloaded at runtime (first start)
- Consider using Docker volumes for model persistence
- Build time will be longer on first run due to model download