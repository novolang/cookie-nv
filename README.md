# cookie-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`. Installing this package works;
calling it panics with `not implemented`.

## What this is

RFC 6265bis in both directions, sans-IO: a `Cookie` header read without
copying it, a `Set-Cookie` written with the combinations a browser
silently drops **refused**, a jar with the storage model's boundary
rules as arithmetic, and signed and encrypted cookies whose cipher the
caller supplies.

- `cookieattr` — the attributes, and the rules that make a set legal;
- `cookieparse` — both headers read, one tolerantly and one strictly;
- `cookiewrite` — `Set-Cookie`, and the header that deletes a cookie;
- `cookiejar` — domain, path and expiry, with the clock as an argument;
- `cookieseal` — signed and encrypted, with key rotation in the type.

```
novo pkg add cookie-nv
novo pkg build
novo test
```

## The one example that will work

```novo ignore
use cookieattr
use cookiewrite

// A session cookie that a browser will actually keep.
fn session_header(token: Str) -> Str
    match cookiewrite.set_cookie("__Host-sid", token, cookieattr.defaults())
        Ok(h)  => h
        Err(_) => ""
```

## The load-bearing interface: `check_attrs`

```novo ignore
pub fn check_attrs(name: Str, a: CookieAttrs) -> [CookieError] []
```

A `Set-Cookie` whose attributes disagree with each other is not an error
anybody ever sees. The browser ignores the cookie, the next request
arrives without it, and what the server observes is *"no session"*
rather than *"a cookie I wrote wrongly"* — three layers from the line
that caused it.

Every one of these is a shipped bug and a comparison this function
makes:

| written | what a browser does |
| --- | --- |
| `__Host-sid` with `Domain=example.com` | ignores the cookie |
| `__Host-sid` with `Path=/admin` | ignores the cookie — `Path=/` is required |
| `__Secure-sid` without `Secure` | ignores the cookie |
| `SameSite=None` without `Secure` | ignores the cookie, since Chrome 80 |
| `Partitioned` without `Secure` | ignores the cookie |

So **every writer in `cookiewrite` answers a `Result`**, which is the
package's main argument: a cookie library whose `to_string` cannot fail
is one that emits headers a browser drops. The check costs four
comparisons. `set_cookie_unchecked` exists for the proxy passing a
header through and for the test that wants a bad one, and its name is
the disclosure.

`check_attrs` answers **every** problem rather than the first, because a
caller who got one attribute wrong usually got two, and fixing them one
at a time is two deploys. `apply_prefix` is the repair published beside
the check — so a caller who wants a `__Host-` cookie and does not want
to remember three rules never has to turn the check off.

## Why the prefixes matter more than they look

A cookie set by `evil.example.com` for `Domain=example.com` is sent to
`bank.example.com`, and `bank.example.com` **cannot tell it apart from
one it set itself**. Cookies have no origin, only a domain, and that has
been true since 1994.

`__Host-` is the fix, and it is the only host-locking cookies have: a
browser accepts such a cookie only with `Secure`, `Path=/` and no
`Domain`. A library that writes `__Host-` cookies with a `Domain` has
produced a name that *looks* locked and is not there at all — which is
worse than not using the prefix, because the name is what a reviewer
reads.

## Signed and encrypted are two different promises

| | signed | encrypted |
| --- | --- | --- |
| the client can read the value | **yes** | no |
| the client can change it | no | no |
| right for | a user id, a role, a flag | an internal id, a third-party token |

A library that offered one function called `secure` would be offering
the wrong one to half its callers. `sign`/`verify` and
`encrypt`/`decrypt` say which promise is being made at the call site.

**The cookie name is authenticated**, and that is the part libraries
miss. A MAC over the value alone lets a client move a value between
cookies: a `role=user` signed for `role` is a valid `admin` cookie if
the server reads `admin` with the same key. So the name goes into the
MAC and into the AEAD's associated data every time, and `verify` takes
the name it **expects** rather than reading one out of the input.

