from .base_agent import BaseAgent
from typing import Dict, Any
from datetime import datetime
from utils.validators import validate_application_data
import chromadb
import json

class AdmissionOfficer(BaseAgent):
    def __init__(self):
        super().__init__()
        self.applications = {}
        
    def check_status(self, application_id: str) -> Dict[str, Any]:
        """Check status of an application"""
        try:
            collection = self.db.client.get_or_create_collection("applications")
            results = collection.get(ids=[application_id])
            
            if not results['ids']:
                return {"found": False}
                
            application_data = json.loads(results['documents'][0])
            metadata = results['metadatas'][0]
            
            return {
                "found": True,
                "status": metadata['status'],
                "student_name": application_data['name'],
                "program": application_data['program'],
                "email": application_data.get('email')
            }
            
        except Exception:
            return {"found": False}
        
    def get_admission_stats(self) -> Dict[str, Any]:
        """Get admission statistics"""
        try:
            collection = self.db.client.get_or_create_collection("applications")
            results = collection.get()
            
            status_counts = {
                "total_applications": len(results['ids']),
                "pending": sum(1 for meta in results['metadatas'] if meta['status'] == 'pending'),
                "shortlisted": sum(1 for meta in results['metadatas'] if meta['status'] == 'shortlisted'),
                "rejected": sum(1 for meta in results['metadatas'] if meta['status'] == 'rejected')
            }
            
            return status_counts
            
        except Exception:
            return {
                "total_applications": 0,
                "pending": 0,
                "shortlisted": 0,
                "rejected": 0
            }
        
    async def process_application(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new application"""
        try:
            # Validate application data
            validated_data = validate_application_data(application_data)
            
            # Store application
            app_id = self.db.store_application({
                **validated_data,
                "submission_date": datetime.now().isoformat(),
                "status": "pending"
            })
            self.applications[app_id] = "pending"
            
            self.log_action("process_application", {
                "application_id": app_id,
                "program": validated_data['program']
            })
            
            return {
                "success": True,
                "application_id": app_id,
                "message": "Application submitted successfully"
            }
            
        except Exception as e:
            self.log_action("process_application_error", {"error": str(e)})
            return {
                "success": False,
                "error": str(e)
            }
            
    def update_application_status(self, application_id: str, new_status: str) -> Dict[str, Any]:
        """Update application status"""
        if new_status not in ["pending", "shortlisted", "rejected"]:
            return {"success": False, "error": "Invalid status"}
            
        try:
            success = self.db.update_application_status(application_id, new_status)
            if success:
                self.applications[application_id] = new_status
                self.log_action("update_status", {
                    "application_id": application_id,
                    "new_status": new_status
                })
                return {"success": True}
            return {"success": False, "error": "Failed to update status"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        
    async def get_program_capacity(self, program: str) -> Dict[str, Any]:
        """Get program capacity and current enrollment"""
        stats = self.db.get_program_statistics(program)
        capacity_prompt = f"What is the current enrollment status for the {program} program?"
        
        capacity_info = await self.generate_response(capacity_prompt)
        
        return {
            "program": program,
            "total_applications": stats["total"],
            "current_enrollment": stats["shortlisted"],
            "capacity_info": capacity_info
        }