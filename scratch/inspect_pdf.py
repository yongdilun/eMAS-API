import fitz
import sys

def inspect_loto_steps():
    pdf_path = 'rag_sources/03_safety_and_maintenance/osha_lockout_tagout_guide.pdf'
    doc = fitz.open(pdf_path)
    
    found = False
    for i, page in enumerate(doc):
        text = page.get_text()
        if '(1) Notification' in text or 'Step 1' in text:
            print(f"=== PAGE {i} ===")
            print(text)
            found = True
    
    if not found:
        print("Steps not found with exact strings. Printing first 10 pages summary.")
        for i in range(min(10, len(doc))):
            print(f"--- Page {i} Snippet ---")
            print(doc[i].get_text()[:500])

if __name__ == "__main__":
    inspect_loto_steps()
