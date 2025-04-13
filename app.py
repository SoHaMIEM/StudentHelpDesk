import streamlit as st
import asyncio
from pathlib import Path
import os
from datetime import datetime
from utils.api_interface import AdmissionAPI
from utils.config import Config
from utils.error_handler import logger

# Initialize configuration
Config.init_directories()

# Initialize session state
if 'api' not in st.session_state:
    st.session_state.api = AdmissionAPI()

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'current_user' not in st.session_state:
    st.session_state.current_user = None
    
def authenticate_user(name: str, email: str) -> bool:
    """Validate and authenticate user"""
    if not name or not email:
        return False
    return True

async def main():
    st.title("University Admission Helpdesk")
    
    # Sidebar for user authentication and type selection
    with st.sidebar:
        user_type = st.selectbox(
            "Select User Type",
            ["Student", "University Director", "Admission Officer"]
        )
        
        if user_type == "Student":
            with st.form("login_form", clear_on_submit=False):
                name = st.text_input("Full Name")
                email = st.text_input("Email")
                submit = st.form_submit_button("Login/Register")
                
                if submit:
                    if authenticate_user(name, email):
                        st.session_state.current_user = {
                            "name": name,
                            "email": email,
                            "type": "student"
                        }
                        st.success(f"Welcome, {name}!")
                    else:
                        st.error("Please provide both name and email")
        else:
            # Simple authentication for staff (in real app, would need proper auth)
            st.session_state.current_user = {
                "type": user_type.lower().replace(" ", "_")
            }
    
    # Check authentication before showing interfaces
    if user_type == "Student":
        if st.session_state.current_user and st.session_state.current_user.get('type') == 'student':
            await show_student_interface()
        else:
            st.warning("Please log in to access the student portal")
    elif user_type == "University Director":
        await show_director_interface()
    else:
        await show_admission_officer_interface()

