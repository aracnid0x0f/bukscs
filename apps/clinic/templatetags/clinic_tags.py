"""
apps/clinic/templatetags/clinic_tags.py
Custom template filters for the BUK Clinic app.
"""
from django import template

register = template.Library()


@register.filter(name="split")
def split_string(value, delimiter=","):
    """
    Split a string by a delimiter and return a list.
    Usage: {{ "a,b,c"|split:"," }}
    """
    return value.split(delimiter)