**The cipher is an argument, not a dependency.** There is no AEAD on the
registry yet — `chacha20-nv` is a planned row — and a cookie library
that waited for one would be a cookie library nobody could use to
encrypt a cookie. `CookieCipher` is a pair of **named** functions the
caller supplies, plus three lengths; this package composes them with the
key derivation, the encoding and the name binding. Named functions and
not lambdas, because a lambda captures, and a captured key is a key
whose lifetime nobody can see at the call site.

**Key rotation is in the type.** `CookieKeys` is a list, newest first:
the first key signs, every key verifies, and `verify` answers **which**
key matched. That is what lets a key be rotated without logging
everybody out — and the index is the number that says when the old key
can come off the list. A single-key API cannot express the state at all,
which is why "we rotated the key and everybody was logged out" happens.

## The public suffix list is not here, and that is a decision

RFC 6265 § 5.3 step 5 says a browser must reject a `Domain` that is a
public suffix — `Domain=com`, `Domain=co.uk`, `Domain=github.io` —
because accepting one would let any site set a cookie for every site
under it.

Answering that needs the Public Suffix List: about 220 KB of data with
its own update cadence, whose correctness is a moving fact **about the
world** rather than about HTTP. Compiling it in would make this package
stale the day it published, and would make a jar's behaviour depend on
when its dependency was last released.

So the jar takes the question as a function.
`CookieJarRules.is_public_suffix` is a `fn(Str) -> Bool` the caller
supplies. `no_public_suffixes()` is the honest default — it answers
`false` for everything, so the jar accepts `Domain=co.uk`, and
`jar_rules_are_unsafe` answers `true` so a caller can assert on it at
start-up rather than discover it in an incident.

## The matching rules are boundaries, and the obvious code gets them wrong

| | matches | does **not** match |
| --- | --- | --- |
| `domain_matches(host, "example.com")` | `example.com`, `a.example.com` | `notexample.com` — the `ends_with` bug |
| `path_matches(request, "/foo")` | `/foo`, `/foo/`, `/foo/bar` | `/foobar` — the `starts_with` bug |
| an IP host | itself | anything else; `1.2.3.4` has no subdomains |

Both are published rather than kept inside the jar, because a server has
the same questions a client does and two copies of a boundary rule is
two places for the boundary to be wrong.

`default_path("/a/b/c")` is `/a/b` — everything up to the last slash —
which is why `cookieattr.defaults()` sets `Path=/` explicitly. The
browser's own default scopes a cookie to a directory, and almost no
caller meant that.

## Nothing is copied on the way in, and everything is on the way out

`cookieparse.parse_header` answers spans into the header string the
caller already holds, so reading one cookie out of a request with eight
of them copies one value. `parse_set_cookie` copies, and the asymmetry
is deliberate: **a server reads many cookies and keeps none, a client
reads one and keeps it.**

The two headers are not the same grammar, and conflating them is the
first mistake a cookie library makes. `Cookie:` is a list of pairs with
no attributes at all — a browser never tells a server what it knows
about a cookie, not its domain, not its path, not its expiry.
`Set-Cookie:` is one pair followed by attributes.

`parse_header` **never fails**: a pair it cannot read is skipped and
counted. RFC 6265bis § 5.5 has a browser do the same, and a server that
refused a whole header because one pair was odd would log out every user
whose browser had a stale cookie from another application on the same
domain. `parse_set_cookie` **does** answer a `Result`, because that is
the header a server writes and a program reading its own output should
hear about a bug in it.

## The layer, and the clock that is not here

`core` — no effects. The two places a cookie library would otherwise
reach for a host are the clock and the cipher, and neither is here:
`Expires` is calendar-nv's `CivilDateTime`, which the caller read off
its own clock, and encryption is a function the caller supplies. A jar
expires cookies against a time it is **handed**, which is what keeps the
package `[]` and what makes a jar testable — a test that wants to see a
cookie expire hands the jar a later time rather than sleeping.

