import fitz
import sys

def test_pdf():
    doc = fitz.open() # Create a blank pdf
    page = doc.new_page()
    page.insert_text((50, 50), "Hello world")
    
    # Just to check the dict structure
    d = page.get_text("dict")
    print("Blocks:")
    for b in d["blocks"]:
        print(b["type"], b.keys())
        if b["type"] == 0:
            for l in b["lines"]:
                for s in l["spans"]:
                    print(s["text"], end="")
            print()

test_pdf()
