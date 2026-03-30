"""
Lightweight IB API handshake probe.

Usage:
    from ibapi.test_port import test_ib_port
    ok, info = test_ib_port("127.0.0.1", 7497)
"""

import socket
import struct
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Copied from server_versions.py so this module is fully self-contained.
_MIN_CLIENT_VER = 100
_MAX_CLIENT_VER = 218


def test_ib_port(host: str, port: int, timeout: float = 4.0) -> tuple[bool, str]:
    """Check whether an IB TWS / Gateway is listening on *host*:*port*.

    Performs the real v100+ handshake (the same byte sequence that
    ``EClient.connect()`` sends) and waits for the server to reply with
    its version number and connection timestamp.

    Returns
    -------
    (True,  "server_version=<N> conn_time=<T>")   on success
    (False, "<reason>")                            on failure
    """
    sock = None
    try:
        # --- TCP connect ---
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))

        # --- send v100 handshake ---
        # prefix: literal "API\0"
        prefix = b"API\x00"
        # version range string, length-prefixed (big-endian uint32)
        ver_str = f"v{_MIN_CLIENT_VER}..{_MAX_CLIENT_VER}"
        ver_bytes = ver_str.encode("ascii")
        ver_msg = struct.pack(f"!I{len(ver_bytes)}s", len(ver_bytes), ver_bytes)
        sock.sendall(prefix + ver_msg)

        # --- read server response ---
        # TWS replies with a 4-byte length prefix followed by two
        # NULL-terminated fields: server_version and conn_time.
        # It may also send unsolicited news before the version fields,
        # so we loop just like EClient.connect() does.
        buf = b""
        for _ in range(10):          # bounded retry
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                return False, "timeout waiting for server response"
            if not chunk:
                return False, "connection closed by server before handshake reply"
            buf += chunk

            # need at least the 4-byte size header
            if len(buf) < 4:
                continue
            msg_len = struct.unpack("!I", buf[:4])[0]
            if len(buf) - 4 < msg_len:
                continue                   # haven't received full message yet

            payload = buf[4 : 4 + msg_len]
            fields = payload.split(b"\x00")
            # strip trailing empty element produced by the final NULL
            fields = [f for f in fields if f]

            if len(fields) >= 2:
                try:
                    server_version = int(fields[0])
                except (ValueError, UnicodeDecodeError):
                    return False, f"unexpected first field (not an int): {fields[0]!r}"
                conn_time = fields[1].decode("ascii", errors="replace")
                return True, f"server_version={server_version} conn_time={conn_time}"

            # fewer than 2 fields — could be an intermediate news burst;
            # consume this message and keep reading
            buf = buf[4 + msg_len :]

        return False, "did not receive valid version fields after multiple reads"

    except socket.timeout:
        return False, f"TCP connect timed out ({host}:{port})"
    except ConnectionRefusedError:
        return False, f"connection refused ({host}:{port})"
    except OSError as exc:
        return False, f"socket error: {exc}"
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


def find_ib_port(
    host: str,
    ports: range | list[int],
    timeout: float = 0.5,
) -> tuple[int, str] | tuple[None, str]:
    """Scan *ports* and return the first one with a live IB server.

    Uses a short TCP-connect pre-check to skip closed ports quickly,
    then performs the full IB handshake only on ports that accept a
    connection.

    Parameters
    ----------
    host     : IP or hostname to probe.
    ports    : iterable of port numbers, e.g. ``range(7496, 7498)``
               or ``[7496, 7497, 4001, 4002]``.
    timeout  : per-port timeout in seconds (default 0.5 s).

    Returns
    -------
    (port, info)   if a live IB server is found
    (None, reason) if none of the ports answered the IB handshake
    """
    for port in ports:
        # fast pre-check: can we even TCP-connect?
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.settimeout(timeout)
        try:
            logger.debug("Probing %s:%d", host, port)
            probe.connect((host, port))
        except (socket.timeout, ConnectionRefusedError, OSError):
            continue
        finally:
            try:
                probe.close()
            except OSError:
                pass

        # port is open — do the real handshake
        ok, info = test_ib_port(host, port, timeout=timeout)
        if ok:
            return port, info

    return None, f"no IB server found on {host} ports {list(ports)}"


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"

    # single port mode:  test_port.py [host] <port>
    # scan mode:         test_port.py [host] <start>-<end>
    arg = sys.argv[2] if len(sys.argv) > 2 else "7496-7497"
    if "-" in arg:
        lo, hi = arg.split("-", 1)
        port, info = find_ib_port(host, range(int(lo), int(hi) + 1))
        if port is not None:
            print(f"OK (port {port}): {info}")
        else:
            print(f"FAIL: {info}")
            sys.exit(1)
    else:
        ok, info = test_ib_port(host, int(arg))
        print(f"{'OK' if ok else 'FAIL'}: {info}")
        if not ok:
            sys.exit(1)
