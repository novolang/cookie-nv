#!/usr/bin/env python3
"""Write tests/httpstate_tests.nv from the http-state test corpus.

The corpus is the IETF http-state working group's cookie parser suite,
https://github.com/abarth/http-state, commit 155e45c6.  Its
`tests/data/parser.json` lists, for each case, the `Set-Cookie` values a
server sends in the response to http://home.example.org:8888/cookie-parser
and the cookies the client then sends to /cookie-parser-result, or to the
URL in `sent-to`.  Its `tests/data/dates/examples.json` lists cookie-date
strings with the date each one denotes.

Usage:
    python3 tools/http_state.py <http-state checkout> > tests/httpstate_tests.nv
    novo fmt tests/httpstate_tests.nv

The corpus was written against RFC 6265.  The cases below are left out,
each for the reason given, and every other case is written into the
suite.
"""
import json
import os
import sys
from urllib.parse import urlsplit

# Cases the corpus disables itself, with a `DISABLED_` prefix, are left
# out without further reason.
LEFT_OUT = {
    # RFC 6265bis section 5.6 step 2 keeps a cookie with no `=` as a
    # cookie with an empty name, where RFC 6265 ignored it.  The corpus
    # expects these to be ignored.
    "0004": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "0023": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "0024": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "0025": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "0026": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "0027": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "0028": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "MOZILLA0014": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "MOZILLA0015": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "MOZILLA0016": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "MOZILLA0017": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    "NAME0033": "a pair with no `=` is a nameless cookie in RFC 6265bis",
    # RFC 6265bis section 5.6 keeps a cookie whose name is empty, where
    # RFC 6265 section 5.2 step 5 ignored it.
    "0021": "a cookie with an empty name is kept in RFC 6265bis",
    "CHROMIUM0009": "a cookie with an empty name is kept in RFC 6265bis",
    "CHROMIUM0010": "a cookie with an empty name is kept in RFC 6265bis",
    "CHROMIUM0012": "a cookie with an empty name is kept in RFC 6265bis",
    "MOZILLA0012": "a cookie with an empty name is kept in RFC 6265bis",
    "NAME0017": "a cookie with an empty name is kept in RFC 6265bis",
    "NAME0023": "a cookie with an empty name is kept in RFC 6265bis",
    "NAME0025": "a cookie with an empty name is kept in RFC 6265bis",
    "NAME0028": "a cookie with an empty name is kept in RFC 6265bis",
    "NAME0031": "a cookie with an empty name is kept in RFC 6265bis",
    "NAME0032": "a cookie with an empty name is kept in RFC 6265bis",
}

# With a second argument `report`, each jar case prints its answer when
# it differs from the corpus's instead of asserting, so a change can be
# reviewed against the whole corpus at once.
REPORT = len(sys.argv) > 2 and sys.argv[2] == "report"

HOME = ("home.example.org", "/cookie-parser")


def nv(s):
    """A Novo string literal."""
    out = []
    for ch in s:
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append('\\"')
        elif ch == '$':
            out.append('\\$')
        elif ch == '\t':
            out.append('\\t')
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append('\\x%02x' % ord(ch))
        else:
            out.append(ch)
    return '"' + ''.join(out) + '"'


def target(case):
    """The host and path the corpus sends the second request to."""
    to = case.get("sent-to")
    if to is None:
        return ("home.example.org", "/cookie-parser-result")
    parts = urlsplit(to)
    host = parts.hostname or "home.example.org"
    if parts.hostname:
        host = parts.netloc.split(':')[0]
    return (host, parts.path)


def expected(case):
    return "; ".join(
        c["value"] if c["name"] == "" else "%s=%s" % (c["name"], c["value"])
        for c in case["sent"])


