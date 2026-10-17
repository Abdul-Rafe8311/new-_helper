"""URL canonicalisation: the same story must map to the same URL however it was linked."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = frozenset({"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid"})
TRACKING_PREFIXES = ("utm_", "ga_", "pk_", "hsa_")
# AMP variants: /amp/ or trailing /amp path segments, ?amp / ?outputType=amp, amp. subdomains.
_AMP_SEGMENT = re.compile(r"/amp(?=/|$)", re.IGNORECASE)


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES)


def _is_amp_marker(key: str, value: str) -> bool:
    lowered = key.lower()
    return lowered == "amp" or (lowered == "outputtype" and value.lower() == "amp")


def canonicalize_url(url: str) -> str:
    """Lowercase host, drop fragment, tracking params, AMP markers and trailing slashes."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    host = (parts.hostname or "").lower()
    if host.startswith("amp."):
        host = host[4:]
    if host.startswith("www."):
        host = host[4:]
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    path = _AMP_SEGMENT.sub("", parts.path)
    path = re.sub(r"/{2,}", "/", path).rstrip("/")
    query = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(k) and not _is_amp_marker(k, v)
    )
    return urlunsplit((scheme, host, path or "", urlencode(query), ""))


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")
