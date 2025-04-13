from typing import Dict, Any
from datetime import datetime
import json
from .config import Config

class DocumentGenerator:
    def __init__(self):
        self.templates = {
            "admission_letter": """
UNIVERSITY ADMISSION LETTER

Date: {date}

Dear {name},

Congratulations! We are pleased to inform you that you have been accepted into the {program} program at our university.

Program Details:
- Program: {program}
- Duration: {duration}
- Start Date: {start_date}

Your student ID will be: {student_id}

Please complete the following steps to confirm your admission:
1. Pay the admission fee by the due date
2. Submit any pending documents
3. Complete the online orientation

Fee Details:
{fee_details}

Due Date for Fee Payment: {fee_due_date}

Best regards,
Admission Office
            """,
            
            "fee_slip": """
FEE PAYMENT SLIP

Student Details:
- Name: {name}
- Program: {program}
- Student ID: {student_id}

Fee Breakdown:
{fee_breakdown}

Total Amount: ${total_amount}
Due Date: {due_date}

Payment Methods:
1. Online Payment Portal: www.university.edu/payment
2. Bank Transfer to:
   Account Name: University Account
   Account Number: XXXX-XXXX-XXXX
   Bank: University Bank

Please quote your Student ID in all communications.
            """
        }
        
    def generate_admission_letter(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate admission letter from template"""
        try:
            program_duration = {
                "Undergraduate": "4 years",
                "Graduate": "2 years",
                "PhD": "4-5 years"
            }
            
            fee_structure = self._get_fee_structure(student_data['program'])
            
            letter_data = {
                "date": datetime.now().strftime("%B %d, %Y"),
                "name": student_data['name'],
                "program": student_data['program'],
                "duration": program_duration[student_data['program']],
                "start_date": "September 1, 2025",  # This should come from configuration
                "student_id": f"2025{student_data['program'][:2].upper()}{student_data['application_id'][-4:]}",
                "fee_details": self._format_fee_details(fee_structure),
                "fee_due_date": "August 1, 2025"  # This should come from configuration
            }
            
            letter = self.templates['admission_letter'].format(**letter_data)
            
            return {
                "success": True,
                "document": letter,
                "student_id": letter_data['student_id']
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate admission letter: {str(e)}"
            }
            
    def generate_fee_slip(self, student_data: Dict[str, Any], student_id: str) -> Dict[str, Any]:
        """Generate fee slip from template"""
        try:
            fee_structure = self._get_fee_structure(student_data['program'])
            total_amount = sum(fee_structure.values())
            
            fee_data = {
                "name": student_data['name'],
                "program": student_data['program'],
                "student_id": student_id,
                "fee_breakdown": self._format_fee_breakdown(fee_structure),
                "total_amount": total_amount,
                "due_date": "August 1, 2025"  # This should come from configuration
            }
            
            fee_slip = self.templates['fee_slip'].format(**fee_data)
            
            return {
                "success": True,
                "document": fee_slip,
                "amount": total_amount
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate fee slip: {str(e)}"
            }
            
    def _get_fee_structure(self, program: str) -> Dict[str, float]:
        """Get fee structure for program"""
        fee_structure = {
            "Undergraduate": {
                "Tuition Fee": 30000,
                "Registration Fee": 500,
                "Library Fee": 1000,
                "Technology Fee": 1500,
                "Student Activities": 1000
            },
            "Graduate": {
                "Tuition Fee": 40000,
                "Registration Fee": 500,
                "Library Fee": 1500,
                "Technology Fee": 2000,
                "Research Fee": 2500
            },
            "PhD": {
                "Tuition Fee": 45000,
                "Registration Fee": 500,
                "Library Fee": 2000,
                "Technology Fee": 2500,
                "Research Fee": 5000
            }
        }
        return fee_structure.get(program, {})
        
    def _format_fee_details(self, fee_structure: Dict[str, float]) -> str:
        """Format fee structure for admission letter"""
        details = ["Fee Structure:"]
        for item, amount in fee_structure.items():
            details.append(f"- {item}: ${amount:,}")
        details.append(f"\nTotal Fee: ${sum(fee_structure.values()):,}")
        return "\n".join(details)
        
    def _format_fee_breakdown(self, fee_structure: Dict[str, float]) -> str:
        """Format fee structure for fee slip"""
        breakdown = []
        for item, amount in fee_structure.items():
            breakdown.append(f"{item}: ${amount:,}")
        return "\n".join(breakdown)