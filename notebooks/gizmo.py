#
# gizmo.py` is a collection of utility functions`
#

import os
import sys
import json
import logging
import logging.config
import inspect
import asyncio
import datetime
import numbers
from collections import deque
from itertools import islice
from typing import Iterable
from numpy.typing import NDArray
import numpy as np

logger = logging.getLogger(__name__)

def load_spec_file(scriptdir: str = os.path.dirname(os.path.realpath(__file__))
    , filename: str = 'spec.json') -> dict:
    # spec file
    
    specfile = os.path.join(scriptdir, filename)
    if not os.path.exists(specfile):
        logger.error(f"Spec file not found: {specfile}")
        sys.exit(1)
    with open(specfile, 'r') as f:
        spec = json.load(f)
    logger.info(f"spec file loaded: {specfile}")
    return spec

import ctypes
import uuid
from ctypes import wintypes
from IPython import embed

# Constants from the Windows API
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

def prevent_sleep() -> None:
    # Prevent Windows from sleeping
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

def restore_sleep() -> None:
    # Restore the default behavior
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

# https://stackoverflow.com/questions/72847468/ctypes-how-to-parser-buffer-content

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_uint8 * 8)
    ]

# class GUID(ctypes.Structure):
#     _fields_ = [
#         ("Data1", wintypes.ULONG),
#         ("Data2", wintypes.USHORT),
#         ("Data3", wintypes.USHORT),
#         ("Data4", wintypes.BYTE * 8)
#     ]

    # def __str__(self):
    #     return f"{{{self.Data1:08X}-{self.Data2:04X}-{self.Data3:04X}-{''.join(f'{x:02X}' for x in self.Data4)}}}"
    # def __repr__(self):
    #     return f"GUID('{self}')"

    def __str__(self):
        return (f"{{{self.Data1:08x}-{self.Data2:04x}-{self.Data3:04x}-"
                f"{bytes(self.Data4[:2]).hex()}-{bytes(self.Data4[2:]).hex()}}}")

    # GUID_ptr = ctypes.POINTER['GUID']
    @staticmethod
    def to_string(guid_ptr) -> str:
        return str(guid_ptr.contents)

    def __init__(self, guid = None):
        if guid is not None:
            data = uuid.UUID(guid)
            self.Data1 = data.time_low
            self.Data2 = data.time_mid
            self.Data3 = data.time_hi_version
            self.Data4[0] = data.clock_seq_hi_variant
            self.Data4[1] = data.clock_seq_low
            self.Data4[2:] = data.node.to_bytes(6, "big")

    def __bytes__(self):
        return bytes(self.Data1.to_bytes(4, "little")
                    + self.Data2.to_bytes(2, "little")
                    + self.Data3.to_bytes(2, "little")
                    + self.Data4)

def GetPowerSetting() -> str:
    # https://learn.microsoft.com/en-us/windows/win32/api/powersetting/nf-powersetting-powergetactivescheme
    # Define necessary constants and types
    PowerGetActiveScheme = ctypes.windll.powrprof.PowerGetActiveScheme
    # [out] A pointer that receives a pointer to a GUID structure. Use the LocalFree function to free this memory.
    PowerGetActiveScheme.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.POINTER(GUID))]
    PowerGetActiveScheme.restype = wintypes.DWORD

    # Initialize variables
    active_scheme_guid_ptr = ctypes.POINTER(GUID)() # Create a pointer to a GUID

    # Call the function
    result = PowerGetActiveScheme(None, ctypes.byref(active_scheme_guid_ptr))
    if result == 0:  # ERROR_SUCCESS
        return GUID.to_string(active_scheme_guid_ptr)
    else:
        raise ctypes.WinError(result)
    # end of GetPowerSetting

def get_friendly_name(scheme_guid: GUID) -> str:
    PowerReadFriendlyName = ctypes.windll.powrprof.PowerReadFriendlyName
    PowerReadFriendlyName.argtypes = [ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(GUID), ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_wchar), ctypes.POINTER(ctypes.c_uint32)]
    PowerReadFriendlyName.restype = ctypes.c_uint32

    buffer_size = ctypes.c_uint32(0)
    PowerReadFriendlyName(None, ctypes.byref(scheme_guid), None, None, None, ctypes.byref(buffer_size))
    # print(buffer_size.value)
    # buffer = (ctypes.c_ubyte * buffer_size.value)()
    buffer = ctypes.create_unicode_buffer(buffer_size.value)
    result = PowerReadFriendlyName(None, ctypes.byref(scheme_guid), None, None, buffer, ctypes.byref(buffer_size))

    if result == 0:  # ERROR_SUCCESS
        return buffer.value
    else:
        raise ctypes.WinError(result)  
    # end of get_friendly_name

