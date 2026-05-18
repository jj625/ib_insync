import math
import sys
from _decimal import Decimal

NO_VALID_ID: int = -1
MAX_MSG_LEN: int = 0xFFFFFF  # 16Mb - 1byte
UNSET_INTEGER: int = 2**31 - 1
UNSET_DOUBLE: float = float(sys.float_info.max)
UNSET_LONG: int = 2**63 - 1
UNSET_DECIMAL: Decimal = Decimal(2**127 - 1)
DOUBLE_INFINITY: float = math.inf
INFINITY_STR: str = "Infinity"
