#!/usr/bin/env python3
"""
SOCKS5 Proxy Checker

A minimal, dependency-free SOCKS5 proxy connectivity tester.
Implements RFC 1928 handshake and optionally fetches a remote URL
through the proxy to report latency and exit IP.

Usage:
    python socks5_checker.py --host 127.0.0.1 --port 1080
    python socks5_checker.py --host 127.0.0.1 --port 1080 --user u --pass p
    python socks5_checker.py --host 127.0.0.1 --port 1080 --target https://httpbin.org/ip
"""

import argparse
import json
import socket
import ssl
import struct
import sys
import time
from urllib.parse import urlparse


def resolve_host(host: str) -> str:
    """Resolve a hostname to its first IPv4 address."""
    try:
        return socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
    except socket.gaierror as exc:
        raise RuntimeError(f"Cannot resolve {host}: {exc}") from exc


def socks5_auth(sock: socket.socket, username: str = "", password: str = "") -> None:
    """Perform username/password authentication (RFC 1929)."""
    if not username:
        # No-auth was already negotiated; nothing to do.
        return

    user_bytes = username.encode("utf-8")
    pass_bytes = password.encode("utf-8")
    if len(user_bytes) > 255 or len(pass_bytes) > 255:
        raise ValueError("Username or password exceeds 255 bytes")

    auth_req = (
        bytes([0x01, len(user_bytes)]) + user_bytes
        + bytes([len(pass_bytes)]) + pass_bytes
    )
    sock.sendall(auth_req)

    resp = sock.recv(2)
    if len(resp) < 2:
        raise ConnectionError("SOCKS5 auth response truncated")
    if resp[0] != 0x01:
        raise ConnectionError(f"Unexpected SOCKS5 auth version: {resp[0]}")
    if resp[1] != 0x00:
        raise ConnectionError(f"SOCKS5 auth failed, status: {resp[1]}")


def socks5_connect(
    sock: socket.socket,
    target_host: str,
    target_port: int,
    username: str = "",
    password: str = "",
) -> None:
    """Negotiate SOCKS5 and request a CONNECT to target_host:target_port."""
    methods = [0x00]  # no authentication
    if username:
        methods.append(0x02)  # username/password

    greeting = bytes([0x05, len(methods)] + methods)
    sock.sendall(greeting)

    resp = sock.recv(2)
    if len(resp) < 2:
        raise ConnectionError("SOCKS5 greeting response truncated")
    if resp[0] != 0x05:
        raise ConnectionError(f"Unexpected SOCKS5 version: {resp[0]}")

    chosen = resp[1]
    if chosen == 0xFF:
        raise ConnectionError("No acceptable SOCKS5 authentication method")
    if chosen == 0x02:
        socks5_auth(sock, username, password)
    elif chosen != 0x00:
        raise ConnectionError(f"Unsupported SOCKS5 auth method: {chosen}")

    # Resolve target to IPv4 for the request.
    target_ip = resolve_host(target_host)

    req = bytes(
        [0x05, 0x01, 0x00, 0x01]  # VER, CMD=CONNECT, RSV, ATYP=IPv4
    ) + socket.inet_aton(target_ip) + struct.pack(">H", target_port)
    sock.sendall(req)

    resp = sock.recv(10)
    if len(resp) < 10:
        raise ConnectionError("SOCKS5 connect response truncated")
    if resp[0] != 0x05:
        raise ConnectionError(f"Unexpected SOCKS5 version: {resp[0]}")
    if resp[1] != 0x00:
        errors = {
            0x01: "general SOCKS server failure",
            0x02: "connection not allowed",
            0x03: "network unreachable",
            0x04: "host unreachable",
            0x05: "connection refused",
            0x06: "TTL expired",
            0x07: "command not supported",
            0x08: "address type not supported",
        }
        err = errors.get(resp[1], f"unknown error {resp[1]}")
        raise ConnectionError(f"SOCKS5 connect failed: {err}")


def fetch_through_socket(
    sock: socket.socket, url: str, timeout: float
) -> dict:
    """Fetch a simple HTTP/HTTPS URL through an already-established proxy socket."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https targets are supported")

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    if parsed.scheme == "https":
        ctx = ssl.create_default_context()
        sock = ctx.wrap_socket(sock, server_hostname=host)

    sock.settimeout(timeout)
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"User-Agent: socks5-checker/1.0\r\n"
        f"Accept: */*\r\n"
        f"Connection: close\r\n\r\n"
    ).encode("utf-8")
    sock.sendall(request)

    data = b""
    while True:
        try:
            chunk = sock.recv(8192)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk

    if not data:
        raise ConnectionError("No response from target through proxy")

    header_end = data.find(b"\r\n\r\n")
    if header_end == -1:
        raise ConnectionError("Malformed HTTP response")

    body = data[header_end + 4 :]
    try:
        text = body.decode("utf-8").strip()
        payload = json.loads(text) if text.startswith("{") else {"raw": text[:500]}
    except Exception:
        payload = {"raw": body[:500].decode("utf-8", errors="ignore")}

    return payload


def check_socks5(args) -> dict:
    """Run the full check and return a structured result."""
    result = {
        "proxy": f"{args.host}:{args.port}",
        "auth": bool(args.user),
        "target": args.target,
        "success": False,
        "connect_latency_ms": None,
        "total_latency_ms": None,
        "exit_ip": None,
        "error": None,
    }

    target = urlparse(args.target)
    target_host = target.hostname or "httpbin.org"
    target_port = target.port or (443 if target.scheme == "https" else 80)

    t0 = time.perf_counter()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(args.timeout)
        sock.connect((args.host, args.port))
        t1 = time.perf_counter()

        socks5_connect(sock, target_host, target_port, args.user, args.pass_)

        if args.target:
            payload = fetch_through_socket(sock, args.target, args.timeout)
            result["target_response"] = payload

            # Try to extract exit IP from common response formats.
            for key in ("ip", "origin"):
                if key in payload:
                    result["exit_ip"] = payload[key].split(",")[0].strip()
                    break

        result["success"] = True
        result["connect_latency_ms"] = round((t1 - t0) * 1000, 2)
        result["total_latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        try:
            sock.close()
        except Exception:
            pass

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="SOCKS5 proxy connectivity checker")
    parser.add_argument("--host", required=True, help="SOCKS5 proxy host")
    parser.add_argument("--port", type=int, required=True, help="SOCKS5 proxy port")
    parser.add_argument("--user", default="", help="Username for authentication")
    parser.add_argument("--pass", dest="pass_", default="", help="Password for authentication")
    parser.add_argument(
        "--target",
        default="https://socks5ip.com.cn/wp-json/ip-quality/v1/detect",
        help="URL to fetch through the proxy",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Socket timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output compact JSON")
    args = parser.parse_args()

    result = check_socks5(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
