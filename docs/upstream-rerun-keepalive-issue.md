# Upstream issue draft: rerun-io/rerun

Draft body for an issue to be filed against
[`rerun-io/rerun`](https://github.com/rerun-io/rerun) requesting that
the `MessageProxyService` gRPC client and server expose / enable HTTP/2
keepalive. Until this lands upstream we have to either tune every
middlebox in the path (see `rerun-viewer/nginx.conf.template`) or emit
application-level heartbeats from the SDK (see README → Known issues).

---

**Title:** MessageProxy gRPC client/server lack HTTP/2 keepalive — long-lived `WriteMessages` streams die on any idle middlebox

**Body:**

### Summary

The `MessageProxyService` gRPC client (`re_grpc_client`) and server
(`re_grpc_server`) build their tonic `Endpoint` / `Server` without any
HTTP/2 or TCP keepalive options. As a result, the long-lived
`WriteMessages` stream that `rerun.connect_grpc()` opens is silently
torn down by any L4/L7 hop in the path that has an idle timeout —
nginx (`client_body_timeout` 60s default), Traefik (`idleTimeout` 180s),
Azure LB (4 min default), AWS NLB (350s), conntrack, etc.

The SDK only notices on the next `rr.log()` call, which fails with:

    h2 protocol error: http2 error

This is reproducible deterministically with any client that holds the
stream open for longer than the smallest idle timeout in the path
between batches.

### Where

Client (`crates/store/re_grpc_client/src/write.rs:338`):

```rust
let endpoint = match Endpoint::from_shared(uri.origin.as_url()) {
    Ok(endpoint) => endpoint, // ← no keepalive applied
    ...
};
```

Server (`crates/store/re_grpc_server/src/lib.rs:278`):

```rust
Server::builder()
    .accept_http1(true)
    .layer(cors)
    .layer(grpc_web)
    .add_routes(routes)
    .serve_with_incoming_shutdown(...)
```

For comparison, `crates/store/re_redap_client/src/grpc.rs:79-83`
already does exactly the right thing on the dataplatform client:

```rust
.http2_keep_alive_interval(Duration::from_secs(30))
.keep_alive_timeout(Duration::from_secs(20))
.keep_alive_while_idle(true)
.tcp_keepalive(Some(Duration::from_secs(30)));
```

### Impact

Anyone deploying `re_grpc_server` behind any reverse proxy or cloud LB
(i.e., effectively all production / Kubernetes deployments) hits this.
The Python `connect_grpc()` API surfaces no way to configure keepalive,
so users currently have no recourse other than:

1. tuning every middlebox idle timeout to be larger than the longest
   plausible inter-batch gap (fragile, often impossible on managed LBs);
2. emitting application-level heartbeat `rr.log()` calls on a timer
   (works but ugly, every user reinvents it).

### Proposed fix

Mirror the `re_redap_client` settings on both endpoints:

- `re_grpc_client/src/write.rs`: apply `http2_keep_alive_interval`,
  `keep_alive_timeout`, `keep_alive_while_idle(true)`, `tcp_keepalive`
  on the `Endpoint` before `.connect()`.
- `re_grpc_server/src/lib.rs`: apply `http2_keepalive_interval`,
  `http2_keepalive_timeout`, `tcp_keepalive` on the `Server::builder()`.

Reasonable defaults (matching `re_redap_client`): 30s ping interval,
20s ping timeout, `keep_alive_while_idle = true`, 30s TCP keepalive.
Optionally make these configurable via `connect_grpc_opts(...)` and
the server CLI / `ServerOptions`.

### Versions affected

Confirmed on `0.33.0` (release tag) and `main` (`0.34.0-alpha.1+dev`).

### Workarounds

- raise nginx `client_body_timeout` / `proxy_read_timeout` /
  `grpc_read_timeout` etc. (caps at ~24 days, the `ngx_msec_t`
  ceiling), and equivalent settings on every other middlebox in the
  path;
- emit a periodic `rr.log("internal/keepalive", ...)` from a
  background thread.

Happy to send a PR if the maintainers agree on the defaults / API
surface.
