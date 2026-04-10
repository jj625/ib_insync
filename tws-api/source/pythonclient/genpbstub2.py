#!/usr/bin/env python3
"""
Deterministic protobuf .pyi stub generator.
- Scalar fields: non-optional (float, int, bool, str, bytes)
- Message fields: optional (Message | None)
- Enums: typed as enum class
- Maps: Dict[key, value]
- Repeated: List[T]
- Oneofs: union of participating fields
- Stable ordering: sorted by filename, then field order
- No runtime imports from generated modules
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from google.protobuf.descriptor import (
    FieldDescriptor,
    Descriptor,
    EnumDescriptor,
)
from google.protobuf.message import Message

ROOT = Path(__file__).resolve().parent
PROTO_DIR = ROOT / "ibapi" / "protobuf"


# ---------------------------------------------------------------------------
# Type mapping
# ---------------------------------------------------------------------------

SCALAR_MAP = {
    FieldDescriptor.TYPE_DOUBLE: "float",
    FieldDescriptor.TYPE_FLOAT: "float",
    FieldDescriptor.TYPE_INT64: "int",
    FieldDescriptor.TYPE_UINT64: "int",
    FieldDescriptor.TYPE_INT32: "int",
    FieldDescriptor.TYPE_FIXED64: "int",
    FieldDescriptor.TYPE_FIXED32: "int",
    FieldDescriptor.TYPE_BOOL: "bool",
    FieldDescriptor.TYPE_STRING: "str",
    FieldDescriptor.TYPE_BYTES: "bytes",
    FieldDescriptor.TYPE_UINT32: "int",
    FieldDescriptor.TYPE_SFIXED32: "int",
    FieldDescriptor.TYPE_SFIXED64: "int",
    FieldDescriptor.TYPE_SINT32: "int",
    FieldDescriptor.TYPE_SINT64: "int",
}


def type_for_field(fd: FieldDescriptor) -> str:
    """Return Python type annotation for a protobuf field."""
    # Repeated
    if fd.label == FieldDescriptor.LABEL_REPEATED:
        if fd.type == FieldDescriptor.TYPE_MESSAGE:
            return f"list[{fd.message_type.name}]"
        elif fd.type == FieldDescriptor.TYPE_ENUM:
            return f"list[{fd.enum_type.name}]"
        else:
            return f"list[{SCALAR_MAP[fd.type]}]"

    # Map
    if fd.type == FieldDescriptor.TYPE_MESSAGE and fd.message_type.GetOptions().map_entry:
        key_fd = fd.message_type.fields_by_name["key"]
        val_fd = fd.message_type.fields_by_name["value"]
        key_t = SCALAR_MAP.get(key_fd.type, key_fd.message_type.name)
        if val_fd.type == FieldDescriptor.TYPE_MESSAGE:
            val_t = val_fd.message_type.name
        elif val_fd.type == FieldDescriptor.TYPE_ENUM:
            val_t = val_fd.enum_type.name
        else:
            val_t = SCALAR_MAP[val_fd.type]
        return f"dict[{key_t}, {val_t}]"

    # Enum
    if fd.type == FieldDescriptor.TYPE_ENUM:
        return fd.enum_type.name

    # Message (optional)
    if fd.type == FieldDescriptor.TYPE_MESSAGE:
        return f"{fd.message_type.name} | None"

    # Scalar (non-optional)
    return SCALAR_MAP[fd.type]


# ---------------------------------------------------------------------------
# Stub generation
# ---------------------------------------------------------------------------

def emit_enum(ed: EnumDescriptor) -> list[str]:
    out = [f"class {ed.name}(int):", "    ...", ""]
    return out


def emit_message(desc: Descriptor) -> list[str]:
    out = [f"class {desc.name}(Message):"]

    # Fields
    for fd in desc.fields:
        t = type_for_field(fd)
        out.append(f"    {fd.name}: {t}")

    # Oneofs
    for oneof in desc.oneofs:
        union_t = " | ".join(
            type_for_field(f) for f in oneof.fields
        )
        out.append(f"    # oneof {oneof.name}: {union_t}")

    # Standard protobuf API
    out.extend([
        "",
        "    def ParseFromString(self, data: bytes) -> None: ...",
        "    def SerializeToString(self) -> bytes: ...",
        "    def HasField(self, field_name: str) -> bool: ...",
        "    def CopyFrom(self, other: Message) -> None: ...",
        "    def MergeFrom(self, other: Message) -> None: ...",
        "",
    ])
    return out


def generate_stub(module_name: str, module) -> str:
    """Generate .pyi content for a single *_pb2 module."""
    lines = [
        "from __future__ import annotations",
        "from typing import Any, Optional, List, Dict",
        "from google.protobuf.message import Message",
        "",
    ]

    # Enums first
    enums = sorted(module.DESCRIPTOR.enum_types_by_name.values(), key=lambda e: e.name)
    for ed in enums:
        lines.extend(emit_enum(ed))

    # Messages
    msgs = sorted(module.DESCRIPTOR.message_types_by_name.values(), key=lambda m: m.name)
    for md in msgs:
        lines.extend(emit_message(md))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    sys.path.insert(0, str(ROOT))

    pb_files = sorted(PROTO_DIR.glob("*_pb2.py"))
    for py_file in pb_files:
        mod_name = py_file.stem
        module = __import__(f"ibapi.protobuf.{mod_name}", fromlist=["*"])
        stub = generate_stub(mod_name, module)

        out_path = py_file.with_suffix(".pyi")
        out_path.write_text(stub, encoding="utf-8")
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
