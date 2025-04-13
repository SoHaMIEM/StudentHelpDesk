import os
from pathlib import Path

class PolicyLoader:
    @staticmethod
    def load_policies():
        """Load all policy files from the data directory"""
        data_dir = Path(__file__).parent.parent / 'data'
        policies = {}
        
        policy_files = [
            'admission_policy.txt',
            'loan_policy.txt',
            'shortlisting_criteria.txt'
        ]
        
        for file in policy_files:
            try:
                with open(data_dir / file, 'r') as f:
                    policies[file.replace('.txt', '')] = f.read()
            except FileNotFoundError:
                print(f"Warning: Policy file {file} not found")
                policies[file.replace('.txt', '')] = ""
                
        return policies