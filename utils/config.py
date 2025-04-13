import os
import json
from pathlib import Path
from dotenv import load_dotenv

class Config:
    # Load environment variables
    load_dotenv()
    
    # API Keys and Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Database Configuration
    CHROMA_PERSISTENCE_DIR = os.getenv('CHROMA_PERSISTENCE_DIR', './data/chroma')
    
    # Program Capacity Configuration
    try:
        MAX_APPLICATIONS_PER_PROGRAM = json.loads(
            os.getenv('MAX_APPLICATIONS_PER_PROGRAM', 
            '{"Undergraduate": 100, "Graduate": 50, "PhD": 20}')
        )
    except json.JSONDecodeError:
        MAX_APPLICATIONS_PER_PROGRAM = {
            "Undergraduate": 100,
            "Graduate": 50,
            "PhD": 20
        }
    
    # Loan Configuration
    LOAN_ANNUAL_BUDGET = float(os.getenv('LOAN_ANNUAL_BUDGET', '1000000'))
    LOAN_INTEREST_RATE = 0.06  # 6% base interest rate
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Document Types
    ALLOWED_DOCUMENT_TYPES = {
        'pdf': ['application/pdf'],
        'doc': ['application/msword'],
        'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        'image': ['image/jpeg', 'image/png']
    }
    
    @classmethod
    def init_directories(cls) -> None:
        """Initialize required directories"""
        Path(cls.CHROMA_PERSISTENCE_DIR).mkdir(parents=True, exist_ok=True)
        
    @classmethod
    def get_program_capacity(cls, program: str) -> int:
        """Get maximum capacity for a program"""
        return cls.MAX_APPLICATIONS_PER_PROGRAM.get(program, 0)
        
    @classmethod
    def is_valid_document_type(cls, mime_type: str) -> bool:
        """Check if document type is allowed"""
        return any(mime_type in types for types in cls.ALLOWED_DOCUMENT_TYPES.values())