# Compatibility shim for the misspelled module name (llm_cliient).
# The real implementation lives in `llm_client.py` and reads configuration from environment variables.
from .llm_client import call_llm, call_llm_json

__all__ = ["call_llm", "call_llm_json"]

