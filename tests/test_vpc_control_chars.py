"""Regression: VPC with literal newline/tab inside a song verse must parse."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from json2vpc import vpc_to_json, fix_vpc


def test_literal_newline_in_verse():
    vpc = '{Text:"Choir Book",Songs:[{Text:"Amazing Grace",Verses:[{Text:"Amazing grace how sweet\nthe sound that saved a wretch like me"}]}]}'
    data = vpc_to_json(vpc)
    assert data["Songs"][0]["Verses"][0]["Text"] == "Amazing grace how sweet\nthe sound that saved a wretch like me"


def test_literal_tab_and_cr():
    vpc = '{Text:"T",Songs:[{Text:"S",Verses:[{Text:"line1\tline2\rline3"}]}]}'
    data = vpc_to_json(vpc)
    assert data["Songs"][0]["Verses"][0]["Text"] == "line1\tline2\nline3"


def test_bare_keys_still_quoted():
    data = vpc_to_json('{Text:"T",Count:3,Ok:true}')
    assert data == {"Text": "T", "Count": 3, "Ok": True}


def test_bom_stripped():
    data = vpc_to_json('\ufeff{Text:"T",Songs:[]}')
    assert data["Text"] == "T"


def test_bytes_input_utf8_sig():
    raw = b'\xef\xbb\xbf{Text:"T",Songs:[]}'
    assert vpc_to_json(raw)["Text"] == "T"
