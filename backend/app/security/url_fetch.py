"""SSRF-safe image URL fetching for webhooks and provider callbacks."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

ALLOWED_HOST_SUFFIXES = (
    ".fal.media",
    ".fal.run",
    ".fal.ai",
    "fal.media",
    "fal.run",
    "fal.ai",
    ".amazonaws.com",
    ".cloudfront.net",
    ".r2.dev",
)


def _host_allowed(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    for suffix in ALLOWED_HOST_SUFFIXES:
        if host == suffix.lstrip(".") or host.endswith(suffix):
            return True
    return False


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def validate_image_url(url: str) -> None:
    """Raise ValueError if URL is not a safe HTTPS image source."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS image URLs are allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid image URL")
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local"):
        raise ValueError("Localhost URLs are not allowed")
    if not _host_allowed(host):
        raise ValueError(f"Image host not allowlisted: {host}")
    try:
        for info in socket.getaddrinfo(host, None):
            if _is_private_ip(info[4][0]):
                raise ValueError("Image URL resolves to a private address")
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve image host: {host}") from exc


async def safe_fetch_image_bytes(url: str, timeout: float = 120.0) -> bytes:
    validate_image_url(url)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("text/"):
            raise ValueError("Refusing to fetch non-image content")
        return resp.content
