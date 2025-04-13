import re
from typing import Dict, Any, List
from .error_handler import DocumentValidationError, LoanProcessingError

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_application_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate student application data"""
    errors = []
    
    if not data.get('name'):
        errors.append("Name is required")
    
    if not data.get('email') or not validate_email(data['email']):
        errors.append("Valid email is required")
        
    if not data.get('program') or data['program'] not in ["Undergraduate", "Graduate", "PhD"]:
        errors.append("Valid program selection is required")
        
    if errors:
        raise DocumentValidationError(", ".join(errors))
        
    return data

def validate_loan_request(amount: float, student_info: Dict[str, Any]) -> None:
    """Validate loan request data"""
    errors = []
    
    if amount <= 0:
        errors.append("Loan amount must be positive")
        
    if not student_info.get('name'):
        errors.append("Student name is required")
        
    if not student_info.get('program'):
        errors.append("Program information is required")
        
    if errors:
        raise LoanProcessingError(", ".join(errors))

def validate_documents(documents: List[Any], program: str) -> Dict[str, Any]:
    """Validate uploaded documents based on program requirements"""
    required_docs = {
        "Undergraduate": ["transcript", "recommendation", "statement"],
        "Graduate": ["transcript", "recommendations", "statement", "resume"],
        "PhD": ["transcript", "research_proposal", "recommendations", "cv"]
    }
    
    if program not in required_docs:
        raise DocumentValidationError("Invalid program specified")
        
    missing_docs = []
    doc_names = [doc.name.lower() for doc in documents]
    
    for required_doc in required_docs[program]:
        if not any(required_doc.lower() in doc for doc in doc_names):
            missing_docs.append(required_doc)
            
    if missing_docs:
        raise DocumentValidationError(f"Missing required documents: {', '.join(missing_docs)}")
        
    return {
        "valid": True,
        "documents": doc_names
    }