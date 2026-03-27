import re

def detect(text_v1: str, text_v2: str) -> dict:
    # We will look for mentions: "Figure 1", "Fig. 1", "Table 1", "Tab. 1"
    # And captions: starting with "Figure N:" or "Table N:"
    
    fig_pattern = re.compile(r"(?:Figure|Fig\.)\s+(\d+)", re.IGNORECASE)
    tab_pattern = re.compile(r"(?:Table|Tab\.)\s+(\d+)", re.IGNORECASE)
    
    # Captions pattern: line starts with "Figure 1:" or "Figure 1."
    fig_cap_pattern = re.compile(r"^\s*(?:Figure|Fig\.)\s+(\d+)[\.:]\s*(.+)", re.IGNORECASE | re.MULTILINE)
    tab_cap_pattern = re.compile(r"^\s*(?:Table|Tab\.)\s+(\d+)[\.:]\s*(.+)", re.IGNORECASE | re.MULTILINE)
    
    def extract_info(text):
        figs = set(fig_pattern.findall(text))
        tabs = set(tab_pattern.findall(text))
        
        fig_caps = {m[0]: m[1].strip() for m in fig_cap_pattern.findall(text)}
        tab_caps = {m[0]: m[1].strip() for m in tab_cap_pattern.findall(text)}
        
        return figs, tabs, fig_caps, tab_caps
        
    figs1, tabs1, fig_caps1, tab_caps1 = extract_info(text_v1)
    figs2, tabs2, fig_caps2, tab_caps2 = extract_info(text_v2)
    
    added_figures = list(figs2 - figs1)
    removed_figures = list(figs1 - figs2)
    
    added_tables = list(tabs2 - tabs1)
    removed_tables = list(tabs1 - tabs2)
    
    changed_captions = []
    
    # Check if a figure is present in both but caption changed
    for f_num in figs1.intersection(figs2):
        cap1 = fig_caps1.get(f_num)
        cap2 = fig_caps2.get(f_num)
        if cap1 and cap2 and cap1 != cap2:
            changed_captions.append({"entity": "Figure", "num": f_num, "old": cap1, "new": cap2})
            
    for t_num in tabs1.intersection(tabs2):
        cap1 = tab_caps1.get(t_num)
        cap2 = tab_caps2.get(t_num)
        if cap1 and cap2 and cap1 != cap2:
            changed_captions.append({"entity": "Table", "num": t_num, "old": cap1, "new": cap2})
            
    return {
        "added_figures": added_figures,
        "removed_figures": removed_figures,
        "added_tables": added_tables,
        "removed_tables": removed_tables,
        "changed_captions": changed_captions
    }
