from .base_agent import BaseAgent
from typing import Dict, Any, List
from utils.config import Config
from datetime import datetime
import json
import chromadb

class ShortlistingAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.db = chromadb.Client()
        self.collection = self.db.create_collection("eligibility_criteria")
        self.program_capacity = {
            "Undergraduate": 100,
            "Graduate": 50,
            "PhD": 20
        }
        
    def check_eligibility(self, application: Dict[str, Any]) -> Dict[str, Any]:
        program = application.get('program')
        if not program:
            return {"eligible": False, "reason": "Program not specified"}
            
        # Check program capacity
        current_applications = self.collection.get(
            where={"program": program}
        )
        
        if len(current_applications['ids']) >= self.program_capacity[program]:
            return {"eligible": False, "reason": f"Program {program} has reached capacity"}
            
        # In a real implementation, this would check actual eligibility criteria
        # For demo purposes, we'll simulate the check
        eligibility_result = {
            "eligible": True,
            "score": 85,  # Example score
            "feedback": "Application meets all eligibility criteria"
        }
        
        # Store the eligibility result
        self.collection.add(
            documents=[str(eligibility_result)],
            metadatas=[{
                "program": program,
                "applicant": application['name'],
                "score": eligibility_result['score']
            }],
            ids=[f"{application['name']}_{program}"]
        )
        
        return eligibility_result
        
    async def evaluate_candidate(self, application_id: str) -> Dict[str, Any]:
        """Evaluate a candidate's application"""
        try:
            # Get application data
            collection = self.db.client.get_collection("applications")
            results = collection.get(ids=[application_id])
            
            if not results['ids']:
                return {"success": False, "error": "Application not found"}
                
            application_data = json.loads(results['documents'][0])
            program = application_data['program']
            
            # Get document verification results
            doc_collection = self.db.client.get_collection("documents")
            doc_results = doc_collection.get(
                where={"application_id": application_id}
            )
            
            # Generate evaluation prompt
            prompt = f"""
            Evaluate this candidate for {program} program:
            Application details: {json.dumps(application_data)}
            Document verification results: {json.dumps(doc_results['documents'])}
            Consider: academic performance, recommendations, and program fit.
            """
            
            evaluation = await self.generate_response(prompt)
            
            # Calculate score based on criteria
            score = await self._calculate_score(application_data, doc_results['documents'])
            
            result = {
                "application_id": application_id,
                "program": program,
                "score": score,
                "evaluation": evaluation,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store evaluation result
            self._store_evaluation(result)
            
            self.log_action("evaluate_candidate", {
                "application_id": application_id,
                "score": score
            })
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            self.log_action("evaluation_error", {"error": str(e)})
            return {"success": False, "error": str(e)}
            
    async def generate_shortlist(self, program: str) -> Dict[str, Any]:
        """Generate shortlist for a specific program"""
        try:
            # Get program capacity
            capacity = Config.get_program_capacity(program)
            
            # Get all evaluated applications for the program
            collection = self.db.client.get_collection("applications")
            applications = collection.get(
                where={"program": program}
            )
            
            if not applications['ids']:
                return {
                    "success": True,
                    "total": 0,
                    "shortlisted": [],
                    "message": f"No applications found for {program}"
                }
                
            # Sort by score and get top candidates
            candidates = []
            for app_id, doc, meta in zip(
                applications['ids'],
                applications['documents'],
                applications['metadatas']
            ):
                app_data = json.loads(doc)
                if meta.get('status') != 'rejected':
                    candidates.append({
                        "id": app_id,
                        "score": app_data.get('score', 0),
                        "data": app_data
                    })
                    
            # Sort by score and take top candidates up to capacity
            shortlisted = sorted(
                candidates,
                key=lambda x: x['score'],
                reverse=True
            )[:capacity]
            
            # Update application status for shortlisted candidates
            for candidate in shortlisted:
                self.db.update_application_status(candidate['id'], "shortlisted")
                
            self.log_action("generate_shortlist", {
                "program": program,
                "total_applications": len(candidates),
                "shortlisted": len(shortlisted)
            })
            
            return {
                "success": True,
                "total": len(candidates),
                "shortlisted": shortlisted,
                "message": f"Generated shortlist for {program}"
            }
            
        except Exception as e:
            self.log_action("shortlist_error", {"error": str(e)})
            return {"success": False, "error": str(e)}
            
    async def _calculate_score(self, application_data: Dict[str, Any], documents: List[str]) -> float:
        """Calculate candidate score based on various criteria"""
        try:
            # Generate scoring prompt
            prompt = f"""
            Score this candidate on a scale of 0-100 based on:
            1. Academic performance (40%)
            2. Letters of recommendation (30%)
            3. Statement of purpose (20%)
            4. Overall profile fit (10%)
            
            Application: {json.dumps(application_data)}
            Documents: {json.dumps(documents)}
            """
            
            score_response = await self.generate_response(prompt)
            
            # Extract numerical score from response
            try:
                score = float(score_response.strip())
                return min(max(score, 0), 100)  # Ensure score is between 0 and 100
            except ValueError:
                return 50  # Default score if parsing fails
                
        except Exception:
            return 50  # Default score if scoring fails
            
    def _store_evaluation(self, evaluation: Dict[str, Any]) -> None:
        """Store evaluation result in database"""
        try:
            collection = self.db.client.get_collection("applications")
            collection.update(
                ids=[evaluation['application_id']],
                documents=[json.dumps(evaluation)],
                metadatas=[{
                    "score": evaluation['score'],
                    "program": evaluation['program'],
                    "evaluation_date": evaluation['timestamp']
                }]
            )
        except Exception as e:
            self.log_action("store_evaluation_error", {"error": str(e)})