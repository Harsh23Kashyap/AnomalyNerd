"""Nested HTML tables must not become silently damaged numeric evidence."""
from pathlib import Path
import importlib.util
import os
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from anomalynerd.html_ingest import parse_html

FLAT='<table><tr><th>Method</th><th>Score</th></tr><tr><td>A</td><td>99</td></tr><tr><td>B</td><td>88</td></tr></table>'
NESTED='<table><tr><th>Method</th><th>Score</th></tr><tr><td>A<table><tr><td>note</td></tr></table></td><td>99</td></tr><tr><td>B</td><td>88</td></tr></table>'
@pytest.mark.parametrize('nested',[NESTED,NESTED.replace('note','<table><tr><td>deep</td></tr></table>'),NESTED.replace('note','12345'),NESTED.replace('<td>A<table>','<td><table>')])
def test_nested_table_is_not_numeric_evidence(tmp_path,nested):
 p=tmp_path/'nested.html';p.write_text(nested)
 result=parse_html(str(p))
 assert not result.tables
 assert any('nested' in n and 'not analyzed' in n for n in result.notes)
 assert not any('no tables were found' in n for n in result.notes)

@pytest.mark.parametrize('before,after',[(True,False),(False,True),(True,True)])
def test_independent_flat_tables_survive(tmp_path,before,after):
 p=tmp_path/'mixed.html';p.write_text((FLAT if before else '')+NESTED+(FLAT if after else ''))
 result=parse_html(str(p))
 assert len(result.tables)==int(before)+int(after)
 assert all(any('99' in row for row in t.rows) for t in result.tables)
 assert any('nested' in n for n in result.notes)

@pytest.mark.parametrize('tag',['script','style','template'])
def test_ignored_markup_does_not_poison_flat_table(tmp_path,tag):
 p=tmp_path/'ignored.html';p.write_text('<'+tag+'>'+NESTED+'</'+tag+'>'+FLAT)
 result=parse_html(str(p))
 assert len(result.tables)==1
 assert not any('nested' in n for n in result.notes)

def test_prose_after_rejected_table_is_retained(tmp_path):
 p=tmp_path/'prose.html';p.write_text(NESTED+'<p>t(28)=2.40, p=.02</p>')
 result=parse_html(str(p))
 assert any('t(28)' in x for x in result.stat_strings)
