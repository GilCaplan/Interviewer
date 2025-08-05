"""
Local LLM Service for Llama 3.2 1B Instruct
Handles model downloading, device detection, and inference
"""

import os
import json
import torch
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from huggingface_hub import hf_hub_download, login, HfApi
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    pipeline,
    BitsAndBytesConfig
)

class DeviceDetector:
    """Detects and manages optimal device for inference"""
    
    @staticmethod
    def get_optimal_device() -> Tuple[str, Dict[str, Any]]:
        """
        Detect optimal device and return device info
        Returns: (device_name, device_config)
        """
        device_config = {}
        
        # Check for CUDA (NVIDIA GPU)
        if torch.cuda.is_available():
            device = "cuda"
            device_config = {
                "device": device,
                "gpu_count": torch.cuda.device_count(),
                "gpu_name": torch.cuda.get_device_name(0),
                "memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
                "torch_dtype": "float16"  # Store as string for JSON serialization
            }
            print(f"🚀 Using CUDA GPU: {device_config['gpu_name']}")
            return device, device_config
        
        # Check for MPS (Apple Silicon)
        elif torch.backends.mps.is_available():
            device = "mps" 
            device_config = {
                "device": device,
                "torch_dtype": "float32",  # Store as string for JSON serialization
                "low_cpu_mem_usage": True
            }
            print("🍎 Using Apple MPS (Metal Performance Shaders)")
            return device, device_config
        
        # Fallback to CPU
        else:
            device = "cpu"
            device_config = {
                "device": device,
                "torch_dtype": "float32",  # Store as string for JSON serialization
                "low_cpu_mem_usage": True
            }
            print("💻 Using CPU (consider GPU for better performance)")
            return device, device_config

