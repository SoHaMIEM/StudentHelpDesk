import chromadb
from pathlib import Path
from typing import Dict, Any, List, Optional
from .config import Config
import json

class DBManager:
    def __init__(self):
        Path(Config.CHROMA_PERSISTENCE_DIR).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=Config.CHROMA_PERSISTENCE_DIR)
        self._initialize_collections()
        
    def _initialize_collections(self):
        """Initialize required collections if they don't exist"""
        collections = {
            "applications": "Store student applications and their status",
            "documents": "Store document metadata and verification status",
            "loans": "Store loan applications and their status",
            "queries": "Store student queries and responses for future reference"
        }
        
        existing_collections = {col.name: col for col in self.client.list_collections()}
        
        for name, description in collections.items():
            if name not in existing_collections:
                self.client.create_collection(
                    name=name,
                    metadata={"description": description}
                )
                
    def store_application(self, application_data: Dict[str, Any]) -> str:
        """Store a new application"""
        try:
            collection = self.client.get_or_create_collection("applications")
            app_id = f"{application_data['name']}_{application_data['program']}".lower().replace(' ', '_')
            
            # Ensure the application data is JSON serializable
            doc_data = json.dumps(application_data)
            
            # Add the application to the collection
            collection.add(
                documents=[doc_data],
                metadatas=[{
                    "status": application_data.get('status', 'pending'),
                    "program": application_data['program'],
                    "submission_date": application_data.get('submission_date')
                }],
                ids=[app_id]
            )
            
            return app_id
        except Exception as e:
            raise Exception(f"Failed to store application: {str(e)}")
        
    def update_application_status(self, app_id: str, new_status: str) -> bool:
        """Update application status"""
        collection = self.client.get_or_create_collection("applications")
        try:
            results = collection.get(ids=[app_id])
            if results['ids']:
                metadata = results['metadatas'][0]
                metadata['status'] = new_status
                collection.update(
                    ids=[app_id],
                    metadatas=[metadata]
                )
                return True
        except Exception:
            return False
            
    def store_document_verification(self, app_id: str, doc_data: Dict[str, Any]) -> bool:
        """Store document verification results"""
        collection = self.client.get_or_create_collection("documents")
        try:
            collection.add(
                documents=[json.dumps(doc_data['verification_result'])],
                metadatas=[{
                    "application_id": app_id,
                    "document_type": doc_data['type'],
                    "verified": doc_data['verified']
                }],
                ids=[f"{app_id}_doc_{doc_data['type']}"]
            )
            return True
        except Exception:
            return False
            
    def store_loan_application(self, loan_data: Dict[str, Any]) -> str:
        """Store a new loan application"""
        collection = self.client.get_or_create_collection("loans")
        loan_id = f"loan_{loan_data['student_name']}_{loan_data['amount']}".lower().replace(' ', '_')
        
        collection.add(
            documents=[json.dumps(loan_data)],
            metadatas=[{
                "status": "pending",
                "amount": loan_data['amount'],
                "program": loan_data['program']
            }],
            ids=[loan_id]
        )
        return loan_id
        
    def get_program_statistics(self, program: str) -> Dict[str, int]:
        """Get statistics for a specific program"""
        collection = self.client.get_or_create_collection("applications")
        results = collection.get(
            where={"program": program}
        )
        
        status_counts = {
            "total": len(results['ids']),
            "pending": sum(1 for meta in results['metadatas'] if meta['status'] == 'pending'),
            "shortlisted": sum(1 for meta in results['metadatas'] if meta['status'] == 'shortlisted'),
            "rejected": sum(1 for meta in results['metadatas'] if meta['status'] == 'rejected')
        }
        return status_counts
        
    def get_loan_statistics(self) -> Dict[str, Any]:
        """Get overall loan statistics"""
        collection = self.client.get_or_create_collection("loans")
        results = collection.get()
        
        total_amount = sum(meta['amount'] for meta in results['metadatas'])
        approved_amount = sum(
            meta['amount'] for meta in results['metadatas'] 
            if json.loads(doc)['status'] == 'approved'
            for doc in results['documents']
        )
        
        return {
            "total_applications": len(results['ids']),
            "total_amount_requested": total_amount,
            "total_amount_approved": approved_amount,
            "remaining_budget": Config.LOAN_ANNUAL_BUDGET - approved_amount
        }
        
    def store_query(self, query: str, response: str, metadata: Dict[str, Any]) -> None:
        """Store student query and response for future reference"""
        collection = self.client.get_or_create_collection("queries")
        query_id = f"query_{metadata.get('student_name', 'anonymous')}_{len(collection.get()['ids'])}"
        
        collection.add(
            documents=[response],
            metadatas=[{
                "query": query,
                "program": metadata.get('program', 'general'),
                "timestamp": metadata.get('timestamp')
            }],
            ids=[query_id]
        )
        
    def store_generated_documents(self, application_id: str, doc_data: Dict[str, Any]) -> None:
        """Store generated admission documents"""
        collection = self.client.get_or_create_collection("documents")
        collection.add(
            documents=[json.dumps(doc_data)],
            metadatas=[{
                "application_id": application_id,
                "document_type": "admission_documents",
                "generated_date": doc_data['generated_date']
            }],
            ids=[f"{application_id}_admission_docs"]
        )