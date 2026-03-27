import re

def parse(text: str) -> dict[str, str]:
    """
    Split extracted paper text into semantic sections.
    """
    sections = {}
    current_section = "Preamble"
    current_content = []
    
    # Common academic headers. Also matching numbered ones like "3.2 Our Approach"
    header_pattern = re.compile(
        r"^(?:\d+(?:\.\d+)*\s+)?("
        r"Abstract|Introduction|Related Work"
        r"|Background|Preliminaries|Methodology|Methods?"
        r"|(?:Our )?Approach|Model|Experiments?|Results|Evaluation"
        r"|Analysis|Discussion|Conclusions?"
        r"|Limitations?|Future Work|Broader Impact"
        r"|Ethics Statement|Acknowledgments?"
        r"|References|Bibliography|Appendix|Appendices)\s*$",
        re.IGNORECASE
    )
    
    # We will split text by newlines and try to identify headers.
    lines = text.split("\n")
    for line in lines:
        clean_line = line.strip()
        # To avoid false positives on lines that just happen to just contain "Model",
        # let's only consider relatively short lines as headers. 
        # (Though extracting headers accurately from unformatted PDF text is notoriously hard.)
        if len(clean_line) < 50 and header_pattern.match(clean_line):
            # Save previous section
            if current_content:
                sections[current_section] = sections.get(current_section, "") + "\n".join(current_content) + "\n"
            else:
                if current_section not in sections:
                    sections[current_section] = ""
                    
            # Set new section
            # Strip number prefix to group multiple 3.2 Introduction to "Introduction" or just use clean_line.
            # The prompt asks to map section_name -> content, so using clean_line is easiest.
            # But the LLM will see whatever name we give. Let's use clean_line as the section_name.
            current_section = clean_line
            current_content = []
        else:
            current_content.append(line)
            
    # Save the last section
    if current_content:
        sections[current_section] = sections.get(current_section, "") + "\n".join(current_content) + "\n"
        
    # Clean up empty strings
    for k in list(sections.keys()):
        sections[k] = sections[k].strip()
        
    return sections
