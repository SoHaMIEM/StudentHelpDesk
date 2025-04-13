from .base_agent import BaseAgent
from typing import Dict, Any, List
from utils.validators import validate_documents
from utils.error_handler import DocumentValidationError
import mimetypes
from datetime import datetime
import os
from pathlib import Path
import re

class DocumentChecker(BaseAgent):
    def __init__(self):
        super().__init__()
        # Set up Poppler path to the correct binary location
        self.poppler_path = str(Path(__file__).parent.parent / 'poppler' / 'poppler-21.03.0' / 'Library' / 'bin')
        os.environ["PATH"] = os.environ["PATH"] + os.pathsep + self.poppler_path
        
    async def verify_documents(self, documents: List[Any]) -> Dict[str, Any]:
        """Verify submitted documents"""
        try:
            # Configure environment for PDF processing
            os.environ["PATH"] = os.environ["PATH"] + os.pathsep + self.poppler_path
            
            # Validate documents using OCR and match against student database
            verification_result = validate_documents(documents)
            
            if verification_result["valid"]:
                # Store the verification result in database
                self.db.store_document_verification(
                    f"verification_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    {
                        "type": "ocr_verification",
                        "verification_result": verification_result,
                        "verified": True
                    }
                )
                
                self.log_action("verify_documents", {
                    "num_documents": len(documents),
                    "verification_status": "success",
                    "match_score": verification_result.get("match_score", 0)
                })
                
            return verification_result
            
        except Exception as e:
            self.log_action("document_verification_error", {"error": str(e)})
            return {
                "valid": False,
                "verification_status": "error",
                "reason": f"Document verification failed: {str(e)}",
                "error": str(e)
            }
            
    async def analyze_document_content(self, document: Any) -> Dict[str, Any]:
        """Analyze document content using AI"""
        try:
            content_prompt = f"Analyze the content of this document: {document.name}"
            analysis = await self.generate_response(content_prompt)
            
            result = {
                "document": document.name,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store analysis result
            self.db.store_document_verification(
                f"analysis_{document.name}",
                {"verification_result": result}
            )
            
            return result
            
        except Exception as e:
            self.log_action("content_analysis_error", {"error": str(e)})
            return {
                "error": "Failed to analyze document content",
                "details": str(e)
            }

    def _extract_fields(self, text: str, doc_type: str) -> Dict[str, str]:
        """Extract required fields based on document type"""
        fields = {}
        
        if doc_type == "marksheet":
            # Extract name (improved pattern matching with newline handling)
            name_matches = re.finditer(r'name[:\s]+([A-Z][A-Za-z\s]+?)(?=\n|$|roll|class|of\s|registration)', text, re.IGNORECASE)
            names = [match.group(1).strip() for match in name_matches if match.group(1)]
            if not names:
                # Try alternate pattern for names without 'name:' prefix
                name_matches = re.finditer(r'([A-Z][A-Za-z\s]+?)(?=\n|$|roll|class|of\s|registration)', text)
                names = [match.group(1).strip() for match in name_matches if match.group(1)]
            fields["name"] = names[0] if names else None

            # Extract DOB (improved pattern)
            dob_matches = re.finditer(r'(?:date\s+of\s+birth|dob|born\s+on)[:\s]+([\d]{2}[-/][\d]{2}[-/][\d]{4}|[\d]{4}[-/][\d]{2}[-/][\d]{2})', text, re.IGNORECASE)
            dobs = [match.group(1) for match in dob_matches]
            fields["dob"] = dobs[0] if dobs else None

            # Extract passing year (improved pattern)
            year_matches = re.finditer(r'(?:pass|examination|academic\s+year|year)[:\s]+(20\d{2})', text, re.IGNORECASE)
            years = [match.group(1) for match in year_matches]
            fields["passing_year"] = years[0] if years else None

            # Extract board (improved pattern)
            board_matches = re.finditer(r'(?:board|council|issued\s+by)[:\s]+((?:CBSE|ICSE|ISC|STATE|BOARD|COUNCIL)[\s\w]+?)(?=\n|$|roll|class)', text, re.IGNORECASE)
            boards = [match.group(1).strip() for match in board_matches]
            fields["board"] = boards[0] if boards else None

            # Extract total marks (improved pattern)
            marks_matches = re.finditer(r'total[:\s]+(\d+)|aggregate[:\s]+(\d+(?:\.\d+)?)', text, re.IGNORECASE)
            marks = [match.group(1) or match.group(2) for match in marks_matches]
            fields["total_marks"] = marks[0] if marks else None

        elif doc_type == "id":
            # Extract name (with improved newline handling)
            name_matches = re.finditer(r'name[:\s]+([A-Z][A-Za-z\s]+?)(?=\n|$|male|female|sex|gender|father|mother|dob)', text, re.IGNORECASE)
            names = [match.group(1).strip() for match in name_matches if match.group(1)]
            fields["name"] = names[0] if names else None

            # Extract DOB (improved pattern)
            dob_matches = re.finditer(r'(?:date\s+of\s+birth|dob|born\s+on)[:\s]+([\d]{2}[-/][\d]{2}[-/][\d]{4}|[\d]{4}[-/][\d]{2}[-/][\d]{2})', text, re.IGNORECASE)
            dobs = [match.group(1) for match in dob_matches]
            fields["dob"] = dobs[0] if dobs else None

            # Extract Aadhar (improved pattern)
            aadhar_matches = re.finditer(r'(\d{4}[\s-]*\d{4}[\s-]*\d{4})', text)
            aadhars = [match.group(1).replace(' ', '').replace('-', '') for match in aadhar_matches]
            fields["aadhar"] = aadhars[0] if aadhars else None

        return fields