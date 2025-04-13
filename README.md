# University Admission Helpdesk

An automated helpdesk system for managing university admissions using AI agents and Streamlit.

## Features

- Multi-agent system for handling different aspects of admission process
- Document validation and verification
- Student loan processing
- Real-time admission statistics
- Student counseling support
- Role-based access (Student, Director, Admission Officer)

## Prerequisites

- Python 3.9 or higher
- Virtual environment (recommended)

## Setup

1. Clone the repository and create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
Create a `.env` file in the project root with:
```
GEMINI_API_KEY=your_api_key_here
CHROMA_PERSISTENCE_DIR=./data/chroma
MAX_APPLICATIONS_PER_PROGRAM={"Undergraduate": 100, "Graduate": 50, "PhD": 20}
LOAN_ANNUAL_BUDGET=1000000
```

## Running the Application

Start the Streamlit application:
```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

## Usage

### Student Portal
- Submit admission applications
- Request student loans
- Ask questions about programs and admission process

### Director Dashboard
- View admission statistics
- Monitor loan allocations
- Track program-wise enrollment

### Admission Officer Interface
- Review pending applications
- Update application status
- Verify documents

## Architecture

The system uses multiple AI agents powered by Google's Gemini model:
- Admission Officer: Manages overall admission process
- Document Checker: Validates submitted documents
- Shortlisting Agent: Evaluates and shortlists candidates
- Student Counselor: Handles student queries
- Loan Agent: Processes loan requests

Data is persisted using ChromaDB for efficient storage and retrieval.