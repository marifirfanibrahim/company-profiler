"""
build httpx client
apply pool limits
apply tls config
"""

from typing import Dict, Optional

import httpx


# ============== CLIENT ==============

def build_httpx_client(
    config,
    timeout: int,
    headers: Optional[Dict[str, str]] = None,
    follow_redirects: Optional[bool] = None,
    verify: Optional[bool] = None,
    force_connection_close: Optional[bool] = None,
) -> httpx.Client:
    # build httpx client
    t = int(timeout)

    # read pool limits
    mk = int(config.HTTP_MAX_KEEPALIVE_CONNECTIONS)
    mc = int(config.HTTP_MAX_CONNECTIONS)

    # read redirect setting
    if follow_redirects is None:
        follow_redirects = bool(config.HTTP_FOLLOW_REDIRECTS)

    # read tls setting
    if verify is None:
        verify = bool(config.HTTP_VERIFY_TLS)

    # read connection close setting
    if force_connection_close is None:
        force_connection_close = bool(config.HTTP_FORCE_CONNECTION_CLOSE)

    # build headers map
    hdrs = dict(headers or {})

    if bool(force_connection_close):
        # force connection close
        hdrs["Connection"] = "close"

    # build limits object
    limits = httpx.Limits(
        max_keepalive_connections=int(mk),
        max_connections=int(mc),
    )

    # build client instance
    return httpx.Client(
        timeout=t,
        headers=hdrs,
        verify=bool(verify),
        follow_redirects=bool(follow_redirects),
        limits=limits,
    )