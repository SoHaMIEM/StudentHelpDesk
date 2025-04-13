import google.generativeai as genai
from typing import Dict, Any
from utils.db_manager import DBManager
from utils.error_handler import logger
import os
from utils.policy_loader import PolicyLoader


class BaseAgent:
    def __init__(self):

        policies = PolicyLoader.load_policies()
        
        self.system_prompt = (
            "You are a helpful and professional student counselor with complete knowledge of the university's policies.\n\n"
            f"ADMISSION POLICIES:\n{policies['admission_policy']}\n\n"
            f"LOAN POLICIES:\n{policies['loan_policy']}\n\n"
            f"SHORTLISTING CRITERIA:\n{policies['shortlisting_criteria']}\n\n"
            "\nOnly answer queries related to these policies and student admissions. "
            "If the query is outside this scope (e.g., unrelated topics, personal questions, non-academic matters), "
            "politely decline and ask the student to rephrase the query to focus on admissions."
        )


        # Configure Gemini API
        genai.configure(
            api_key=os.getenv('GEMINI_API_KEY'),
            transport='rest'
        )
        
        # Use text model for general queries
        try:
            generation_config = {
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40,
            }
            
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
            
            self.model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {str(e)}")
            # Fallback to a simple response generator
            self.model = None
            
        self.db = DBManager()
        
    async def generate_response(self, prompt: str) -> str:
        try:
            if self.model:
                full_prompt = f"{self.system_prompt}\n\n{prompt}"
                response = self.model.generate_content(full_prompt)
                if response and hasattr(response, 'text'):
                    return response.text
                elif isinstance(response, list) and len(response) > 0:
                    return response[0].text if hasattr(response[0], 'text') else str(response[0])
                else:
                    return str(response)
            else:
                return "I apologize, but I'm currently unable to generate a detailed response. Please try again later."
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble generating a response at the moment."

        
    def format_message(self, context: Dict[str, Any]) -> str:
        # Override this method in specific agents
        raise NotImplementedError
        
    def log_action(self, action: str, details: Dict[str, Any]) -> None:
        """Log agent actions for tracking and debugging"""
        logger.info(f"Agent action: {action}", extra=details)