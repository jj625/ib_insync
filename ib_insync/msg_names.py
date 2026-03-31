"""Message ID to mnemonic name mappings for debug logging.

Derived automatically from ibapi.message.IN / ibapi.message.OUT so that
new message types added to the tws-api subtree are picked up without
manual edits here.
"""

from ibapi.message import IN, OUT


def _invert(cls) -> dict[int, str]:
    """Build {int_value: 'ATTR_NAME'} from a class's public int attrs."""
    return {
        v: k for k, v in vars(cls).items()
        if not k.startswith('_') and isinstance(v, int)
    }


# Incoming message ID -> mnemonic name
IN_MSG_NAMES: dict[int, str] = _invert(IN)

# Outgoing message ID -> mnemonic name
OUT_MSG_NAMES: dict[int, str] = _invert(OUT)


def in_msg_name(msgId: int) -> str:
    """Return 'msgId=N(NAME)' for debug logging."""
    name = IN_MSG_NAMES.get(msgId)
    return f'msgId={msgId}({name})' if name else f'msgId={msgId}'


def out_msg_name(msgId: int) -> str:
    """Return 'msgId=N(NAME)' for debug logging."""
    name = OUT_MSG_NAMES.get(msgId)
    return f'msgId={msgId}({name})' if name else f'msgId={msgId}'
