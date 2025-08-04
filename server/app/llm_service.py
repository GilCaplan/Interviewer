import google.generativeai as genai
import os
import json
import random
import time
from datetime import datetime, timedelta
from .config import Config
from .rate_limiter import rate_limit
from .local_llm_service import local_llm_service

# Rate limiting for free tier
class RateLimiter:
    def __init__(self):
        self.requests_per_minute = int(os.environ.get('LLM_REQUESTS_PER_MINUTE', '15'))
        self.requests_per_day = int(os.environ.get('LLM_REQUESTS_PER_DAY', '1500'))
        self.minute_requests = []
        self.daily_requests = []
    
    def can_make_request(self):
        now = datetime.now()
        
        # Clean old requests
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        self.minute_requests = [req for req in self.minute_requests if req > minute_ago]
        self.daily_requests = [req for req in self.daily_requests if req > day_ago]
        
        # Check limits
        if len(self.minute_requests) >= self.requests_per_minute:
            return False, "Rate limit: Too many requests per minute"
        
        if len(self.daily_requests) >= self.requests_per_day:
            return False, "Rate limit: Daily quota exceeded"
        
        return True, None
    
    def record_request(self):
        now = datetime.now()
        self.minute_requests.append(now)
        self.daily_requests.append(now)

# Global rate limiter instance
rate_limiter = RateLimiter()

# Configure Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')  # Free tier model
else:
    model = None

