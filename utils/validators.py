import re
from typing import Dict, Any, List
from .error_handler import DocumentValidationError, LoanProcessingError, logger
import pytesseract
from PIL import Image
import pandas as pd
import pdf2image
from pathlib import Path
import io
import os
import json
import google.generativeai as genai
from .config import Config

# Configure Gemini
genai.configure(api_key=Config.GEMINI_API_KEY)

def get_gemini_model():
    """Get configured Gemini model instance"""
    generation_config = {
        'temperature': 0.1,  # Low temperature for factual extraction
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
    
    return genai.GenerativeModel(
        model_name='gemini-2.0-flash',
        generation_config=generation_config,
        safety_settings=safety_settings
    )

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
    Validate documents using OCR and Gemini AI for information extraction.
    Documents are valid only if all required fields are present in the extracted data.
    """
    try:
        # Configure Tesseract with absolute path
        tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Load student database
        student_df = pd.read_csv(Path(__file__).parent.parent / 'data' / 'student.csv')
        
        # Configure Poppler path
        poppler_path = str(Path(__file__).parent.parent / 'poppler' / 'poppler-21.03.0' / 'Library' / 'bin')
        
        model = get_gemini_model()
        
        # Initialize extracted data structure
        extracted_data = {
            'name': [],
            'dob': [],
            'passing_year': [],
            'board': [],
            'gender': []
        }
        
        logger.info("Starting document processing...")
        
        # Process each document
        for doc in documents:
            text = ""
            logger.info(f"Processing document: {doc.name}")
            
            # Handle PDF files
            if doc.name.lower().endswith('.pdf'):
                try:
                    images = pdf2image.convert_from_bytes(
                        doc.read(),
                        dpi=300,
                        fmt='jpeg',
                        thread_count=2,
                        poppler_path=poppler_path,
                        grayscale=True
                    )
                    
                    for page_num, img in enumerate(images, 1):
                        logger.info(f"Processing PDF page {page_num}")
                        text += pytesseract.image_to_string(
                            img,
                            config='--oem 3 --psm 3 -l eng',
                            timeout=30
                        )
                        
                except Exception as e:
                    logger.error(f"PDF processing error: {str(e)}")
                    raise Exception(f"PDF processing failed: {str(e)}")
                    
            elif doc.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                image = Image.open(io.BytesIO(doc.read())).convert('L')
                text += pytesseract.image_to_string(
                    image,
                    config='--oem 3 --psm 3 -l eng'
                )
            else:
                continue
                
            logger.info(f"Extracted text length: {len(text)}")
            
            # Clean up OCR text
            text = ' '.join(text.split())  # Remove extra whitespace
            text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII characters
            
            # Use Gemini to extract information
            prompt = f"""You are an expert document analyzer. Extract specific information from the following document text.

Rules:
1. Return ONLY a valid JSON object, no other text or explanation
2. For missing or unclear information, use null (not the string "null")
3. Format dates as YYYY-MM-DD if possible
4. Names should be in proper case
5. Board must be one of: CBSE, ICSE, WBCHSE
6. Gender must be one of: Male, Female
7. Passing year must be a 4-digit year between 1990 and 2025

The response must be in this exact format:
{{
    "name": null,
    "dob": null,
    "passing_year": null,
    "board": null,
    "gender": null
}}

Document text to analyze:
{text}"""
            
            try:
                response = model.generate_content(prompt)
                # Log raw response for debugging
                logger.debug(f"Raw Gemini response before cleanup: {response.text}")
                
                # Clean the response text to ensure it's valid JSON
                response_text = response.text.strip()
                # Remove any markdown code block markers if present
                response_text = re.sub(r'^```json\s*|\s*```$', '', response_text)
                logger.debug(f"Cleaned response text: {response_text}")
                
                # Parse JSON response
                extracted = json.loads(response_text)
                
                # Add extracted values to our collection
                for field in extracted_data:
                    if extracted.get(field) is not None and extracted[field] != "null":
                        extracted_data[field].append(extracted[field])
                        
                logger.info(f"Gemini extracted: {extracted}")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error from Gemini response: {str(e)}")
                logger.error(f"Response that failed parsing: {response_text}")
                continue
            except Exception as e:
                logger.error(f"Gemini extraction error: {str(e)}")
                continue

        # Clean and standardize extracted data
        cleaned_data = {}
        for field, values in extracted_data.items():
            # Only include fields that have non-empty values
            unique_values = list(set(v for v in values if v))
            if unique_values:
                cleaned_data[field] = unique_values
        
        logger.info(f"Cleaned data: {cleaned_data}")
        
        # Check if all required fields are present and have values
        required_fields = {'name', 'dob', 'passing_year', 'board', 'gender'}
        missing_fields = required_fields - set(cleaned_data.keys())
        
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return {
                "valid": False,
                "verification_status": "failed",
                "reason": f"Missing required fields: {', '.join(missing_fields)}",
                "extracted_data": cleaned_data
            }
        
        # All required fields are present with values
        logger.info("All required fields found in documents")
        return {
            "valid": True,
            "verification_status": "success",
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