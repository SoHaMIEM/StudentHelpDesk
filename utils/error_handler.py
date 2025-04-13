from typing import Any, Dict, Optional
import logging
from functools import wraps

class AdmissionError(Exception):
    """Base exception class for admission-related errors"""
    pass

class DocumentValidationError(AdmissionError):
    """Raised when document validation fails"""
    pass

class LoanProcessingError(AdmissionError):
    """Raised when loan processing encounters an error"""
    pass

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('admission.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('admission_helpdesk')

logger = setup_logger()

def handle_exceptions(func):
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            return await func(*args, **kwargs)
        except DocumentValidationError as e:
            logger.error(f"Document validation failed: {str(e)}")
            return {"success": False, "error": str(e), "error_type": "document_validation"}
        except LoanProcessingError as e:
            logger.error(f"Loan processing failed: {str(e)}")
            return {"success": False, "error": str(e), "error_type": "loan_processing"}
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            return {"success": False, "error": "An unexpected error occurred", "error_type": "unknown"}
    return wrapper