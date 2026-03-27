import difflib

def compare(meta_v1: dict, meta_v2: dict) -> dict:
    changes = {}
    
    # Authors
    authors_v1 = meta_v1.get("authors", [])
    authors_v2 = meta_v2.get("authors", [])
    
    set_v1 = set(authors_v1)
    set_v2 = set(authors_v2)
    
    added_authors = list(set_v2 - set_v1)
    removed_authors = list(set_v1 - set_v2)
    
    # Check for reordering if identical sets
    reordered_authors = False
    if not added_authors and not removed_authors and authors_v1 != authors_v2:
        reordered_authors = True
        
    if added_authors or removed_authors or reordered_authors:
        changes["authors"] = {
            "added": added_authors,
            "removed": removed_authors,
            "reordered": reordered_authors
        }
        
    # Title
    title_v1 = meta_v1.get("title", "")
    title_v2 = meta_v2.get("title", "")
    if title_v1 != title_v2:
        changes["title"] = {
            "old": title_v1,
            "new": title_v2
        }
        
    # Abstract
    abs_v1 = meta_v1.get("abstract", "")
    abs_v2 = meta_v2.get("abstract", "")
    if abs_v1 != abs_v2:
        d = list(difflib.unified_diff(
            abs_v1.splitlines(), 
            abs_v2.splitlines(),
            n=3,
            lineterm=""
        ))
        changes["abstract"] = {
            "diff": "\n".join(d)
        }
        
    # Categories
    cat_v1 = set(meta_v1.get("categories", []))
    cat_v2 = set(meta_v2.get("categories", []))
    if cat_v1 != cat_v2:
        changes["categories"] = {
            "added": list(cat_v2 - cat_v1),
            "removed": list(cat_v1 - cat_v2)
        }
        
    return changes
