import fitz  # PyMuPDF

def extract_text(pdf_bytes: bytes) -> str:
    """
    Extracts text preserving page boundaries with "--- PAGE N ---" markers.
    """
    doc = fitz.open("pdf", pdf_bytes)
    output = []
    
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text("text")
        output.append(f"--- PAGE {i + 1} ---")
        output.append(text)
        
    return "\n".join(output)

def extract_text_blocks(pdf_bytes: bytes) -> list[dict]:
    """
    Extracts structured text blocks.
    Returns list of {text, page, font_size, is_bold, bbox}
    """
    doc = fitz.open("pdf", pdf_bytes)
    blocks_out = []
    
    for i in range(len(doc)):
        page = doc[i]
        page_dict = page.get_text("dict")
        
        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            flags = span.get("flags", 0)
                            # PyMuPDF flag 16 means bold for some fonts, but reliable bold detection 
                            # usually checks if "Bold" is in the font name.
                            font_name = span.get("font", "").lower()
                            is_bold = "bold" in font_name or (flags & 16) == 16
                            font_size = span.get("size", 0)
                            bbox = span.get("bbox", [])
                            
                            blocks_out.append({
                                "text": text,
                                "page": i + 1,
                                "font_size": font_size,
                                "is_bold": is_bold,
                                "bbox": bbox
                            })
                            
    return blocks_out
