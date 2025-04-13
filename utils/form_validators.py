from typing import Dict, Any, Tuple
import re
from decimal import Decimal
from datetime import datetime

def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not email:
        return False, "Email is required"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, ""

def validate_loan_amount(amount: float, program: str) -> Tuple[bool, str]:
    """Validate loan amount based on program limits"""
    program_limits = {
        "Undergraduate": 50000,
        "Graduate": 75000,
        "PhD": 100000
    }
    
    if amount <= 0:
        return False, "Loan amount must be positive"
    if amount > program_limits.get(program, 0):
        return False, f"Maximum loan amount for {program} is ${program_limits[program]:,}"
    return True, ""

def validate_document_upload(files: list, program: str) -> Tuple[bool, str]:
    """Validate uploaded documents"""
    required_docs = {
        "Undergraduate": ["transcript", "recommendation", "statement"],
        "Graduate": ["transcript", "recommendations", "statement", "resume"],
        "PhD": ["transcript", "research_proposal", "recommendations", "cv"]
    }
    
    if not files:
        return False, "No documents uploaded"
        
    doc_names = [f.name.lower() for f in files]
    missing = []
    
    for req in required_docs.get(program, []):
        if not any(req in name for name in doc_names):
            missing.append(req)
            
    if missing:
        return False, f"Missing required documents: {', '.join(missing)}"
    return True, ""

def validate_application_form(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
    """Validate complete application form"""
    errors = {}
    
    # Validate name
    if not data.get('name'):
        errors['name'] = "Name is required"
    elif len(data['name']) < 2:
        errors['name'] = "Name is too short"
    
    # Validate email
    valid_email, email_error = validate_email(data.get('email', ''))
    if not valid_email:
        errors['email'] = email_error
    
    # Validate program selection
    if not data.get('program'):
        errors['program'] = "Program selection is required"
    elif data['program'] not in ["Undergraduate", "Graduate", "PhD"]:
        errors['program'] = "Invalid program selected"
    
    # Validate documents
    valid_docs, doc_error = validate_document_upload(
        data.get('documents', []),
        data.get('program', '')
    )
    if not valid_docs:
        errors['documents'] = doc_error
    
    return len(errors) == 0, errors

def validate_loan_form(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
    """Validate loan application form"""
    errors = {}
    
    # Validate amount
    if not data.get('amount'):
        errors['amount'] = "Loan amount is required"
    else:
        valid_amount, amount_error = validate_loan_amount(
            data['amount'],
            data.get('program', '')
        )
        if not valid_amount:
            errors['amount'] = amount_error
    
    # Validate program
    if not data.get('program'):
        errors['program'] = "Program selection is required"
    
    return len(errors) == 0, errors