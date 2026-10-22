"""Reported-statistic syntax shared by extraction and recomputation."""
import re

NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
# Do not accept a numeric prefix of a malformed or unsupported expression.
END_NUMBER = r"(?![\w.])"
P_VALUE = rf"\s*,?\s*p\s*([=<>])\s*({NUMBER}){END_NUMBER}"
_T = re.compile(rf"\bt\s*\(\s*({NUMBER})\s*\)\s*=\s*({NUMBER}){P_VALUE}", re.I)
_F = re.compile(rf"\bF\s*\(\s*({NUMBER})\s*,\s*({NUMBER})\s*\)\s*=\s*({NUMBER}){P_VALUE}", re.I)
_R = re.compile(rf"\br\s*\(\s*({NUMBER})\s*\)\s*=\s*({NUMBER}){P_VALUE}", re.I)
_CHI2 = re.compile(
    rf"(?:χ²|χ2|chi\s*-?\s*square|chi2)\s*\(\s*({NUMBER})"
    rf"\s*(?:,\s*N\s*=\s*\d+)?\s*\)\s*=\s*({NUMBER}){P_VALUE}", re.I)
_Z = re.compile(rf"\bz\s*=\s*({NUMBER}){P_VALUE}", re.I)
TEST_PATTERNS = (_T, _F, _R, _CHI2, _Z)
