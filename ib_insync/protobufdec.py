# Generic schema-less protobuf decoder
# Deterministic, restart-safe, no hidden state.

from typing import Tuple, Any, Dict, List

def read_varint(buf: bytes, i: int) -> Tuple[int, int]:
    shift = 0
    result = 0
    while True:
        b = buf[i]
        result |= (b & 0x7F) << shift
        i += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, i

def read_length_delimited(buf: bytes, i: int) -> Tuple[bytes, int]:
    length, i = read_varint(buf, i)
    end = i + length
    return buf[i:end], end

def decode_field(buf: bytes, i: int) -> Tuple[int, Any, int]:
    key, i = read_varint(buf, i)
    field_number = key >> 3
    wire_type = key & 0x07

    if wire_type == 0:  # varint
        value, i = read_varint(buf, i)
        return field_number, value, i

    elif wire_type == 1:  # 64-bit
        value = buf[i:i+8]
        return field_number, value, i+8

    elif wire_type == 2:  # length-delimited
        raw, i = read_length_delimited(buf, i)
        # Try recursive decode; fallback to raw bytes
        try:
            sub = decode_message(raw)
            return field_number, sub, i
        except Exception:
            return field_number, raw, i

    elif wire_type == 5:  # 32-bit
        value = buf[i:i+4]
        return field_number, value, i+4

    else:
        raise ValueError(f"Unsupported wire type {wire_type}")

def decode_message(buf: bytes) -> Dict[int, List[Any]]:
    i = 0
    out: Dict[int, List[Any]] = {}

    while i < len(buf):
        field_number, value, i = decode_field(buf, i)
        out.setdefault(field_number, []).append(value)

    return out