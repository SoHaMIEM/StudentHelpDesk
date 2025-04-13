import re
from typing import Dict, Any, List
from .error_handler import DocumentValidationError, LoanProcessingError, logger
import pytesseract
from PIL import Image
from typing import List, Dict, Any
import re
import pandas as pd
import pdf2image
from pathlib import Path
import io
import os


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

def validate_documents(documents: List[Any]) -> Dict[str, Any]:
    """
    Validate documents using OCR and match against student database
    Returns success/failure with extracted and matched information
    """
    try:
        # Configure Tesseract with absolute path
        tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Load student database
        student_df = pd.read_csv(Path(__file__).parent.parent / 'data' / 'student.csv')
        
        # Configure Poppler path
        poppler_path = str(Path(__file__).parent.parent / 'poppler' / 'poppler-21.03.0' / 'Library' / 'bin')
        
        # Patterns for data extraction with improved regex
        patterns = {
            'name': r'(?:Name|Student Name)[:\s]+([A-Za-z\s]{2,50})',
            'dob': r'(?:DOB|Date of Birth)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            'passing_year': r'(?:Passing Year|Year of Passing)[:\s]+(\d{4})',
            'board': r'(?:Board|Examination Board)[:\s]*(CBSE|ICSE|WBCHSE)',
            'aadhar': r'\b[2-9]{1}[0-9]{11}\b'
        }
        
        extracted_data = {
            'name': [],
            'dob': [],
            'passing_year': [],
            'board': [],
            'aadhar': []
        }
        
        logger.info("Starting document processing...")
        
        # Process each document
        for doc in documents:
            text = ""
            logger.info(f"Processing document: {doc.name}")
            
            # Handle PDF files
            if doc.name.lower().endswith('.pdf'):
                try:
                    # Convert PDF to images with improved settings
                    images = pdf2image.convert_from_bytes(
                        doc.read(),
                        dpi=300,  # Higher DPI for better quality
                        fmt='jpeg',  # Use JPEG format for OCR
                        thread_count=2,  # Use multiple threads
                        poppler_path=poppler_path,
                        grayscale=True  # Convert to grayscale immediately
                    )
                    
                    # Process each page
                    for page_num, img in enumerate(images, 1):
                        logger.info(f"Processing PDF page {page_num}")
                        # Apply image preprocessing for better OCR
                        text += pytesseract.image_to_string(
                            img,
                            config='--oem 3 --psm 3 -l eng',  # Use best OCR engine mode
                            timeout=30  # Add timeout to prevent hanging
                        )
                        
                except Exception as e:
                    logger.error(f"PDF processing error: {str(e)}")
                    raise Exception(f"PDF processing failed: {str(e)}")
                    
            # Handle image files
            elif doc.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                image = Image.open(io.BytesIO(doc.read())).convert('L')  # Convert to grayscale
                text += pytesseract.image_to_string(
                    image,
                    config='--oem 3 --psm 3 -l eng'
                )
            else:
                continue
                
            logger.info(f"Extracted text length: {len(text)}")
            
            # Extract information using regex patterns
            for field, pattern in patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if isinstance(matches[0], tuple):
                        extracted_data[field].append(matches[0][1])
                    else:
                        extracted_data[field].append(matches[0])
                logger.info(f"Found {len(matches)} matches for {field}")
                        
        # Clean and standardize extracted data
        cleaned_data = {
            field: list(set(values)) 
            for field, values in extracted_data.items()
            if values
        }
        
        logger.info(f"Cleaned data: {cleaned_data}")
        
        # Match against student database
        matches = []
        for idx, row in student_df.iterrows():
            match_score = 0
            match_details = {}
            
            for field in cleaned_data:
                db_value = str(row[field]).strip()
                for extracted_value in cleaned_data[field]:
                    extracted_clean = str(extracted_value).strip().lower()
                    db_clean = db_value.lower()
                    
                    # Use more flexible matching for dates
                    if field == 'dob':
                        # Normalize date formats
                        extracted_clean = re.sub(r'[-/]', '', extracted_clean)
                        db_clean = re.sub(r'[-/]', '', db_clean)
                    
                    if extracted_clean == db_clean:
                        match_score += 1
                        match_details[field] = extracted_value
                        
            if match_score >= 1:  # At least one field should match
                matches.append({
                    'student_data': row.to_dict(),
                    'matched_fields': match_details,
                    'match_score': match_score
                })
                
        # Determine verification result
        if matches:
            best_match = max(matches, key=lambda x: x['match_score'])
            logger.info(f"Found match with score {best_match['match_score']}")
            return {
                "valid": True,
                "verification_status": "success",
                "matched_student": best_match['student_data'],
                "matched_fields": best_match['matched_fields'],
                "match_score": best_match['match_score'],
                "extracted_data": cleaned_data
            }
        else:
            logger.warning("No matches found in student database")
            return {
                "valid": False,
                "verification_status": "failed",
                "reason": "No matching student records found",
                "extracted_data": cleaned_data
            }
            
    except Exception as e:
        logger.error(f"Document validation error: {str(e)}")
        return {
            "valid": False,
            "verification_status": "error",
            "reason": f"Document processing failed: {str(e)}",
            "error": str(e)
        }