**No `@tier(embedded)` claim, and none is intended.** A jar is a
growable list and a cookie header is a string. A device that sets one
cookie formats one string, which is not what this package is for. The
audit's `core-embedded` row passes as *makes no device claim*.

**calendar-nv, for `Expires` and nothing else.** RFC 6265 § 5.1.1
defines its own date parser — five formats, a two-digit-year rule, and a
deliberate tolerance for the spellings Netscape shipped in 1994 — and
what it produces is a civil datetime. That parser lives here rather than
in calendar-nv, because calendar-nv's own parsers would correctly refuse
most of what browsers accept.

**crypto-nv, for the HMAC under a signed cookie.**
`hashing.hmac_sha256` is the whole of it. Building a MAC out of a hash
by hand is how a length-extension bug gets shipped.

## Where the names come from

Public type names are unique across the whole assembly, dependencies
included.

| here | the obvious name | why not |
| --- | --- | --- |
| `CookieAttrs` | `Attributes`, `Options` | generic; every package wants `Options` |
| `CookiePair`, `CookieSpec` | `Cookie` | a bare `Cookie` is the name a session package and a client package both want, and the two halves here are genuinely different types |
| `CookieJar` | `Jar` | generic |
| `CookieSpan` | `Span` | url-nv publishes `Span`, and it is a module name in use |
| `CookieKeys` | `Key`, `KeyRing` | `Key` will collide with every crypto package on the grid |
| `CookieCipher` | `Cipher`, `Aead` | the same |
| `CookieLife` | `Expiry`, `Lifetime` | generic, and `Duration` is a standard library type |
| module `cookieattr`, `cookiejar`, … | `cookie`, `jar`, `parse`, `write` | the last three are names other packages will want, and a bare `cookie` would collide with a future session package's own module |

## The reference implementation

**the `cookie` crate** for the signed and private jar shape, the key
derivation from one master, and the `CookieBuilder` vocabulary.
**Python's `http.cookies`** for the observation that the two headers are
two grammars, and for how much tolerance a real parser needs.
**RFC 6265bis** for everything normative: § 4.1.1 for the grammars,
§ 5.1.3 and § 5.1.4 for the matching boundaries, § 5.3 for the storage
algorithm, § 5.4 for the send order, and § 4.1.3 for the prefixes.

The oracles are RFC 6265bis's own examples, the `cookie` crate's signed
and private jar suites, and the `http-cookies` test corpus's date cases
— which is where the five `Expires` spellings come from.

Deliberately left out, and where it goes instead:

- **The Public Suffix List.** A function the caller supplies; see above.
- **Sessions.** `session-nv`'s row on the plan. A session is a cookie
  plus a store, and the store is `host`.
- **A cipher.** `chacha20-nv`'s row. `CookieCipher` is the seam.
- **Randomness.** A `core` package has none, so the nonce and the key
  are the caller's. A nonce this package invented would be a constant,
  and a repeated nonce breaks every AEAD there is.
- **Percent-encoding a value.** url-nv's `pct`. A cookie value's
  grammar allows `/`, `:` and `=`, which is why a JWT goes in one
  unencoded and an encoder would be doing harm.
- **Reading a jar off disk, or writing one.** `core`, so there is
  nothing to read with. `entries` and `jar_from` are the seam, and
  every field an entry needs is public for that reason.

## Status

Every function is `todo()`. Three suites, all red, all for the same
reason — every assertion reaches `not implemented: cookie-nv.<fn>`,
which is the expected result until the bodies land.

```
novo test --isolate tests/cookieattr_tests.nv   # the combinations a browser drops
novo test --isolate tests/cookiejar_tests.nv    # both parsers, and the matching boundaries
novo test --isolate tests/cookieseal_tests.nv   # signing, encryption, and a rotated key
```

`novo doc` renders and its examples compile.
