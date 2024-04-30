'''
Copyright (C) 2021 S[&]T, The Netherlands.

Common XML/JSON helper functions
'''

import datetime
import os
import re


def indent_xml(element, level=0):
    i = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = i + "  "
        if not element.tail or not element.tail.strip():
            element.tail = i
        for element in element:
            indent_xml(element, level + 1)
        if not element.tail or not element.tail.strip():
            element.tail = i
    else:
        if level and (not element.tail or not element.tail.strip()):
            element.tail = i


def json_remove_comments(json_like):
    """
    Removes C-style comments from *json_like* and returns the result.  Example::
        >>> test_json = '''\
        {
            "foo": "bar", // This is a single-line comment
            "baz": "blah" /* Multi-line
            Comment */
        }'''
        >>> remove_comments('{"foo":"bar","baz":"blah",}')
        '{\n    "foo":"bar",\n    "baz":"blah"\n}'
    """
    comments_re = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )

    def replacer(match):
        s = match.group(0)
        if s[0] == '/':
            return ""
        return s
    return comments_re.sub(replacer, json_like)


def remove_trailing_commas(json_like):
    """
    Removes trailing commas from *json_like* and returns the result.  Example::
        >>> remove_trailing_commas('{"foo":"bar","baz":["blah",],}')
        '{"foo":"bar","baz":["blah"]}'
    """
    trailing_object_commas_re = re.compile(
        r'(,)\s*}(?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    trailing_array_commas_re = re.compile(
        r'(,)\s*\](?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    # Fix objects {} first
    objects_fixed = trailing_object_commas_re.sub("}", json_like)
    # Now fix arrays/lists [] and return the result
    return trailing_array_commas_re.sub("]", objects_fixed)


def get_current_utc_datetime() -> datetime.datetime:
    """
    Helper method, returns the current UTC datetime.
    Can be overridden in tests using environment variable CURRENT_UTC_DATETIME=<some time>.
    """
    if 'CURRENT_UTC_DATETIME' in os.environ:
        return datetime.datetime.strptime(os.environ['CURRENT_UTC_DATETIME'], '%Y%m%dT%H%M%S').replace(tzinfo=datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)
