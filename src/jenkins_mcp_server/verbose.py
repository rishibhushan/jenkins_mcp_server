"""Shared verbose logging utility"""
import sys

# Global verbose flag
_VERBOSE = False

def set_verbose(verbose: bool):
    """Set the global verbose flag"""
    global _VERBOSE
    _VERBOSE = verbose

def vprint(msg: str):
    """Print message only if verbose mode is enabled"""
    if _VERBOSE:
        print(msg, file=sys.stderr, flush=True)

def is_verbose() -> bool:
    """Check if verbose mode is enabled"""
    return _VERBOSE