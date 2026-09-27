#!/usr/bin/env python3
"""Write tests/differential_tests.nv from Python's standard library.

Two second opinions, each used where it and RFC 6265bis agree:

- `http.cookies.SimpleCookie` reads each `Cookie` header below.  A
  header is kept when Python read every `name=value` piece in it, since
  Python drops the whole header at the first piece it refuses, and each
  cookie's value, with its quotes removed, is compared with
  `cookieparse.get_str` followed by `cookieparse.unquote`.  Python keeps
  the last of two cookies with one name and RFC 6265bis the first, so a
  header repeating a name is not used.
- `email.utils.format_datetime(..., usegmt=True)` writes the RFC 1123
  date of RFC 9110 section 5.6.7, which is the one form RFC 6265bis
  section 4.1.1 allows a server's `Expires`.  Each date below is written
  by Python and compared with `cookiewrite.format_expires`, and the text
  is read back with `cookieparse.parse_expires`.

Usage:
    python3 tools/differential.py > tests/differential_tests.nv
    novo fmt tests/differential_tests.nv
"""
import datetime
import email.utils
import http.cookies
import random
import sys

HEADERS = [
    "sid=abc",
    "sid=abc; theme=dark",
    "a=1; b=2; c=3",
    "token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc-_",
    "path=/a/b; q=x:y",
    'quoted="hello"',
    "  spaced  =  value  ; next=1",
    "empty=; other=x",
    "b64=YWJjZA==",
    "n1=v1;n2=v2",
    "__Host-sid=x; __Secure-id=y",
    "k=a!b#c$d%e&f'g*h+i-j.k^l_m`n|o~p",
]


def nv(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$') + '"'


def main():
    w = sys.stdout.write
    w("// differential_tests.nv — Python's http.cookies and email.utils as a\n")
    w("// second opinion.\n//\n")
    w("// Written by tools/differential.py with Python %s.  The tool's\n" % sys.version.split()[0])
    w("// docstring says which cases are used and why.\n\n")
    w("use std.test\nuse civil\nuse cookieparse\nuse cookiewrite\n\n")
    w("@test\nfn test_python_http_cookies_reads_the_same_values() [io]\n")
    for h in HEADERS:
        pieces = [p for p in h.split(";") if p.strip()]
        names = [p.split("=", 1)[0].strip() for p in pieces]
        c = http.cookies.SimpleCookie()
        c.load(h)
        if len(c) != len(pieces) or len(set(names)) != len(names):
            continue
        w("    test.case(%s)\n" % nv(h))
        for name, morsel in c.items():
            w("    test.assert(cookieparse.unquote(cookieparse.get_str(%s, %s) ?? \"<absent>\") == %s)\n"
              % (nv(h), nv(name), nv(morsel.value)))
        w("    test.assert(cookieparse.count(%s) == %d)\n" % (nv(h), len(c)))
    w("\n@test\nfn test_python_email_utils_writes_the_same_dates() [io]\n")
    rng = random.Random(6265)
    days = [datetime.datetime(1970, 1, 1), datetime.datetime(1994, 11, 6, 8, 49, 37),
            datetime.datetime(2000, 2, 29, 23, 59, 59), datetime.datetime(2038, 1, 19, 3, 14, 8),
            datetime.datetime(9999, 12, 31, 23, 59, 59)]
    for _ in range(20):
        days.append(datetime.datetime(1601, 1, 1) + datetime.timedelta(seconds=rng.randrange(0, 13_000_000_000)))
    for d in days:
        text = email.utils.format_datetime(d.replace(tzinfo=datetime.timezone.utc), usegmt=True)
        w("    test.case(%s)\n" % nv(text))
        w("    let d%d = civil.datetime(civil.date(%d, %d, %d)!, civil.time_of(%d, %d, %d, 0)!)\n"
          % (days.index(d), d.year, d.month, d.day, d.hour, d.minute, d.second))
        w("    test.assert(cookiewrite.format_expires(d%d) == %s)\n" % (days.index(d), nv(text)))
        w("    match cookieparse.parse_expires(%s)\n" % nv(text))
        w("        Ok(back) => test.assert(civil.compare_datetime(back, d%d) == 0)\n" % days.index(d))
        w("        Err(_)   => test.assert(false)\n")


main()
