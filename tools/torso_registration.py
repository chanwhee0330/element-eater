"""Measure the torso independently of moving ears, hands and feet."""
from outline_registration import fit_outline

def fit_torso(image,element=None,expected=None):
    return fit_outline(image,expected,element)
