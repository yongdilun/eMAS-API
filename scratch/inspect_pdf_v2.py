import fitz
import re

def search_loto_steps():
    pdf_path = 'rag_sources/03_safety_and_maintenance/osha_lockout_tagout_guide.pdf'
    doc = fitz.open(pdf_path)
    
    # Common OSHA LOTO steps often appear in a list
    patterns = [
        r'\(1\)\s+Notification',
        r'\(2\)\s+Machine',
        r'\(3\)\s+Machine',
        r'\(4\)\s+Apply',
        r'\(5\)\s+Release',
        r'\(6\)\s+Verification'
    ]
    
    for i, page in enumerate(doc):
        text = page.get_text()
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            print(f"--- MATCH FOUND ON PAGE {i} ---")
            print(text)
            
    print("--- SEARCH COMPLETED ---")

if __name__ == "__main__":
    search_loto_steps()
