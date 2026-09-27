# Changelog

All notable changes to cookie-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## 0.1.0 — 2026-09-28

The first implementation of the interface published as 0.0.1: the
attribute rules, both parsers, the writers, the storage model and
signed and encrypted values.

### Added

- `cookieattr.browser_rules` answers the rules a browser applies to a
  cookie it has already parsed: the two prefixes, `SameSite=None` and
  `Partitioned`, each of which needs `Secure`.  `check_attrs` is the
  name's grammar, the `Domain`'s, the `Path`'s, then these.
- `cookieparse.value_error` answers the first byte of a value the
  `cookie-value` grammar refuses.
- `tests/httpstate_tests.nv` holds 195 cases of the http-state working
  group's cookie parser corpus and its 15 cookie-date examples, written
  by `tools/http_state.py`.  The tool lists the cases RFC 6265bis
  answers differently.
- `tests/differential_tests.nv` checks the `Cookie` parser against
  Python's `http.cookies` and `format_expires` against its
  `email.utils`, and is written by `tools/differential.py`.

### Changed

These change what code written against 0.0.x observes.

- `parse_set_cookie_lenient` follows RFC 6265bis section 5.6: a pair
  with no `=` is a cookie with an empty name, and a header with a
  control byte other than a tab is ignored whole.
- `parse_set_cookie` refuses whatever `cookiewrite.set_cookie` would
  refuse to write, the prefix rules included, as well as anything the
  lenient reading ignores.
- `cookiewrite.quote_value` never adds quotes.  The quoted form of the
  `cookie-value` grammar admits the same bytes as the bare form, so a
  legal value is answered as written and any other is refused.
- `cookiejar.domain_matches` compares ignoring ASCII case and keeps a
  trailing dot, as a browser does with a `Domain` attribute.
  `canonical_host` is the call that removes one.
- `cookiejar.store` reads the `Domain` as `cookieparse` answers it,
  without a leading dot, and caps a lifetime at 400 days (RFC 6265bis
  section 5.7).  A stored `Max-Age` becomes an expiry time.
- `cookiejar.jar_rules_are_unsafe` answers `true` when the public-suffix
  test calls any of `com`, `net`, `org` and `co.uk` not a public
  suffix.
- An empty key set signs nothing: `cookieseal.sign` answers the empty
  string.

### Toolchain

- The toolchain floor is 0.14.0, and the dependencies are calendar-nv
  `^0.2.0` and crypto-nv `^0.1.6`.  The bodies target novo 0.14.0 and
  carry no workaround for a compiler defect.

## 0.0.2 — 2026-09-15

README rewritten to the package README style guide (docs/writing-a-readme.md); no change to the interface.

## 0.0.1 — 2026-09-11

The **interface**: every signature and every effect row, and no bodies.
`stability = "draft"`, and the release is recorded `implemented = false`.

### Added

- `cookieattr` — `CookieAttrs` as a value, `CookiePrefix` read off the
  name, and `check_attrs` as the rule set a browser applies silently.
- `cookieparse` — a `Cookie` header as spans and a `Set-Cookie` as a
  value, with a strict parser for a server's own output and a lenient
  one for somebody else's.
- `cookiewrite` — every writer answering a `Result`, plus
  `delete_cookie`, which keeps the attributes the cookie was set with
  because the browser keys on that triple.
- `cookiejar` — RFC 6265 § 5.3's storage algorithm and § 5.4's send
  order, with the clock as an argument and the public-suffix question as
  a function.
- `cookieseal` — signed and encrypted cookies, with the cookie name
  authenticated and key rotation in the type.

### Known

- **`check_attrs` is the load-bearing interface.** Five attribute
  combinations make a browser drop a cookie without reporting anything,
  and all five are refused here rather than emitted.
- **Every writer answers a `Result`.** A cookie library whose
  `to_string` cannot fail emits headers a browser drops.
- **The cookie name is in the MAC and in the associated data**, so a
  signed or encrypted value cannot be moved between cookies.
- **The cipher is an argument** — `CookieCipher` is a pair of named
  functions — because there is no AEAD on the registry yet.
- **Key rotation is a list, newest first**, and `verify` answers which
  key matched.
- **The Public Suffix List is a function the caller supplies.**
  `no_public_suffixes()` is the honest default and
  `jar_rules_are_unsafe` says so.
- **The jar has no clock.** Expiry compares against a time the caller
  passes in, which is what keeps the package `[]`.
- **No `@tier(embedded)` claim.** A jar is a growable list.

### Design notes

Public type names are unique across a whole assembly, dependencies
included, so the names here are prefixed where the obvious name would
collide. `CookieAttrs` rather than `Options`, `CookiePair` and
`CookieSpec` rather than one `Cookie`, `CookieJar` rather than `Jar`,
`CookieSpan` because url-nv publishes `Span`, `CookieKeys` and
`CookieCipher` because `Key` and `Cipher` belong to every cryptography
package, and `CookieLife` because `Duration` is a standard library
type. The modules are `cookieattr`, `cookieparse`, `cookiewrite`,
`cookiejar` and `cookieseal` for the same reason: `parse`, `write` and
a bare `cookie` are names other packages will want.

Parsing is asymmetric on purpose. `cookieparse.parse_header` answers
spans into the caller's string and `parse_set_cookie` copies, because a
server reads many cookies and keeps none while a client reads one and
keeps it.
