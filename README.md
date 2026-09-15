# cookie-nv

An HTTP cookie is a name and a value that a server asks a client to
store and send back on later requests. The rules for writing one,
reading one and deciding which requests it goes on are specified in
[RFC 6265bis](https://datatracker.ietf.org/doc/draft-ietf-httpbis-rfc6265bis/).
This package brings both directions of that specification to
novo-lang: the `Cookie` request header, the `Set-Cookie` response
header, the client-side storage model, and cookies that are signed or
encrypted. [session-nv](https://novo-lang.org/packages/session-nv) is
built on it.

**Status: NOT IMPLEMENTED — interface only.** Every function is
declared with its full signature, but every body is a `todo()` that
panics when called. The package is published so its design can be
reviewed and depended on before it is implemented. Version 0.1.0 will
be the first working release.

## What a cookie is

A server sends a **`Set-Cookie`** response header. It carries one name,
one value and a list of **attributes** that say how long the client
keeps the cookie and which requests it goes on. A client sends a
**`Cookie`** request header. It carries a list of names and values and
no attributes at all, so a server never learns what a client knows
about a cookie it stored. The two headers are two grammars, defined in
RFC 6265bis section 4.1.1 and section 4.2.1.

The attributes are these.

| Attribute | What it says |
| --- | --- |
| `Domain` | The host and its subdomains the cookie is sent to. Absent means this host only. |
| `Path` | The path prefix the cookie is sent under. |
| `Expires` | The date after which the client discards the cookie. |
| `Max-Age` | The seconds from now after which the client discards it. It wins over `Expires`. |
| `Secure` | The cookie is sent over HTTPS only. |
| `HttpOnly` | Scripts in the page cannot read the cookie. |
| `SameSite` | Whether the cookie goes on requests started by another site. |
| `Partitioned` | The cookie is separate per embedding site. |

A cookie with neither `Expires` nor `Max-Age` is a **session cookie**.
The client discards it when it closes, and no header can say when that
is.

Cookies have no origin, only a domain. A cookie set by one host for a
parent domain is sent to every other host under that domain, and the
receiver cannot tell it from one it set itself. The **name prefixes**
of section 4.1.3 are the answer. A name beginning `__Secure-` is
accepted only with `Secure`. A name beginning `__Host-` is accepted
only with `Secure`, with `Path=/` and with no `Domain`, which locks the
cookie to the single host that set it.

A client keeps its cookies in a **jar**. Section 5.3 is the algorithm
for storing one and section 5.4 is the order for sending them. Two
boundary rules decide which cookies a request carries.
**Domain-matching** (section 5.1.3) holds when the request host equals
the cookie's domain or ends with a dot and that domain.
**Path-matching** (section 5.1.4) holds when the request path equals
the cookie's path, or continues it at a `/` boundary.

A **signed** cookie carries a message authentication code, a short tag
computed under a secret key, so the client can read the value and
cannot change it. An **encrypted** cookie is sealed under an
authenticated encryption scheme, so the client can neither read it nor
change it. Both are ordinary cookie values once written, and neither is
part of RFC 6265bis.

Every function in this package performs no input and no output. It
reads no clock, opens no socket and holds no key store. A time and a
cipher arrive as arguments.

## Install

```
novo pkg add cookie-nv
```

## Example

```novo
use cookieattr
use cookieparse
use cookiewrite

fn main() [io]
    // The `Cookie` header as it arrived on the request.
    let header = "sid=abc123; theme=dark"

    // Read one value out of it. Nothing else in the header is copied.
    match cookieparse.get_str(header, "sid")
        Some(v) => println("the session is ${v}")
        None    => println("the request carried no session cookie")

    // The attributes a session cookie needs: `Path=/`, `Secure`,
    // `HttpOnly`, `SameSite=Lax`, no `Domain`, no expiry.
    let a = cookieattr.defaults()

    // Write the `Set-Cookie` header. A combination a browser would drop
    // is refused here instead of being sent.
    match cookiewrite.set_cookie("__Host-sid", "abc123", a)
        Ok(h)  => println(h)
        Err(e) => println(e.message())
```

Build and test with `novo pkg build` and `novo test`. Today `novo test`
fails on purpose: every test reaches a
`not implemented: cookie-nv.<module>.<fn>` panic. The tests are the
specification the implementation will have to satisfy.

## What the package contains

| Module | Contents |
| --- | --- |
| `cookieattr` | The attributes as a value, the name prefixes, the error type, and the check that says whether a combination is one a client accepts. |
| `cookieparse` | Reading: the `Cookie` header as spans over the caller's string, and `Set-Cookie` as a value, strictly or tolerantly. |
| `cookiewrite` | Writing: a `Set-Cookie` header, the header that deletes a cookie, and a `Cookie` header from a list of pairs. |
| `cookiejar` | The client storage model: storing, sending, expiring, and the domain and path matching rules on their own. |
| `cookieseal` | Signed and encrypted cookie values, key derivation from one master secret, and key rotation. |

## How to choose an entry point

**`cookieparse.get` and `get_str` read one cookie out of a request.**
`get` answers a `CookieSpan`, a start and a length into the header
string the caller already holds, so reading one value out of a header
with eight cookies in it copies one value. `get_str` answers the value
as a new string. Use the span form on a request path, and the string
form when the value outlives the header.

**`cookieparse.parse_set_cookie` reads a header a program wrote
itself**, and answers a `Result`, so a bug in that program is reported.
**`parse_set_cookie_lenient` reads a header somebody else wrote.** It
answers the cookie it managed to read and a list of what was wrong
with it.

**`cookiewrite.set_cookie` writes a header and checks it.**
`set_cookie_unchecked` writes the same header and checks nothing, for a
proxy passing a header through and for a test that wants a bad one.
`set_cookie_into` appends to a buffer the caller owns, and
`set_cookie_len` gives the length without writing anything.

**`cookiejar` is for a client**, such as an HTTP client following
redirects across hosts. A server that sets and reads its own cookies
needs `cookieparse` and `cookiewrite` and nothing else.

**`cookieseal.sign` and `verify` are for a value the client may read.**
`encrypt` and `decrypt` are for a value it may not. See rule 7.

## The rules a user needs

1. **Five attribute combinations make a client drop a cookie without
   reporting anything.** A `__Host-` name with a `Domain`, a `__Host-`
   name whose `Path` is not `/`, a `__Secure-` or `__Host-` name
   without `Secure`, `SameSite=None` without `Secure`, and
   `Partitioned` without `Secure`. The server then sees a request with
   no cookie rather than an error. RFC 6265bis sections 4.1.3 and
   5.4.7 are the rules. `cookieattr.check_attrs` reports all of them
   that apply, and every writer in `cookiewrite` answers a `Result`
   rather than emitting one.
2. **`check_attrs` answers every problem, not the first.**
   `cookieattr.apply_prefix` is the repair beside the check: it returns
   the attributes a name's prefix requires, so a caller who wants a
   `__Host-` cookie need not remember the three rules.
3. **`SameSite` absent is not `SameSite=Lax`.** Absent means the
   client's own default applies, and that default has changed over
   time. A cookie that must travel cross-site has to say
   `SameSite=None` and `Secure` (section 5.4.7).
4. **An absent `Path` is not `Path=/`.** With no `Path` the client
   computes a default from the request path: everything up to the last
   `/` (section 5.1.4). That scopes the cookie to a directory, which is
   almost never what the caller meant, so `cookieattr.defaults()` sets
   `/` explicitly. `cookiejar.default_path` is that computation.
5. **A cookie is identified by name, domain and path together**
   (section 5.3). Deleting one means sending a `Set-Cookie` with the
   same three and an expiry in the past. `cookiewrite.delete_cookie`
   takes the attributes the cookie was set with for that reason.
6. **The matching rules are boundary comparisons, and a prefix test is
   the bug.** `example.com` domain-matches `a.example.com` and does not
   match `notexample.com`. `/foo` path-matches `/foo/bar` and does not
   match `/foobar`. An IP address matches only itself, because it has
   no subdomains. `cookiejar.domain_matches`, `path_matches` and
   `host_is_ip` are those three rules, published on their own because a
   server asks the same questions a client does.
7. **Signed and encrypted are two different promises.** A signed value
   is readable by the client and cannot be changed by it. An encrypted
   value is neither readable nor changeable. Choose by whether the
   client is allowed to know the value.
8. **The cookie's name is authenticated.** It goes into the MAC and
   into the associated data of the encryption, and `verify` and
   `decrypt` take the name the caller expects rather than reading one
   out of the input. Without this a value signed for one cookie is a
   valid value for another read under the same key.
9. **The signing and encryption keys must be different bytes.**
   `cookieseal.derive` turns one master secret into the pair. Using one
   key for a MAC and for a cipher is a key reuse across primitives.
10. **The key set is a list, newest first.** The first key signs, every
    key verifies, and `verify` answers which key matched. Rotating a
    key without that list logs every user out at once.
11. **The nonce for `encrypt` is the caller's.** This package has no
    source of randomness, and a nonce it invented would be a constant.
    A repeated nonce under one key breaks every authenticated
    encryption scheme. `cookieseal.nonce_len` says how many bytes to
    bring.
12. **`cookieparse.parse_header` never fails.** A pair it cannot read
    is skipped and counted, which is what section 5.5 has a client do.
    A server that refused a whole header over one odd pair would log
    out every user carrying a stale cookie from another application on
    the same domain.
13. **A jar's public-suffix check is a function the caller supplies.**
    Section 5.3 step 5 says a `Domain` that is a public suffix, such as
    `co.uk`, must be rejected. `cookiejar.no_public_suffixes()` answers
    `false` for every name, so a jar built on it accepts `Domain=co.uk`,
    and `jar_rules_are_unsafe` answers `true` so a program can check at
    start-up. See "What is not included".
14. **A jar has no clock.** `store`, `cookies_for`, `prune` and
    `is_expired` all take the current time as a `CivilDateTime`
    argument.
15. **Reading a jar does not prune it.** `cookies_for` omits expired
    cookies and leaves them in place. `prune` is the call that removes
    them.

## Sizes and limits

| Quantity | Value |
| --- | --- |
| Signing and encryption key length | 32 bytes (`cookieseal.key_len`) |
| Master secret length | 32 bytes (`cookieseal.master_len`) |
| Nonce length | whatever the caller's cipher declares (`cookieseal.nonce_len`) |
| Sealed value encoding | base64url, no padding, tag first |
| Prefixes recognised | `__Secure-` and `__Host-`, compared case-sensitively |

## What is not included

- **The Public Suffix List.** It is about 220 KB of data with its own
  release cadence, and it describes the world rather than HTTP. A copy
  compiled in here would go stale between releases, so the question is
  a `fn(Str) -> Bool` the caller supplies.
- **A cipher.** There is no authenticated encryption package on the
  registry yet. `cookieseal.CookieCipher` is a pair of named functions
  and three lengths, so the caller chooses the primitive.
  [chacha20-nv](https://novo-lang.org/packages/chacha20-nv) is the
  planned one.
- **Randomness.** This package declares no effects, so it has no source
  of random bytes. Keys and nonces are the caller's.
- **A clock.** Times arrive as arguments. See rule 14.
- **Percent-encoding a cookie value.** A cookie value may contain `/`,
  `:` and `=`, so a token goes in unencoded. Use
  [url-nv](https://novo-lang.org/packages/url-nv) when a value needs
  escaping for some other reason.
- **Reading a jar from disk or writing one to it.** This package
  performs no input or output. `cookiejar.entries` and `jar_from` are
  the pair a caller serialises through, and every field of a
  `CookieEntry` is public for that reason.
- **Sessions.** A session is a cookie and a store.
  [session-nv](https://novo-lang.org/packages/session-nv) has both.
- **A build for a microcontroller.** A jar is a growable list and a
  header is a string, so this package makes no device claim.

## Related packages

- [session-nv](https://novo-lang.org/packages/session-nv) keeps
  server-side session state behind a cookie. Take it when the cookie
  carries an identifier for data the server holds. Take this package
  when you write and read the cookies yourself.
- [url-nv](https://novo-lang.org/packages/url-nv) parses URLs and
  percent-encodes. A jar is asked about a host and a path, and that is
  where they come from.
- [http-codec-nv](https://novo-lang.org/packages/http-codec-nv) reads
  and writes HTTP/1.1 messages. It hands over the header field values
  this package parses.
- [calendar-nv](https://novo-lang.org/packages/calendar-nv) is civil
  dates and times with no clock in them. `Expires` is one of its
  values. This package depends on it.
- [crypto-nv](https://novo-lang.org/packages/crypto-nv) is hashes and
  HMAC. The signed cookie's tag is its `hashing.hmac_sha256`. This
  package depends on it.
- [jwt-nv](https://novo-lang.org/packages/jwt-nv) and
  [paseto-nv](https://novo-lang.org/packages/paseto-nv) are signed
  token formats. Take one of them when the token travels somewhere
  other than a cookie, or when another party must verify it.

## Tests

```bash
novo test tests/cookieattr_tests.nv   # the combinations a client drops
novo test tests/cookiejar_tests.nv    # both parsers, and the matching boundaries
novo test tests/cookieseal_tests.nv   # signing, encryption, and a rotated key
```

The normative cases come from RFC 6265bis: section 4.1.1 for the
grammars, sections 5.1.3 and 5.1.4 for the matching boundaries,
section 5.3 for the storage algorithm, section 5.4 for the send order
and section 4.1.3 for the prefixes. The reference implementations are
Rust's `cookie` crate, for the shape of a signed and a private jar and
for the derivation of two keys from one master, and Python's
`http.cookies`, for how much tolerance a real parser needs. The five
`Expires` spellings of section 5.1.1 come from the `http-cookies` test
corpus.

The suite asserts that each of the five silently dropped combinations
is refused, that `notexample.com` does not domain-match `example.com`,
that `/foobar` does not path-match `/foo`, that a `Cookie` header with
one bad pair still yields the good ones, that a value signed for one
cookie name does not verify under another, and that a rotated key set
still verifies a cookie signed by the previous key.

The tests compile today and fail at run, each on the
`not implemented: cookie-nv.<module>.<fn>` panic that is its body. That
is the expected state of an interface release. They turn green one at a
time as bodies land.

## Implementation status

| Item | Implemented |
| --- | --- |
| `cookieattr.CookieSpan`, `.CookieSameSite`, `.CookiePrefix`, `.CookieLife`, `.CookieAttrs`, `.CookieError` | the types are declared |
| `cookieattr.defaults`, `.empty_attrs`, `.prefix_of` | no |
| `cookieattr.check_attrs`, `.attrs_ok`, `.apply_prefix` | no |
| `cookieattr.name_byte_ok`, `.value_byte_ok`, `.same_site_name`, `.same_site_named` | no |
| `cookieattr.CookieError.message` | no |
| `cookieparse.parse_header`, `.get`, `.get_str`, `.get_all`, `.count` | no |
| `cookieparse.span_str`, `.span_empty`, `.unquote` | no |
| `cookieparse.parse_set_cookie`, `.parse_set_cookie_lenient`, `.parse_expires` | no |
| `cookiewrite.set_cookie`, `.set_cookie_unchecked`, `.set_cookie_into`, `.set_cookie_len` | no |
| `cookiewrite.delete_cookie`, `.format_expires`, `.cookie_header`, `.quote_value` | no |
| `cookiejar.jar`, `.jar_from`, `.entries`, `.jar_len`, `.store`, `.remove` | no |
| `cookiejar.cookies_for`, `.header_for`, `.prune`, `.clear_session`, `.is_expired` | no |
| `cookiejar.no_public_suffixes`, `.rules_with_suffixes`, `.jar_rules_are_unsafe` | no |
| `cookiejar.domain_matches`, `.path_matches`, `.default_path`, `.host_is_ip`, `.canonical_host` | no |
| `cookieseal.one_key`, `.keys_of`, `.rotate`, `.key_count`, `.key_len` | no |
| `cookieseal.sign`, `.verify`, `.peek_signed`, `.is_sealed` | no |
| `cookieseal.cipher`, `.encrypt`, `.decrypt`, `.nonce_len` | no |
| `cookieseal.derive`, `.master_len` | no |

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
