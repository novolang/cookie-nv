# Changelog

All notable changes to cookie-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

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
