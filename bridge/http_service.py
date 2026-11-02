"""Bounded protocol validation and dispatch for the local HTTP bridge backends."""

import json
import re

PROTOCOL = "webkit2jb-bridge/1"
MAX_REQUEST_BYTES = 4096
MAX_MESSAGE_BYTES = 256
OPERATIONS = frozenset(("capabilities", "diagnostic", "connectivity", "echo", "ns2jb-compatibility", "memory-policy"))
NS2JB_SOURCE_COMMIT = "95f5525089273c5fce0b95047f3600f8442e96ae"
NS2JB_UNAVAILABLE_NOTE = (
    "No license-cleared, platform-neutral NS2JB contract was verified; "
    "Horizon process-control interfaces are unavailable in this bridge."
)
BACKENDS = frozenset(("linux-native", "linux-mock", "horizon-homebrew", "pc-simulated", "unavailable"))


def ns2jb_compatibility_result(*, simulated, note=NS2JB_UNAVAILABLE_NOTE):
    """Stable descriptive result; it never claims that upstream NS2JB is callable."""
    return {
        "adapterVersion": 2,
        "sourceCommit": NS2JB_SOURCE_COMMIT,
        "capabilityFlags": 0,
        "status": "CAPABILITY_UNAVAILABLE",
        "licenseConfirmed": False,
        "dataProtocolVerified": False,
        "horizonServiceAvailable": False,
        "privilegedOperationsAvailable": False,
        "simulated": bool(simulated),
        "note": str(note)[:192],
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_FIELD")
        result[key] = value
    return result


def validate_request(message, expected_backend="pc-simulated"):
    if not isinstance(message, dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    if set(message) != {"protocol", "requestId", "operation", "backend", "payload"}:
        raise ValueError("REQUEST_FIELDS_MISMATCH")
    if message["protocol"] != PROTOCOL:
        raise LookupError("PROTOCOL_VERSION_UNSUPPORTED")
    request_id = message["requestId"]
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", request_id):
        raise ValueError("INVALID_REQUEST_ID")
    operation = message["operation"]
    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise LookupError("UNSUPPORTED_OPERATION")
    backend = message["backend"]
    if not isinstance(backend, str) or backend not in BACKENDS or backend != expected_backend:
        raise LookupError("BACKEND_MISMATCH")
    payload = message["payload"]
    if not isinstance(payload, dict):
        raise ValueError("INVALID_PAYLOAD")
    if operation == "echo":
        if set(payload) != {"message"} or not isinstance(payload["message"], str):
            raise ValueError("INVALID_PAYLOAD")
        if len(payload["message"].encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise OverflowError("MESSAGE_TOO_LARGE")
    elif payload:
        raise ValueError("INVALID_PAYLOAD")
    return message


def response(request_id, operation, *, ok, result=None, error=None, backend="none", execution=None):
    if execution is None:
        execution = {"mode": "none", "platform": "unknown", "architecture": "unknown", "origin": "unavailable",
                     "nativeLibraryLoaded": False, "nativeProcessConnected": False,
                     "switchNativeExecution": False}
    return {
        "protocol": PROTOCOL,
        "requestId": request_id,
        "operation": operation,
        "backend": backend,
        "ok": ok,
        "error": error,
        "result": result or {},
        "execution": execution,
    }


def handshake(runtime=None):
    if runtime is None:
        from bridge.python.runtime import SimulatedRuntime
        runtime = SimulatedRuntime()
    backend = runtime.backend_id
    try:
        result = runtime.handshake()
    except Exception as error:
        code = getattr(error, "code", "BACKEND_FAILURE")
        status = getattr(error, "status", 502)
        message = str(error)[:160] or "Backend capability discovery failed"
        return status, response("handshake", "handshake", ok=False,
            error={"code": code, "message": message}, backend=backend,
            execution=runtime.execution())
    if backend == "unavailable":
        error = {"code": "CAPABILITY_UNAVAILABLE", "message": result.get("unavailableReason", "No backend available")}
        return 503, response("handshake", "handshake", ok=False, error=error,
                              backend=backend, execution=runtime.execution())
    return 200, response("handshake", "handshake", ok=True, result=result,
                          backend=backend, execution=runtime.execution())


def process_request(raw, runtime=None):
    """Return (HTTP status, versioned response) without opening sockets or running commands."""
    if runtime is None:
        from bridge.python.runtime import SimulatedRuntime
        runtime = SimulatedRuntime()
    backend = runtime.backend_id
    execution = runtime.execution()
    request_id, operation = "invalid", "unknown"
    try:
        message = json.loads(raw, object_pairs_hook=_unique_object,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError("INVALID_JSON_CONSTANT")))
        if isinstance(message, dict):
            if isinstance(message.get("requestId"), str):
                request_id = message["requestId"]
            if isinstance(message.get("operation"), str):
                operation = message["operation"]
        request = validate_request(message, expected_backend=backend)
        result = runtime.dispatch(request)
        return 200, response(request_id, operation, ok=True, result=result,
                             backend=backend, execution=execution)
    except OverflowError:
        return 413, response(request_id, operation, ok=False,
            error={"code": "MESSAGE_TOO_LARGE", "message": "Echo payload exceeds 256 UTF-8 bytes"},
            backend=backend, execution=execution)
    except LookupError as error:
        code = str(error)
        return (409 if code == "BACKEND_MISMATCH" else 400), response(request_id, operation, ok=False,
            error={"code": code, "message": "Bridge request is not supported"},
            backend=backend, execution=execution)
    except (ValueError, UnicodeDecodeError) as error:
        return 400, response(request_id, operation, ok=False,
            error={"code": "INVALID_REQUEST", "message": str(error)[:160]},
            backend=backend, execution=execution)
    except RecursionError:
        return 400, response(request_id, operation, ok=False,
            error={"code": "INVALID_REQUEST", "message": "JSON nesting limit exceeded"},
            backend=backend, execution=execution)
    except Exception as error:
        if hasattr(error, "code"):
            code = error.code
            status = getattr(error, "status", 502)
            message = str(error)[:160]
        else:
            code, status, message = "BACKEND_FAILURE", 502, "Backend request failed"
        return status, response(request_id, operation, ok=False,
            error={"code": code, "message": message}, backend=backend, execution=execution)
