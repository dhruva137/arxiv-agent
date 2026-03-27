import pytest
from arxiv_diff.tools.arxiv_api import _strip_version
from arxiv_diff.tools.section_parser import parse as parse_sections
from arxiv_diff.tools.text_differ import diff as diff_sections
from arxiv_diff.tools.metadata_compare import compare as compare_metadata
from arxiv_diff.tools.figure_detector import detect as detect_figures

def test_arxiv_id_normalization():
    assert _strip_version("2301.00001v2") == "2301.00001"
    assert _strip_version("2301.00001") == "2301.00001"

def test_section_parser():
    text = "Preamble text here\nAbstract\nThis is the abstract\n1 Introduction\nIntro text\n3.2 Our Approach\nApproach text"
    res = parse_sections(text)
    assert "Preamble" in res
    assert "Abstract" in res
    assert "1 Introduction" in res
    assert "3.2 Our Approach" in res

def test_text_differ():
    v1 = {"Abstract": "A B C", "Intro": "Hello", "OldSection": "Delete me"}
    v2 = {"Abstract": "A B D", "Intro": "Hello", "NewSection": "Add me"}
    
    res = diff_sections(v1, v2)
    assert "NewSection" in res["added_sections"]
    assert "OldSection" in res["removed_sections"]
    assert "Intro" in res["unchanged_sections"]
    assert "Abstract" in res["changed_sections"]

def test_metadata_compare():
    m1 = {"title": "T1", "authors": ["A"], "abstract": "abs1"}
    m2 = {"title": "T2", "authors": ["A", "B"], "abstract": "abs2"}
    res = compare_metadata(m1, m2)
    assert res["title"]["old"] == "T1"
    assert res["authors"]["added"] == ["B"]
    assert "abstract" in res

def test_figure_detector():
    t1 = "See Figure 1 and Table 1. \nFigure 1: Old Cap"
    t2 = "See Figure 1 and Fig. 2\nFigure 1: New Cap\nFigure 2: Foo"
    
    res = detect_figures(t1, t2)
    assert "2" in res["added_figures"]
    assert "1" in res["removed_tables"]
    assert any(c["num"] == "1" and c["new"] == "New Cap" for c in res["changed_captions"])