def main():
    root = sys.argv[1]
    cases = json.load(open(os.path.join(root, "tests/data/parser.json")))
    dates = json.load(open(os.path.join(root, "tests/data/dates/examples.json")))
    w = sys.stdout.write
    w("// httpstate_tests.nv — the http-state working group's cookie parser\n")
    w("// corpus, and its cookie-date examples.\n")
    w("//\n")
    w("// Written by tools/http_state.py from https://github.com/abarth/http-state\n")
    w("// at commit 155e45c6.  Each case stores the corpus's `Set-Cookie` values\n")
    w("// in a jar as the response to http://home.example.org:8888/cookie-parser\n")
    w("// and compares the `Cookie` header the jar writes for the next request\n")
    w("// with the one the corpus expects.  The time is 2012-01-01, when the\n")
    w("// corpus's future dates were in the future.  Cases the corpus disables,\n")
    w("// and the ones RFC 6265bis answers differently, are listed with their\n")
    w("// reason in the tool.\n\n")
    w("use std.test\nuse civil\nuse cookieparse\nuse cookiejar\nuse cookiewrite\n\n")
    w("// The entries of the Public Suffix List the corpus's hosts reach.\n")
    w("fn suffix(d: Str) -> Bool\n")
    w("    d == \"org\" or d == \"com\" or d == \"net\"\n\n")
    w("fn now() -> civil.CivilDateTime\n")
    w("    civil.datetime(civil.date(2012, 1, 1)!, civil.midnight())\n\n")
    w("// The Cookie header the jar writes after storing `received`.\n")
    w("fn run(received: [Str], host: Str, path_value: Str) -> Str\n")
    w("    var j = cookiejar.jar(cookiejar.rules_with_suffixes(suffix))\n")
    w("    for h in received\n")
    w("        let spec = cookieparse.parse_set_cookie_lenient(h).0\n")
    w("        match cookiejar.store(j, spec, %s, %s, now())\n" % (nv(HOME[0]), nv(HOME[1])))
    w("            Ok(next) => j = next\n")
    w("            Err(_)   => ()\n")
    w("    cookiejar.header_for(j, host, path_value, false, now())\n\n")
    if REPORT:
        w("fn check(t: Str, received: [Str], host: Str, path_value: Str, want: Str) [io]\n")
        w("    let got = run(received, host, path_value)\n")
        w("    if got != want\n")
        w("        println(\"${t}: got [${got}] want [${want}]\")\n\n")
    kept = [c for c in cases
            if not c["test"].startswith("DISABLED_") and c["test"] not in LEFT_OUT]
    groups = {}
    for c in kept:
        prefix = c["test"].rstrip("0123456789").lower().rstrip("_") or "general"
        groups.setdefault(prefix, []).append(c)
    for g in sorted(groups):
        w("@test\nfn test_http_state_%s() [io]\n" % g.replace("-", "_"))
        for c in groups[g]:
            host, path = target(c)
            recv = "[" + ", ".join(nv(r) for r in c["received"]) + "]"
            if not c["received"]:
                recv = "[]"
            w("    test.case(%s)\n" % nv(c["test"]))
            if REPORT:
                w("    check(%s, %s, %s, %s, %s)\n" % (nv(c["test"]), recv, nv(host), nv(path), nv(expected(c))))
            else:
                w("    test.assert(run(%s, %s, %s) == %s)\n" % (recv, nv(host), nv(path), nv(expected(c))))
        w("\n")
    w("@test\nfn test_http_state_dates() [io]\n")
    for d in dates:
        w("    test.case(%s)\n" % nv(d["test"]))
        if d["expected"] is None:
            w("    match cookieparse.parse_expires(%s)\n" % nv(d["test"]))
            w("        Ok(_)  => test.assert(false)\n")
            w("        Err(_) => test.assert(true)\n")
        else:
            w("    match cookieparse.parse_expires(%s)\n" % nv(d["test"]))
            w("        Ok(dt) => test.assert(cookiewrite.format_expires(dt) == %s)\n" % nv(d["expected"]))
            w("        Err(_) => test.assert(false)\n")
    print(len(kept), "cases kept", file=sys.stderr)


main()
