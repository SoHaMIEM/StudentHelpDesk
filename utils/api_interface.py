from typing import Dict, Any, List
from agents import (
    AdmissionOfficer,
    DocumentChecker,
    ShortlistingAgent,
    StudentCounselor,
    LoanAgent
)
from .error_handler import logger, handle_exceptions
from .document_generator import DocumentGenerator
from datetime import datetime

class AdmissionAPI:
    def __init__(self):
        self.admission_officer = AdmissionOfficer()
        self.document_checker = DocumentChecker()
        self.shortlisting_agent = ShortlistingAgent()
        self.student_counselor = StudentCounselor()
        self.loan_agent = LoanAgent()
        self.document_generator = DocumentGenerator()
        
    @handle_exceptions
    async def submit_application(self, application_data: Dict[str, Any], documents: List[Any]) -> Dict[str, Any]:
        """Submit a new application"""
        # First verify documents
        doc_verification = await self.document_checker.verify_documents(documents)
        
        # If document verification failed, return the error with extracted data
        if not doc_verification['valid']:
            return {
                "success": False,
                "error": doc_verification.get('reason', 'Document verification failed'),
                "extracted_data": doc_verification.get('extracted_data', {})
            }
            
        # Process application
        result = await self.admission_officer.process_application(application_data)
        if result['success']:
            # Add verification results to the response
            result.update({
                "extracted_data": doc_verification.get('extracted_data', {}),
                "matched_student": doc_verification.get('matched_student', {}),
                "match_score": doc_verification.get('match_score', 0)
            })
            
            # Send confirmation to student
            await self.student_counselor.send_communication(
                application_data,
                "application_received",
                program=application_data['program']
            )
            
        return result
        
    @handle_exceptions
    async def check_application_status(self, application_id: str) -> Dict[str, Any]:
        """Check status of an application"""
        return self.admission_officer.check_status(application_id)
        
    @handle_exceptions
    async def process_loan_request(self, amount: float, student_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new loan request"""
        return await self.loan_agent.process_loan_request(amount, student_info)
        
    @handle_exceptions
    async def get_loan_status(self, loan_id: str) -> Dict[str, Any]:
        """Check status of a loan application"""
        return await self.loan_agent.get_loan_status(loan_id)
        
    @handle_exceptions
    async def answer_student_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle student queries"""
        return await self.student_counselor.answer_query(query, context)
        
    @handle_exceptions
    async def get_program_info(self, program: str) -> Dict[str, Any]:
        """Get detailed program information"""
        return await self.student_counselor.provide_program_info(program)
        
    @handle_exceptions
    async def generate_shortlist(self, program: str) -> Dict[str, Any]:
        """Generate shortlist for a program"""
        return await self.shortlisting_agent.generate_shortlist(program)
        
    @handle_exceptions
    async def get_admission_stats(self) -> Dict[str, Any]:
        """Get admission statistics"""
        stats = self.admission_officer.get_admission_stats()
        loan_stats = await self.loan_agent.generate_loan_report()
        
        return {
            "admission_stats": stats,
            "loan_stats": loan_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    @handle_exceptions
    async def update_application_status(self, application_id: str, new_status: str) -> Dict[str, Any]:
        """Update application status"""
        result = self.admission_officer.update_application_status(application_id, new_status)
        
        if result['success'] and new_status == 'shortlisted':
            # Get application details
            app_details = self.admission_officer.check_status(application_id)
            if app_details['found']:
                # Send notification to student
                await self.student_counselor.send_communication(
                    {"name": app_details['student_name']},
                    "shortlisted",
                    program=app_details['program'],
                    next_steps="Please complete fee payment and document submission"
                )
                
        return result

    @handle_exceptions
    async def generate_admission_documents(self, application_id: str) -> Dict[str, Any]:
        """Generate admission letter and fee slip for a shortlisted student"""
        # Get application details
        app_details = self.admission_officer.check_status(application_id)
        if not app_details['found'] or app_details['status'] != 'shortlisted':
            return {
                "success": False,
                "error": "Application not found or not shortlisted"
            }
            
        # Generate admission letter
        letter_result = self.document_generator.generate_admission_letter({
            "name": app_details['student_name'],
            "program": app_details['program'],
            "application_id": application_id
        })
        
        if not letter_result['success']:
            return letter_result
            
        # Generate fee slip using student ID from admission letter
        fee_slip_result = self.document_generator.generate_fee_slip(
            {
                "name": app_details['student_name'],
                "program": app_details['program']
            },
            letter_result['student_id']
        )
        
        if not fee_slip_result['success']:
            return fee_slip_result
            
        # Send documents to student
        await self.student_counselor.send_communication(
            {
                "name": app_details['student_name'],
                "email": app_details['email']
            },
            "shortlisted",
            program=app_details['program'],
            next_steps="Please find your admission letter and fee slip attached."
        )
        
        # Store documents in database
        self.db.store_generated_documents(
            application_id,
            {
                "admission_letter": letter_result['document'],
                "fee_slip": fee_slip_result['document'],
                "student_id": letter_result['student_id'],
                "generated_date": datetime.now().isoformat()
            }
        )
        
        return {
            "success": True,
            "admission_letter": letter_result['document'],
            "fee_slip": fee_slip_result['document'],
            "student_id": letter_result['student_id']
        }