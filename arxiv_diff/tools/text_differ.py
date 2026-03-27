import difflib

def diff(sections_v1: dict, sections_v2: dict) -> dict:
    added_sections = []
    removed_sections = []
    unchanged_sections = []
    changed_sections = {}
    
    total_added_lines = 0
    total_removed_lines = 0
    
    keys_v1 = set(sections_v1.keys())
    keys_v2 = set(sections_v2.keys())
    
    for k in keys_v2 - keys_v1:
        added_sections.append(k)
        total_added_lines += len(sections_v2[k].splitlines())
        
    for k in keys_v1 - keys_v2:
        removed_sections.append(k)
        total_removed_lines += len(sections_v1[k].splitlines())
        
    for k in keys_v1.intersection(keys_v2):
        t1 = sections_v1[k]
        t2 = sections_v2[k]
        
        if t1 == t2:
            unchanged_sections.append(k)
        else:
            # Changed
            lines_v1 = t1.splitlines()
            lines_v2 = t2.splitlines()
            
            # SequenceMatcher ratio
            ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
            
            # Diff
            d = list(difflib.unified_diff(lines_v1, lines_v2, n=3, lineterm=""))
            
            # Count added/removed in this section
            a_lines = sum(1 for line in d if line.startswith("+") and not line.startswith("+++"))
            r_lines = sum(1 for line in d if line.startswith("-") and not line.startswith("---"))
            
            total_added_lines += a_lines
            total_removed_lines += r_lines
            
            # Cap at 200 lines to avoid blowing up context window
            capped_diff = "\n".join(d[:200])
            if len(d) > 200:
                capped_diff += "\n... [diff truncated (exceeds 200 lines)]"
                
            changed_sections[k] = {
                "unified_diff": capped_diff,
                "similarity": ratio,
                "added_lines": a_lines,
                "removed_lines": r_lines,
                "is_major_rewrite": ratio < 0.5
            }
            
    return {
        "added_sections": added_sections,
        "removed_sections": removed_sections,
        "unchanged_sections": unchanged_sections,
        "changed_sections": changed_sections,
        "total_added_lines": total_added_lines,
        "total_removed_lines": total_removed_lines,
        "total_changed_sections": len(changed_sections)
    }
