#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""Shorthands for regular expression matching."""

import re


def _first_match(string: str, compiled: "re.Pattern"):  # noqa:ANN202
    match = compiled.search(string)
    if match is None and compiled.groups <= 1:
        return None
    elif match is None:
        return (None,) * compiled.groups
    elif compiled.groups == 0:
        return string
    elif compiled.groups == 1:
        return match.groups()[0]
    else:
        return match.groups()


def any_match(string: str, regex: str, flags: int = re.M) -> list:
    r"""
    Match the given string against the given regex.

      - If no match is found, this function returns an empty list.

      - If a match is found and the regular expression has no groups,
        a list of matching lines returned.

      - If a match is found and the regular expression has one group,
        a list of matching strings is returned.

      - If a match is found and the regular expression has multiple groups,
        a list containing tuples of matching strings is returned.

    This behavior ensures that the following can never fail::

        foo = '1 uno\\n2 due'
        for m in any_match(foo, r'aaa'):         # Returns []
            print(m)

        for m in any_match(foo, r'\\S+'):         # Returns ['1 uno', '2 due']
            print(m)

        for m in any_match(foo, r'(aaa)'):       # Returns []
            print(m)

        for m in any_match(foo, r'(\\S+)'):       # Returns ['1', '2']
            print(m)

        for one, two in any_match(foo, r'(aaa) (\\S+)'): # Returns []
            print(m)

        for one, two in any_match(foo, r'(\\S+) (\\S+)'): # Returns [('1', 'uno'), ('2', 'due')]
            print(m)

    :type  string: string
    :param string: The string that is matched
    :type  regex: string
    :param regex: A regular expression.
    :type  flags: int
    :param flags: The flags for compiling the regex; e.g. re.I
    :rtype:  list[string|tuple]
    :return: A list of strings, or a list of tuples.
    """
    compiled = re.compile(regex, flags)
    results = []
    if compiled.groups <= 1:
        for line in string.split("\n"):
            match = _first_match(line, compiled)
            if match is None:
                continue
            results.append(match)
    else:
        for line in string.split("\n"):
            match = _first_match(line, compiled)
            if match[0] is None:
                continue
            results.append(match)
    return results