class LLMService:
    @staticmethod
    def is_available():
        """Check if any LLM service is available (Gemini or Local)"""
        return (GEMINI_API_KEY is not None and model is not None) or local_llm_service.is_available()
    
    @staticmethod
    def get_llm_status():
        """Get detailed status of all LLM services"""
        return {
            "gemini": {
                "available": GEMINI_API_KEY is not None and model is not None,
                "has_api_key": GEMINI_API_KEY is not None
            },
            "local_llm": local_llm_service.get_model_info(),
            "fallback": "mock_responses"
        }
    
    @staticmethod
    def generate_question(subject="general", context="", question_type="open_ended", question_number=1):
        """
        Generate a question using best available LLM service:
        1. Gemini API (if available and not rate limited)
        2. Local Llama model (if available)
        3. Mock responses (fallback)
        """
        # Try Gemini first if available
        if GEMINI_API_KEY and model:
            # Check rate limits
            can_request, error_msg = rate_limiter.can_make_request()
            if can_request:
                try:
                    # Record the request
                    rate_limiter.record_request()
                    
                    # Build the prompt based on question type and context
                    prompt = LLMService._build_prompt(subject, context, question_type, question_number)
                    
                    # Generate with Gemini (free tier)
                    response = model.generate_content(prompt)
                    
                    # Parse the response
                    result = LLMService._parse_gemini_response(response.text, question_type, subject)
                    result["rate_limited"] = False
                    result["llm_source"] = "gemini"
                    return result
                    
                except Exception as e:
                    print(f"Error with Gemini API: {e}")
                    # Continue to next fallback
            else:
                print(f"Gemini rate limit exceeded: {error_msg}")
                # Continue to next fallback
        
        # Try Local Llama model
        if local_llm_service.is_available():
            try:
                result = local_llm_service.generate_question(question_type, subject, context)
                result["llm_source"] = "local_llama"
                return result
            except Exception as e:
                print(f"Error with local LLM: {e}")
                # Continue to fallback
        
        # Final fallback to mock
        result = LLMService._mock_generate_question(subject, context, question_type, question_number)
        result["llm_source"] = "mock"
        return result
        
    
    @staticmethod
    def _build_prompt(subject, context, question_type, question_number):
        """Build a detailed prompt for Gemini based on question type"""
        
        base_prompt = f"""
        You are an expert interview question generator. Create interview question {question_number} for the subject: {subject}.
        
        Context: {context}
        Question Type: {question_type}
        
        """
        
        if question_type == "multiple_choice":
            prompt = base_prompt + """
            Generate a multiple choice question with exactly 4 options (A, B, C, D).
            Provide the correct answer and a brief explanation.
            
            Return your response in this exact JSON format:
            {
                "question_text": "Your question here",
                "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
                "correct_answer": "A. Option 1",
                "explanation": "Brief explanation why this is correct",
                "difficulty": "medium",
                "hints": ["Hint 1", "Hint 2"]
            }
            """
        
        elif question_type == "coding":
            prompt = base_prompt + """
            Generate a coding question with starter code, solution, and test cases.
            Choose an appropriate programming language based on the subject.
            
            Return your response in this exact JSON format:
            {
                "question_text": "Your coding problem description",
                "language": "python",
                "starter_code": "# Your starter code here\\ndef solution():\\n    pass",
                "solution": "# Complete solution here",
                "test_cases": [
                    {"input": "example input", "expected": "expected output"},
                    {"input": "test case 2", "expected": "expected output 2"}
                ],
                "difficulty": "medium",
                "hints": ["Think about the algorithm", "Consider edge cases"]
            }
            """
        
        elif question_type == "true_false":
            prompt = base_prompt + """
            Generate a true/false question with an explanation.
            
            Return your response in this exact JSON format:
            {
                "question_text": "Your true/false statement",
                "correct_answer": true,
                "explanation": "Explanation of why this is true/false",
                "difficulty": "medium",
                "hints": ["Consider the fundamentals", "Think about common misconceptions"]
            }
            """
        
        elif question_type == "short_answer":
            prompt = base_prompt + """
            Generate a short answer question with expected keywords and sample answers.
            
            Return your response in this exact JSON format:
            {
                "question_text": "Your short answer question",
                "expected_keywords": ["keyword1", "keyword2", "keyword3"],
                "sample_answers": ["Sample answer 1", "Sample answer 2"],
                "max_words": 50,
                "difficulty": "medium",
                "hints": ["Focus on key concepts", "Be concise but complete"]
            }
            """
        
        else:  # open_ended
            prompt = base_prompt + """
            Generate an open-ended interview question with grading criteria and sample answer.
            
            Return your response in this exact JSON format:
            {
                "question_text": "Your open-ended question",
                "sample_answer": "A comprehensive sample answer",
                "grading_criteria": ["Criterion 1", "Criterion 2", "Criterion 3"],
                "difficulty": "medium",
                "hints": ["Think about real-world applications", "Consider multiple perspectives"]
            }
            """
        
        return prompt
    
    @staticmethod
    def _parse_gemini_response(response_text, question_type, subject):
        """Parse Gemini's response and return structured data"""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group())
                
                # Add standard fields
                json_data.update({
                    "type": question_type,
                    "generated_by": "gemini",
                    "timestamp": datetime.utcnow().isoformat(),
                    "subject": subject
                })
                
                return json_data
            else:
                # If no JSON found, create a basic structure
                return {
                    "question_text": response_text[:500],  # Truncate if too long
                    "type": question_type,
                    "generated_by": "gemini",
                    "timestamp": datetime.utcnow().isoformat(),
                    "subject": subject,
                    "difficulty": "medium"
                }
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error parsing Gemini response: {e}")
            # Fallback to mock
            return LLMService._mock_generate_question(subject, "", question_type, 1)
    
    @staticmethod
    def _mock_generate_question(subject="general", context="", question_type="open_ended", question_number=1):
        """Fallback mock question generator"""
        
        # Subject-specific question banks
        subject_questions = {
            "python": [
                "Explain the difference between lists and tuples in Python",
                "How does Python's garbage collection work?",
                "What are Python decorators and how do you use them?",
                "Implement a function to find duplicates in a list"
            ],
            "javascript": [
                "Explain JavaScript closures with an example",
                "What is the difference between == and === in JavaScript?",
                "How do you handle asynchronous operations in JavaScript?",
                "Implement a debounce function"
            ],
            "algorithms": [
                "Implement a binary search algorithm",
                "Explain the time complexity of quicksort",
                "How would you detect a cycle in a linked list?",
                "Design an algorithm to find the shortest path in a graph"
            ],
            "system_design": [
                "Design a URL shortening service like bit.ly",
                "How would you design a chat application?",
                "Explain how you would scale a web application",
                "Design a caching system for a high-traffic website"
            ]
        }
        
        # Override subject from context if specific subjects are mentioned
        context_lower = context.lower()
        for subject_key in subject_questions.keys():
            if subject_key in context_lower:
                subject = subject_key
                break
        
        questions = subject_questions.get(subject.lower(), subject_questions["python"])
        base_question = random.choice(questions)
        
        # Add context awareness
        if context:
            if "beginner" in context.lower():
                base_question = "Beginner level: " + base_question
            elif "advanced" in context.lower():
                base_question = "Advanced: " + base_question
            if f"question {question_number}" in context.lower():
                base_question = f"Question {question_number}: " + base_question
        
        # Generate type-specific content
        question_data = {
            "question_text": base_question,
            "difficulty": random.choice(["easy", "medium", "hard"]),
            "type": question_type,
            "generated_by": "mock_llm",
            "timestamp": datetime.utcnow().isoformat(),
            "subject": subject
        }
        
        # Add type-specific fields
        if question_type == "multiple_choice":
            if subject.lower() == "python":
                question_data.update({
                    "options": ["A. True", "B. False", "C. It depends", "D. None of the above"],
                    "correct_answer": "A. True",
                    "explanation": "This is the correct answer because...",
                    "hints": ["Think about Python's design principles", "Consider the context"]
                })
            else:
                question_data.update({
                    "options": ["A. Option A", "B. Option B", "C. Option C", "D. Option D"],
                    "correct_answer": "A. Option A",
                    "explanation": "This is the correct answer because...",
                    "hints": ["Consider the fundamentals", "Think step by step"]
                })
        
        elif question_type == "true_false":
            question_data.update({
                "correct_answer": random.choice([True, False]),
                "explanation": "This statement is correct/incorrect because...",
                "hints": ["Consider common misconceptions", "Think about edge cases"]
            })
        
        elif question_type == "coding":
            lang = subject.lower() if subject.lower() in ["python", "javascript", "java"] else "python"
            question_data.update({
                "language": lang,
                "starter_code": f"# Write your solution here\ndef solution():\n    pass",
                "solution": f"# Sample solution\ndef solution():\n    return 'implemented'",
                "test_cases": [
                    {"input": "example", "expected": "output"},
                    {"input": "test", "expected": "result"}
                ],
                "hints": ["Think about the algorithm", "Consider edge cases", "Optimize for time complexity"]
            })
        
        elif question_type == "short_answer":
            question_data.update({
                "expected_keywords": ["key", "concept", "important", subject.lower()],
                "sample_answers": ["Sample answer focusing on key concepts", "Alternative approach explanation"],
                "max_words": 50,
                "hints": ["Be concise but complete", "Focus on key concepts"]
            })
        
        else:  # open_ended
            question_data.update({
                "sample_answer": f"A comprehensive answer would cover the fundamental concepts of {subject}, including practical applications and considerations for different scenarios.",
                "grading_criteria": ["Demonstrates understanding of core concepts", "Provides practical examples", "Shows analytical thinking"],
                "hints": ["Think about real-world applications", "Consider multiple perspectives", "Provide specific examples"]
            })
        
        return question_data

    @staticmethod
    def generate_chat_response(message, context=""):
        """Generate a chat response using best available LLM service"""
        # Try Gemini first if available
        if GEMINI_API_KEY and model:
            # Check rate limits
            can_request, error_msg = rate_limiter.can_make_request()
            if can_request:
                try:
                    # Record the request
                    rate_limiter.record_request()
                    
                    prompt = f"""
                    You are an expert interview preparation assistant. Help the user with their question or request.
                    Keep responses concise and focused on interview preparation.
                    
                    Context: {context}
                    User message: {message}
                    
                    Provide a helpful, practical response focused on interview preparation and question design.
                    """
                    
                    response = model.generate_content(prompt)
                    
                    return {
                        "response": response.text,
                        "generated_by": "gemini",
                        "timestamp": datetime.utcnow().isoformat(),
                        "rate_limited": False,
                        "llm_source": "gemini"
                    }
                    
                except Exception as e:
                    print(f"Error with Gemini chat: {e}")
                    # Continue to next fallback
            else:
                print(f"Gemini rate limit exceeded: {error_msg}")
                # Continue to next fallback
        
        # Try Local Llama model
        if local_llm_service.is_available():
            try:
                response_text = local_llm_service.chat_with_context(message, context)
                return {
                    "response": response_text,
                    "generated_by": "llama-local",
                    "timestamp": datetime.utcnow().isoformat(),
                    "llm_source": "local_llama"
                }
            except Exception as e:
                print(f"Error with local LLM chat: {e}")
                # Continue to fallback
        
        # Final fallback to mock
        return {
            "response": "I'm a mock LLM assistant. I can help you with interview questions and suggestions. What would you like to work on?",
            "generated_by": "mock_llm",
            "timestamp": datetime.utcnow().isoformat(),
            "llm_source": "mock"
        }
        
    
    @staticmethod
    def generate_mock_response(subject="general", question_type="open_ended", context=""):
        """Generate a mock response for testing purposes"""
        return LLMService._mock_generate_question(subject, context, question_type, 1)["question_text"]
    
    @staticmethod
    def generate_field_suggestion(field="question_text", question_type="open_ended", context=""):
        """Generate field-specific suggestions for testing"""
        suggestions = {
            "question_text": "What is the main concept you want candidates to understand? Consider making it clear, specific, and aligned with the learning objectives.",
            "options": "Consider providing diverse and plausible options that test different aspects of knowledge while maintaining one clearly correct answer.",
            "hints": "Think about what clues would help without giving away the answer. Progressive hints work well for guiding candidates.",
            "explanation": "Explain why this answer is correct and others are not. Include reasoning that helps candidates learn from their mistakes."
        }
        
        base_suggestion = suggestions.get(field, "Consider the context and requirements for this field and ensure it aligns with best practices.")
        
        if context:
            return f"For {question_type} questions: {base_suggestion}. Context: {context}. Make sure this enhances the overall question quality."
        else:
            return f"For {question_type} questions: {base_suggestion}. Ensure this contributes to a comprehensive assessment."