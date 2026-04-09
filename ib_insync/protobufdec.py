# Generic schema-less protobuf decoder
# Deterministic, restart-safe, no hidden state.

import pprint
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

def decode_field(buf: bytes, i: int, recurse: bool = False, NESTED_FIELDS: set = set()) -> Tuple[int, Any, int]:
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

        # Option A: never recurse (treat as raw bytes)
        # return field_number, raw, i

        # Option B: recurse only for known nested fields
        # NESTED_FIELDS = set()  # e.g. {7, 11, ...} if you discover them
        if recurse and field_number in NESTED_FIELDS:
            try:
                sub = decode_message(raw, recurse=recurse, NESTED_FIELDS=NESTED_FIELDS)
                return field_number, sub, i
            except Exception:
                pass
        return field_number, raw, i

    elif wire_type == 5:  # 32-bit
        value = buf[i:i+4]
        return field_number, value, i+4

    else:
        raise ValueError(f"Unsupported wire type {wire_type}")

def decode_message(buf: bytes, recurse: bool = False, NESTED_FIELDS: set = set()) -> Dict[int, List[Any]]:
    i = 0
    out: Dict[int, List[Any]] = {}

    while i < len(buf):
        field_number, value, i = decode_field(buf, i, recurse=recurse, NESTED_FIELDS=NESTED_FIELDS)
        out.setdefault(field_number, []).append(value)

    return out

if __name__ == '__main__':
    with open('debug_payload.bin', 'rb') as f:
        payload = f.read()
    print(f'Payload:\n{payload}\n\n')
    decoded = decode_message(payload, recurse=True)
    print(f'Decoded:\n{pprint.pformat(decoded, width=160)}')
    _count = decoded[1][0]
    _msgs = decoded[2] # a list
    # print(f'Count: {_count}, Messages: {_msgs}')
    for i in range(len(_msgs)):
        _item = _msgs[i]
        x = decode_message(_item, recurse=False)
        # print(f'Item {i}:\n{pprint.pformat(x, width=160)}')
        y = x[1][0]
        z = decode_message(y, recurse=False)
        print(f'Nested:\n{pprint.pformat(z, width=160)}')
        # for field_number, values in x.items():
        #     print(f'Field {field_number}:')
        #     for value in values:
        #         print(f'  {value}')