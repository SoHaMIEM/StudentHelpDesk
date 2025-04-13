from .base_agent import BaseAgent
from typing import Dict, Any, List
from utils.validators import validate_documents
from utils.error_handler import DocumentValidationError
import mimetypes
from datetime import datetime

class DocumentChecker(BaseAgent):
    def __init__(self):
        super().__init__()
        
    async def verify_documents(self, documents: List[Any]) -> Dict[str, Any]:
        """Verify submitted documents"""
        try:
            # Get document metadata and validate types
            doc_metadata = []
            for doc in documents:
                mime_type = mimetypes.guess_type(doc.name)[0]
                doc_metadata.append({
                    "name": doc.name,
                    "type": mime_type,
                    "size": len(doc.getvalue())
                })
                
            # Store document verification results
            verification_results = []
            for meta in doc_metadata:
                prompt = f"Analyze this document: {meta['name']} of type {meta['type']}"
                analysis = await self.generate_response(prompt)
                
                result = {
                    "document": meta['name'],
                    "verification_result": analysis,
                    "type": meta['type'],
                    "verified": True,
                    "timestamp": datetime.now().isoformat()
                }
                verification_results.append(result)
                
                # Store in database
                self.db.store_document_verification(
                    f"doc_{meta['name']}",
                    result
                )
                
            self.log_action("verify_documents", {
                "num_documents": len(documents),
                "results": verification_results
            })
            
            return {
                "valid": True,
                "results": verification_results,
                "message": "All documents verified successfully"
            }
            
        except DocumentValidationError as e:
            self.log_action("document_validation_error", {"error": str(e)})
            return {
                "valid": False,
                "error": str(e)
            }
        except Exception as e:
            self.log_action("verification_error", {"error": str(e)})
            return {
                "valid": False,
                "error": "An error occurred during document verification"
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