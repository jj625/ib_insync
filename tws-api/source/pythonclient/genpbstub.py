import importlib
import inspect
import pathlib
from textwrap import indent

ROOT = pathlib.Path(__file__).parent
PKG_ROOT = ROOT / "ibapi" / "protobuf"


def py_type(field) -> str:
    from google.protobuf.descriptor import FieldDescriptor as FD

    kind = field.type
    opt = field.label != field.LABEL_REPEATED

    if kind in (FD.TYPE_INT32, FD.TYPE_SINT32, FD.TYPE_SFIXED32,
                FD.TYPE_INT64, FD.TYPE_SINT64, FD.TYPE_SFIXED64,
                FD.TYPE_UINT32, FD.TYPE_UINT64, FD.TYPE_FIXED32, FD.TYPE_FIXED64):
        base = "int"
    elif kind in (FD.TYPE_FLOAT, FD.TYPE_DOUBLE):
        base = "float"
    elif kind == FD.TYPE_BOOL:
        base = "bool"
    elif kind == FD.TYPE_STRING:
        base = "str"
    elif kind == FD.TYPE_BYTES:
        base = "bytes"
    elif kind in (FD.TYPE_MESSAGE, FD.TYPE_ENUM):
        base = "Any"
    else:
        base = "Any"

    if field.label == FD.LABEL_REPEATED:
        return f"list[{base}]"
    if opt:
        return f"Optional[{base}]"
    return base


def generate_stub_for_module(py_path: pathlib.Path) -> None:
    rel = py_path.relative_to(ROOT)
    mod_name = ".".join(rel.with_suffix("").parts)

    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        print(f"SKIP {mod_name}: import failed: {e}")
        return

    descriptor = getattr(mod, "DESCRIPTOR", None)
    if descriptor is None:
        print(f"SKIP {mod_name}: no DESCRIPTOR")
        return

    lines: list[str] = []
    lines.append("from typing import Any, Optional, Iterable\n")

    for msg in descriptor.message_types_by_name.values():
        cls_name = msg.name
        lines.append(f"class {cls_name}:")
        # attributes
        for field in msg.fields:
            t = py_type(field)
            lines.append(f"    {field.name}: {t}")
        lines.append("")
        # __init__
        params = []
        for field in msg.fields:
            t = py_type(field)
            params.append(f"{field.name}: {t} = ...")
        init_sig = ", ".join(params)
        lines.append("    def __init__(self, *, " + init_sig + ") -> None: ...")
        lines.append("")
        # common protobuf methods
        lines.append("    def ParseFromString(self, data: bytes) -> None: ...")        
        lines.append("    def SerializeToString(self) -> bytes: ...")
        lines.append(f"    @classmethod")
        lines.append(f"    def FromString(cls, data: bytes) -> \"{cls_name}\": ...")
        lines.append("    def CopyFrom(self, other: Any) -> None: ...")
        lines.append("    def MergeFrom(self, other: Any) -> None: ...")
        lines.append("    def Clear(self) -> None: ...")
        lines.append("    def HasField(self, field_name: str) -> bool: ...")
        lines.append("    def ListFields(self) -> Iterable[tuple[str, Any]]: ...")
        lines.append("")

    pyi_path = py_path.with_suffix(".pyi")
    pyi_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {pyi_path}")


def main() -> None:
    for py in sorted(PKG_ROOT.glob("*_pb2.py")):
        # skip __init__.py etc
        if py.name == "__init__.py":
            continue
        generate_stub_for_module(py)


if __name__ == "__main__":
    main()