async def show_student_interface():
    st.header("Student Portal")
    
    # Ensure user is logged in
    if not st.session_state.current_user:
        st.warning("Please log in to access the student portal")
        return
        
    # Get user info
    user_info = st.session_state.current_user
    
    tabs = st.tabs(["Application", "Loan Request", "Query Support", "Application Status"])
    
    with tabs[0]:  # Application Tab
        st.subheader("Submit Application")
        with st.form("application_form"):
            # Pre-fill with user info
            name = st.text_input("Full Name", value=user_info.get('name', ''))
            email = st.text_input("Email", value=user_info.get('email', ''))
            program = st.selectbox("Program", ["Undergraduate", "Graduate", "PhD"])
            
            # Document upload with clear instructions
            st.markdown("### Required Documents")
            st.markdown("""
            Please upload the following documents:
            - Academic transcripts
            - Letters of recommendation
            - Statement of purpose
            - CV/Resume
            """)
            
            uploaded_files = st.file_uploader(
                "Upload Documents",
                accept_multiple_files=True,
                type=['pdf', 'doc', 'docx']
            )
            
            submit_button = st.form_submit_button("Submit Application")
            
            if submit_button and name and email and program and uploaded_files:
                with st.spinner("Processing your application..."):
                    # Create application data dictionary
                    application_data = {
                        "name": name,
                        "email": email,
                        "program": program
                    }
                    
                    result = await st.session_state.api.submit_application(
                        application_data,
                        uploaded_files
                    )
                    
                    if result['success']:
                        st.success(f"Application submitted successfully! Your ID: {result['application_id']}")
                        st.info("Please save your application ID for future reference.")
                    else:
                        st.error(result.get('error', 'Application submission failed'))
    
    with tabs[1]:  # Loan Request Tab
        st.subheader("Student Loan Application")
        with st.form("loan_form"):
            loan_amount = st.number_input("Loan Amount Required ($)", min_value=1000, step=1000)
            program = st.selectbox("Program", ["Undergraduate", "Graduate", "PhD"], key="loan_program")
            st.markdown("### Loan Terms")
            st.markdown("""
            - Interest rates from 5-7% based on program
            - 10-year repayment period
            - Flexible repayment options
            """)
            
            submit_loan = st.form_submit_button("Apply for Loan")
            
            if submit_loan:
                with st.spinner("Processing your loan request..."):
                    result = await st.session_state.api.process_loan_request(
                        loan_amount,
                        {
                            "name": st.session_state.current_user['name'],
                            "program": program
                        }
                    )
                    
                    if result['approved']:
                        st.success(f"Loan approved! Amount: ${loan_amount:,}")
                        st.json(result['terms'])
                        st.info(result['next_steps'])
                    else:
                        st.error(result['reason'])
                        if 'suggested_amount' in result:
                            st.info(f"Suggested loan amount: ${result['suggested_amount']:,}")
    
    with tabs[2]:  # Query Support Tab
        st.subheader("Ask a Question")
        
        # Display chat history
        for msg in st.session_state.chat_history:
            if msg['type'] == 'user':
                st.write(f"You: {msg['content']}")
            else:
                st.write(f"Assistant: {msg['content']}")
        
        # Query input
        query = st.text_input("Your Question")
        if query and st.session_state.current_user:
            st.session_state.chat_history.append({"type": "user", "content": query})
            
            with st.spinner("Processing your query..."):
                response = await st.session_state.api.answer_student_query(
                    query,
                    {
                        "student_name": st.session_state.current_user.get('name', 'Anonymous'),
                        "program": st.session_state.current_user.get('program', 'Unknown')
                    }
                )
                
                if response['success']:
                    st.write("Assistant:", response['response'])
                    st.session_state.chat_history.append({
                        "type": "assistant",
                        "content": response['response']
                    })
                    
                    # Show suggested follow-up questions
                    if response.get('suggested_followup'):
                        st.markdown("### You might also want to ask:")
                        for question in response['suggested_followup']:
                            st.markdown(f"- {question}")
                else:
                    st.error("Failed to process your query")
    
    with tabs[3]:  # Application Status Tab
        st.subheader("Check Application Status")
        application_id = st.text_input("Enter your Application ID")
        if application_id:
            with st.spinner("Checking status..."):
                status = await st.session_state.api.check_application_status(application_id)
                if status['found']:
                    st.info(f"Status: {status['status'].title()}")
                    if status['status'] == 'shortlisted':
                        st.success("Congratulations! You have been shortlisted.")
                        st.markdown("### Next Steps")
                        st.markdown("1. Complete fee payment")
                        st.markdown("2. Submit remaining documents")
                        st.markdown("3. Attend orientation")
                else:
                    st.error("Application not found")

async def show_director_interface():
    st.header("Director Dashboard")
    
    # Refresh button for dashboard
    if st.button("Refresh Statistics"):
        st.session_state.stats = await st.session_state.api.get_admission_stats()
    
    if 'stats' not in st.session_state:
        with st.spinner("Loading statistics..."):
            st.session_state.stats = await st.session_state.api.get_admission_stats()
    
    stats = st.session_state.stats
    
    # Overview statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Applications", stats['admission_stats']['total_applications'])
    with col2:
        st.metric("Shortlisted", stats['admission_stats']['shortlisted'])
    with col3:
        st.metric("Pending", stats['admission_stats']['pending'])
    with col4:
        st.metric("Total Loan Amount", f"${stats['loan_stats']['total_amount_approved']:,}")
    
    # Program-wise statistics
    st.subheader("Program Statistics")
    for program in ["Undergraduate", "Graduate", "PhD"]:
        with st.expander(f"{program} Program"):
            shortlist = await st.session_state.api.generate_shortlist(program)
            capacity = Config.get_program_capacity(program)
            
            # Program metrics
            cols = st.columns(3)
            with cols[0]:
                st.metric("Applications", shortlist['total'])
            with cols[1]:
                st.metric("Shortlisted", len(shortlist['shortlisted']))
            with cols[2]:
                st.metric("Available Spots", capacity - len(shortlist['shortlisted']))
    
    # Loan statistics
    st.subheader("Loan Statistics")
    loan_stats = stats['loan_stats']
    st.write(f"Budget Utilization: {(loan_stats['total_amount_approved'] / Config.LOAN_ANNUAL_BUDGET) * 100:.1f}%")
    st.progress(loan_stats['total_amount_approved'] / Config.LOAN_ANNUAL_BUDGET)
    
    if loan_stats.get('analysis'):
        st.markdown("### Analysis")
        st.write(loan_stats['analysis'])

