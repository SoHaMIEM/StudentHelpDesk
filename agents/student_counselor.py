from .base_agent import BaseAgent
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

class StudentCounselor(BaseAgent):
    def __init__(self):
        super().__init__()
        self.communication_templates = {
            "application_received": "Dear {name}, we have received your application for {program}. Our team will review it shortly.",
            "shortlisted": "Congratulations {name}! You have been shortlisted for {program}. Next steps: {next_steps}",
            "document_missing": "Dear {name}, please submit the following documents: {documents}",
            "fee_payment": "Dear {name}, please complete the fee payment of {amount} for {program}."
        }
        self.common_queries = {
            "admission_process": "Information about the admission process and requirements",
            "program_details": "Detailed information about specific programs",
            "deadlines": "Important dates and deadlines",
            "fees": "Fee structure and payment information",
            "documents": "Required documents and submission process",
            "loans": "Student loan options and application process"
        }
    
    async def send_communication(self, student: Dict[str, Any], template_key: str, **kwargs) -> Dict[str, Any]:
        if template_key not in self.communication_templates:
            return {"success": False, "message": "Invalid template"}
            
        template = self.communication_templates[template_key]
        message = template.format(**student, **kwargs)
        
        # In a real implementation, this would send an actual email
        # For demo purposes, we'll just return the message
        return {
            "success": True,
            "recipient": student['email'],
            "message": message
        }
    
    async def get_program_info(self, program: str) -> str:
        prompt = f"Provide detailed information about the {program} program including admission requirements and course structure"
        return await self.generate_response(prompt)
        
    async def answer_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Answer student queries with context awareness"""
        try:
            # Get conversation history if available
            history = await self._get_conversation_history(context.get('student_name'))
            
            # Generate context-aware prompt
            prompt = self._generate_context_aware_prompt(query, context, history)
            
            # Get AI response
            response = await self.generate_response(prompt)
            
            # Store interaction
            await self._store_interaction(query, response, context)
            
            self.log_action("answer_query", {
                "query_type": self._categorize_query(query),
                "student": context.get('student_name', 'anonymous')
            })
            
            return {
                "success": True,
                "response": response,
                "suggested_followup": await self._generate_followup_questions(query, response)
            }
            
        except Exception as e:
            self.log_action("query_error", {"error": str(e)})
            return {
                "success": False,
                "error": "Failed to process your query",
                "details": str(e)
            }
            
    async def provide_program_info(self, program: str) -> Dict[str, Any]:
        """Provide detailed information about a specific program"""
        try:
            prompt = f"Provide comprehensive information about the {program} program, including requirements, curriculum, and career prospects."
            info = await self.generate_response(prompt)
            
            return {
                "success": True,
                "program": program,
                "information": info,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_action("program_info_error", {"error": str(e)})
            return {"success": False, "error": str(e)}
            
    async def _get_conversation_history(self, student_name: Optional[str]) -> List[Dict[str, Any]]:
        """Retrieve conversation history for a student"""
        if not student_name:
            return []
            
        try:
            collection = self.db.client.get_collection("queries")
            results = collection.get(
                where={"student_name": student_name},
                limit=5  # Get last 5 interactions
            )
            
            history = []
            for doc, meta in zip(results['documents'], results['metadatas']):
                history.append({
                    "query": meta['query'],
                    "response": doc,
                    "timestamp": meta['timestamp']
                })
                
            return history
            
        except Exception:
            return []
            
    def _generate_context_aware_prompt(self, query: str, context: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
        """Generate a context-aware prompt for the AI"""
        prompt_parts = [
            f"Answer the following query: {query}",
            f"Program context: {context.get('program', 'Not specified')}"
        ]
        
        if history:
            prompt_parts.append("Previous conversation context:")
            for interaction in history[-2:]:  # Include last 2 interactions
                prompt_parts.append(f"Q: {interaction['query']}")
                prompt_parts.append(f"A: {interaction['response']}")
                
        return "\n".join(prompt_parts)
        
    async def _store_interaction(self, query: str, response: str, context: Dict[str, Any]) -> None:
        """Store interaction in database"""
        metadata = {
            "student_name": context.get('student_name', 'anonymous'),
            "program": context.get('program', 'general'),
            "query_type": self._categorize_query(query),
            "timestamp": datetime.now().isoformat()
        }
        
        self.db.store_query(query, response, metadata)
        
    def _categorize_query(self, query: str) -> str:
        """Categorize the type of query"""
        query_lower = query.lower()
        for category, description in self.common_queries.items():
            if any(word in query_lower for word in category.split('_')):
                return category
        return "general"
        
    async def _generate_followup_questions(self, query: str, response: str) -> List[str]:
        """Generate relevant follow-up questions"""
        prompt = f"""
        Based on this interaction:
        Q: {query}
        A: {response}
        
        Suggest 2-3 relevant follow-up questions the student might want to ask.
        """
        
        suggestions = await self.generate_response(prompt)
        return [q.strip() for q in suggestions.split('\n') if q.strip()]