# friendly_name = get_friendly_name(active_scheme_guid_ptr.contents)
# print(f"Active Power Scheme Friendly Name: {friendly_name}")

def fmt_elapsed_time(elapsed_time: float) -> str:
    if elapsed_time >= 1:
        s = f"{elapsed_time:.2f} s"
    elif elapsed_time >= 1e-3:
        s = f"{elapsed_time * 1e3:.2f} ms"
    elif elapsed_time >= 1e-6:
        s = f"{elapsed_time * 1e6:.2f} µs"
    else:
        s = f"{elapsed_time * 1e9:.2f} ns"
    return s

import time
import functools

# Works with regular functions, instance methods, class methods, static methods, and coroutines.
# Correctly identifies and displays the class name for methods.
# Distinguishes between functions and coroutines in the output.

def measure_time(func):
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print_result(func, args, execution_time)
        return result

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print_result(func, args, execution_time)
        return result

    def print_result(func, args, execution_time, printfn=print):
        if inspect.ismethod(func):
            func_name = f"{func.__self__.__class__.__name__}.{func.__name__}"
        elif args and hasattr(args[0].__class__, func.__name__):
            func_name = f"{args[0].__class__.__name__}.{func.__name__}"
        else:
            func_name = func.__name__

        printfn(f"{'Coroutine' if asyncio.iscoroutinefunction(func) else 'Function'} "
              f"'{func_name}' took {fmt_elapsed_time(execution_time)} to execute.")

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

def almost_zero_vector(v: NDArray, tol: float = 0.0001) -> tuple[bool, float]:
    norm = np.linalg.norm(v)
    return (np.all(np.abs(v) < tol), norm)

def extract_field_as_list(group: Iterable, field_name: str) -> list:
    return [getattr(item, field_name) for item in group]

def extract_field_as_array(group: Iterable, field_name: str) -> NDArray:
    return np.asarray(extract_field_as_list(group, field_name))

def slice_deque(dq: deque, start=None, end=None) -> list:
    length = len(dq)
    if length == 0:
        return []
    
    if start is None:
        start = 0
    elif start < 0:
        start += length
    
    if end is None:
        end = length
    elif end < 0:
        end += length
    
    start = max(0, min(start, length))
    end = max(0, min(end, length))
    
    return list(islice(dq, start, end))

def custom_formatter(value):
    if isinstance(value, (bool, int, float, str, bytes)):
        return str(value)
    if isinstance(value, datetime.datetime):
        value_local = value.astimezone()  # Convert to local time
        if value_local.date() == datetime.datetime.now().date():
            return value_local.strftime('%H:%M:%S')
        else:
            return value_local.strftime(r'%Y-%m-%d %H:%M:%S %Z')
    elif isinstance(value, list):
        return '[' + ", ".join([custom_formatter(v) for v in value]) + ']'
    elif isinstance(value, dict):
        return {k: custom_formatter(v) for k, v in value.items()}
    # elif util.isnamedtupleinstance(value):
    #     return {f: custom_formatter(getattr(value, f)) for f in value._fields}
    # elif util.is_dataclass(value):
    #     return {value.__class__.__qualname__: custom_formatter(util.dataclassNonDefaults(value))}
    else:
        # logger.warning(f"Unknown type: {type(value)}")
        return str(value)

def format_dict(d: dict) -> str:
    return '{' + ", ".join(f"{k}: {custom_formatter(v)}" for k, v in d.items()) + '}'

def is_integer(value: numbers.Real) -> bool:
    return value == int(value)

def format_value(value: numbers.Real, intexpected: bool = False) -> str:
    """
    Format a float value to 2 decimal places if it has a decimal part, otherwise to 0 decimal places
    intexpected: if True means we're expecting an integer value
    """
    if not isinstance(value, int) and intexpected and not is_integer(value):
        logger.warning(f"Expected integer value, got {value}")
    return f"{value:.2f}" if value % 1 != 0 else f"{value:.0f}"

def plus(num: numbers.Real) -> numbers.Real:
    """Return the positive part of the number"""
    return max(0, num)

def neg(num: numbers.Real) -> numbers.Real:
    """Return the negative part of the number"""
    return min(0, num)