async def show_admission_officer_interface():
    st.header("Admission Officer Portal")
    
    tabs = st.tabs(["Review Applications", "Document Verification", "Update Status", "Generate Documents"])
    
    with tabs[0]:  # Review Applications Tab
        st.subheader("Pending Applications")
        program_filter = st.selectbox(
            "Filter by Program",
            ["All Programs", "Undergraduate", "Graduate", "PhD"]
        )
        
        applications = st.session_state.api.admission_officer.applications
        
        for app_id, status in applications.items():
            if status == "pending":
                program = app_id.split('_')[-1]
                if program_filter == "All Programs" or program == program_filter.lower():
                    with st.expander(f"Application: {app_id}"):
                        st.write(f"Status: {status}")
                        if st.button(f"Review {app_id}"):
                            with st.spinner("Checking documents..."):
                                doc_check = await st.session_state.api.document_checker.verify_documents([])
                                st.write(doc_check)
                                
                            # Evaluate candidate
                            evaluation = await st.session_state.api.shortlisting_agent.evaluate_candidate(app_id)
                            if evaluation['success']:
                                st.write("### Evaluation Result")
                                st.write(evaluation['result']['evaluation'])
                                st.metric("Score", f"{evaluation['result']['score']:.1f}/100")
    
    with tabs[1]:  # Document Verification Tab
        st.subheader("Document Verification")
        uploaded_file = st.file_uploader("Upload Document for Verification", type=['pdf', 'doc', 'docx'])
        if uploaded_file:
            with st.spinner("Analyzing document..."):
                analysis = await st.session_state.api.document_checker.analyze_document_content(uploaded_file)
                st.write("### Document Analysis")
                st.write(analysis)
    
    with tabs[2]:  # Update Status Tab
        st.subheader("Update Application Status")
        with st.form("status_update_form"):
            app_id = st.text_input("Application ID")
            new_status = st.selectbox("New Status", ["pending", "shortlisted", "rejected"])
            
            if st.form_submit_button("Update Status"):
                with st.spinner("Updating status..."):
                    result = await st.session_state.api.update_application_status(app_id, new_status)
                    if result['success']:
                        st.success(f"Status updated for application {app_id}")
                        if new_status == "shortlisted":
                            st.info("Student has been notified. You can now generate admission documents.")
                    else:
                        st.error(result.get('error', "Failed to update status"))
                        
    with tabs[3]:  # Generate Documents Tab
        st.subheader("Generate Admission Documents")
        col1, col2 = st.columns(2)
        
        with col1:
            app_id = st.text_input("Enter Application ID")
            if st.button("Generate Documents"):
                with st.spinner("Generating documents..."):
                    result = await st.session_state.api.generate_admission_documents(app_id)
                    if result['success']:
                        st.session_state.generated_docs = result
                        st.success("Documents generated successfully!")
                    else:
                        st.error(result.get('error', "Failed to generate documents"))
                        
        with col2:
            if 'generated_docs' in st.session_state:
                docs = st.session_state.generated_docs
                st.markdown("### Preview Documents")
                
                with st.expander("Admission Letter"):
                    st.text(docs['admission_letter'])
                    
                with st.expander("Fee Slip"):
                    st.text(docs['fee_slip'])
                    
                st.info(f"Student ID: {docs['student_id']}")
                
                if st.button("Send Documents to Student"):
                    with st.spinner("Sending documents..."):
                        # Documents are already sent during generation
                        st.success("Documents sent to student's email")

if __name__ == "__main__":
    asyncio.run(main())