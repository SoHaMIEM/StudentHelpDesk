from .base_agent import BaseAgent
from typing import Dict, Any, Optional
from utils.config import Config
from utils.error_handler import LoanProcessingError
from datetime import datetime
import json

class LoanAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        
    async def process_loan_request(self, amount: float, student_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new loan request"""
        try:
            # Validate student information and check eligibility
            if not await self._verify_student_eligibility(student_info):
                return {
                    "approved": False,
                    "reason": "Student not eligible for loan"
                }
            
            # Check budget availability
            budget_status = await self._check_budget_availability(amount)
            if not budget_status['available']:
                return {
                    "approved": False,
                    "reason": budget_status['reason'],
                    "suggested_amount": budget_status.get('suggested_amount')
                }
            
            # Calculate loan terms
            terms = await self._calculate_loan_terms(amount, student_info)
            
            # Store loan application
            loan_id = self.db.store_loan_application({
                "student_name": student_info['name'],
                "program": student_info['program'],
                "amount": amount,
                "terms": terms,
                "status": "approved",
                "timestamp": datetime.now().isoformat()
            })
            
            self.log_action("process_loan", {
                "loan_id": loan_id,
                "amount": amount,
                "program": student_info['program']
            })
            
            return {
                "approved": True,
                "loan_id": loan_id,
                "amount": amount,
                "terms": terms,
                "next_steps": "Please submit the following documents:\n1. Income proof\n2. Guarantor details\n3. Bank statements"
            }
            
        except Exception as e:
            self.log_action("loan_processing_error", {"error": str(e)})
            raise LoanProcessingError(f"Error processing loan request: {str(e)}")
            
    async def _verify_student_eligibility(self, student_info: Dict[str, Any]) -> bool:
        """Verify if student is eligible for loan"""
        try:
            # Check if student is enrolled/shortlisted
            collection = self.db.client.get_collection("applications")
            results = collection.get(
                where={
                    "student_name": student_info['name'],
                    "program": student_info['program']
                }
            )
            
            if not results['ids']:
                return False
                
            status = results['metadatas'][0].get('status')
            return status in ['shortlisted', 'enrolled']
            
        except Exception:
            return False
            
    async def _check_budget_availability(self, amount: float) -> Dict[str, Any]:
        """Check if requested amount is within budget"""
        try:
            loan_stats = await self.generate_loan_report()
            remaining_budget = Config.LOAN_ANNUAL_BUDGET - loan_stats['total_amount_approved']
            
            if amount > remaining_budget:
                return {
                    "available": False,
                    "reason": "Insufficient budget",
                    "suggested_amount": remaining_budget
                }
                
            return {"available": True}
            
        except Exception as e:
            self.log_action("budget_check_error", {"error": str(e)})
            return {"available": False, "reason": "Error checking budget"}
            
    async def _calculate_loan_terms(self, amount: float, student_info: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate loan terms based on amount and student info"""
        base_interest_rate = Config.LOAN_INTEREST_RATE
        
        # Adjust interest rate based on program and amount
        program_adjustments = {
            "Undergraduate": 0.0,    # No adjustment
            "Graduate": -0.005,      # -0.5% adjustment
            "PhD": -0.01            # -1% adjustment
        }
        
        final_rate = base_interest_rate + program_adjustments.get(student_info['program'], 0)
        
        # Calculate monthly payment (simple calculation for demo)
        term_years = 10
        monthly_payment = (amount * (1 + final_rate * term_years)) / (term_years * 12)
        
        return {
            "interest_rate": final_rate,
            "term_years": term_years,
            "monthly_payment": round(monthly_payment, 2),
            "total_repayment": round(monthly_payment * term_years * 12, 2)
        }
        
    async def generate_loan_report(self) -> Dict[str, Any]:
        """Generate comprehensive loan report"""
        try:
            stats = self.db.get_loan_statistics()
            
            # Generate analysis
            prompt = f"""
            Analyze these loan statistics and provide insights:
            Total applications: {stats['total_applications']}
            Total amount requested: ${stats['total_amount_requested']}
            Total amount approved: ${stats['total_amount_approved']}
            Remaining budget: ${stats['remaining_budget']}
            """
            
            analysis = await self.generate_response(prompt)
            
            return {
                **stats,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_action("report_generation_error", {"error": str(e)})
            return {
                "error": "Failed to generate loan report",
                "details": str(e)
            }
            
    async def get_loan_status(self, loan_id: str) -> Dict[str, Any]:
        """Get status of a specific loan application"""
        try:
            collection = self.db.client.get_collection("loans")
            results = collection.get(ids=[loan_id])
            
            if not results['ids']:
                return {"found": False}
                
            loan_data = json.loads(results['documents'][0])
            return {
                "found": True,
                "status": loan_data['status'],
                "amount": loan_data['amount'],
                "terms": loan_data['terms']
            }
            
        except Exception as e:
            self.log_action("loan_status_error", {"error": str(e)})
            return {"found": False, "error": str(e)}