class LocalLLMService:
    """Service for managing local Llama model inference"""
    
    def __init__(self):
        self.model_name = os.environ.get('LOCAL_MODEL_NAME', 'meta-llama/Llama-3.2-1B-Instruct')
        self.model_path = os.environ.get('LOCAL_MODEL_PATH', './models/llama-1b-instruct')
        self.hf_token = os.environ.get('HUGGINGFACE_TOKEN')
        self.use_local_model = os.environ.get('USE_LOCAL_MODEL', 'true').lower() == 'true'
        
        self.device, self.device_config = DeviceDetector.get_optimal_device()
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.is_initialized = False
        
        # Models directory will be created when needed (in download_model or initialize)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def is_available(self) -> bool:
        """Check if local LLM is available and enabled"""
        return self.use_local_model and self._is_model_downloaded()
    
    def _is_model_downloaded(self) -> bool:
        """Check if model is already downloaded"""
        model_path = Path(self.model_path)
        return (
            model_path.exists() and 
            (model_path / "config.json").exists() and
            (model_path / "tokenizer.json").exists()
        )
    
    def _authenticate_huggingface(self) -> bool:
        """Authenticate with HuggingFace if token is provided"""
        if self.hf_token:
            try:
                login(self.hf_token)
                self.logger.info("✅ HuggingFace authentication successful")
                return True
            except Exception as e:
                self.logger.warning(f"⚠️ HuggingFace authentication failed: {e}")
                return False
        else:
            self.logger.info("ℹ️ No HuggingFace token provided - using public models only")
            return True
    
    def download_model(self) -> bool:
        """Download Llama model from HuggingFace"""
        if self._is_model_downloaded():
            self.logger.info(f"✅ Model already downloaded at {self.model_path}")
            return True
        
        if not self._authenticate_huggingface():
            return False
        
        try:
            # Create models directory when actually downloading
            Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"📥 Downloading {self.model_name}...")
            self.logger.info("This may take several minutes for the first download...")
            
            # Download model files
            model_files = [
                "config.json",
                "generation_config.json", 
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
                "special_tokens_map.json"
            ]
            
            for file in model_files:
                try:
                    downloaded_path = hf_hub_download(
                        repo_id=self.model_name,
                        filename=file,
                        local_dir=self.model_path,
                        local_dir_use_symlinks=False
                    )
                    self.logger.info(f"   ✓ Downloaded {file}")
                except Exception as e:
                    # Some files might not exist, continue
                    self.logger.debug(f"   ⚠️ Could not download {file}: {e}")
            
            # Verify download
            if self._is_model_downloaded():
                self.logger.info(f"✅ Model successfully downloaded to {self.model_path}")
                return True
            else:
                self.logger.error("❌ Model download verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to download model: {e}")
            return False
    
    def initialize_model(self) -> bool:
        """Initialize the model and tokenizer"""
        if self.is_initialized:
            return True
        
        if not self.download_model():
            return False
        
        try:
            self.logger.info(f"🔄 Loading model on {self.device}...")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            # Ensure pad token exists
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Configure model loading based on device
            # Convert string torch_dtype back to actual torch.dtype for model loading
            torch_dtype_str = self.device_config["torch_dtype"]
            if torch_dtype_str == "float16":
                torch_dtype_obj = torch.float16
            elif torch_dtype_str == "float32":
                torch_dtype_obj = torch.float32
            else:
                torch_dtype_obj = torch.float32  # Default fallback
            
            model_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch_dtype_obj,
                "low_cpu_mem_usage": self.device_config.get("low_cpu_mem_usage", False)
            }
            
            # Add device-specific optimizations
            if self.device == "cuda":
                # Use 4-bit quantization for GPU to save memory
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                model_kwargs["quantization_config"] = quantization_config
                model_kwargs["device_map"] = "auto"
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                **model_kwargs
            )
            
            # Move to device if not using device_map
            if "device_map" not in model_kwargs:
                self.model = self.model.to(self.device)
            
            # Create pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                torch_dtype=torch_dtype_obj
            )
            
            self.is_initialized = True
            self.logger.info(f"✅ Model initialized successfully on {self.device}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize model: {e}")
            return False
    
    def generate_question(self, question_type: str, subject: str, context: str = "") -> Dict[str, Any]:
        """Generate a question using local Llama model"""
        if not self.initialize_model():
            return self._get_fallback_response(question_type, subject)
        
        try:
            prompt = self._build_prompt(question_type, subject, context)
            
            # Generate response
            response = self.pipeline(
                prompt,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
            
            generated_text = response[0]["generated_text"]
            # Extract only the new generated part
            generated_content = generated_text[len(prompt):].strip()
            
            return self._parse_llama_response(generated_content, question_type, subject)
            
        except Exception as e:
            self.logger.error(f"Error generating with local model: {e}")
            return self._get_fallback_response(question_type, subject)
    
    def chat_with_context(self, message: str, context: str = "") -> str:
        """Generate chat response using local model"""
        if not self.initialize_model():
            return "I apologize, but I'm currently unable to provide assistance. Please try again later."
        
        try:
            prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful AI assistant for an interview preparation platform. You help users create better interview questions and provide constructive feedback.

Context: {context}

<|eot_id|><|start_header_id|>user<|end_header_id|>

{message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
            
            response = self.pipeline(
                prompt,
                max_new_tokens=256,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
            
            generated_text = response[0]["generated_text"]
            generated_content = generated_text[len(prompt):].strip()
            
            # Clean up response
            if "<|eot_id|>" in generated_content:
                generated_content = generated_content.split("<|eot_id|>")[0].strip()
            
            return generated_content
            
        except Exception as e:
            self.logger.error(f"Error in chat generation: {e}")
            return "I apologize, but I encountered an error. Please try again."
    
    def _build_prompt(self, question_type: str, subject: str, context: str = "") -> str:
        """Build a detailed prompt for Llama based on question type"""
        
        base_context = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an expert interview question generator. Create high-quality {question_type} questions for {subject} interviews.

Requirements:
- Generate realistic, professional interview questions
- Include proper formatting for the question type
- Provide sample answers and grading criteria
- Make questions challenging but fair

{context}

<|eot_id|><|start_header_id|>user<|end_header_id|>

Generate a {question_type} question about {subject}. Format your response as JSON with these fields:
- question_text: The main question
- sample_answer: A good example answer
- grading_criteria: How to evaluate responses
- difficulty: easy/medium/hard
- time_estimate: estimated time in minutes

For multiple choice questions, also include:
- options: Array of 4 choices (A, B, C, D)
- correct_answer: The correct option letter

<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        return base_context
    
    def _parse_llama_response(self, response_text: str, question_type: str, subject: str) -> Dict[str, Any]:
        """Parse Llama's response and return structured data"""
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed_data = json.loads(json_text)
                
                # Ensure required fields exist
                result = {
                    "question_text": parsed_data.get("question_text", f"Sample {question_type} question about {subject}"),
                    "sample_answer": parsed_data.get("sample_answer", "Sample answer would go here."),
                    "grading_criteria": parsed_data.get("grading_criteria", "Evaluate based on accuracy and completeness."),
                    "difficulty": parsed_data.get("difficulty", "medium"),
                    "time_estimate": parsed_data.get("time_estimate", 5),
                    "generated_by": "llama-local",
                    "model_name": self.model_name
                }
                
                # Add multiple choice specific fields
                if question_type == "multiple_choice":
                    result["options"] = parsed_data.get("options", ["Option A", "Option B", "Option C", "Option D"])
                    result["correct_answer"] = parsed_data.get("correct_answer", "A")
                
                return result
            
        except Exception as e:
            self.logger.error(f"Error parsing Llama response: {e}")
        
        # Fallback to parsed text response
        return {
            "question_text": f"Generated question about {subject}: {response_text[:200]}...",
            "sample_answer": "This would depend on the specific requirements.",
            "grading_criteria": "Evaluate based on technical accuracy and explanation quality.",
            "difficulty": "medium", 
            "time_estimate": 5,
            "generated_by": "llama-local",
            "model_name": self.model_name
        }
    
    def _get_fallback_response(self, question_type: str, subject: str) -> Dict[str, Any]:
        """Generate fallback response when model is unavailable"""
        return {
            "question_text": f"Sample {question_type} question about {subject} (Local model unavailable)",
            "sample_answer": "This is a fallback response. Local model is not available.",
            "grading_criteria": "Standard evaluation criteria would apply.",
            "difficulty": "medium",
            "time_estimate": 5,
            "generated_by": "fallback",
            "model_name": "unavailable"
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model setup"""
        # Convert torch.dtype to string for JSON serialization
        device_config_json = {}
        for key, value in self.device_config.items():
            # Handle torch.dtype objects - they have a __str__ method but aren't JSON serializable
            if str(type(value)).startswith("<class 'torch."):
                device_config_json[key] = str(value)
            elif hasattr(value, 'dtype'):  # Handle numpy arrays or tensors
                device_config_json[key] = str(value)
            else:
                device_config_json[key] = value
        
        return {
            "model_name": self.model_name,
            "model_path": self.model_path,
            "device": self.device,
            "device_config": device_config_json,
            "is_available": self.is_available(),
            "is_initialized": self.is_initialized,
            "model_downloaded": self._is_model_downloaded(),
            "use_local_model": self.use_local_model
        }

# Global instance
local_llm_service = LocalLLMService()