"""Runtime adapters for the native C bridge and deterministic HTTP simulator."""

import ctypes
import json
import os
import platform
from pathlib import Path

from bridge.http_service import NS2JB_UNAVAILABLE_NOTE, OPERATIONS, ns2jb_compatibility_result

W2JB_BACKEND_MOCK = 1
W2JB_BACKEND_LINUX = 2
W2JB_PROTOCOL_VERSION = 1
OPERATION_IDS = {"capabilities": 1, "diagnostic": 2, "echo": 3, "connectivity": 4,
                 "ns2jb-compatibility": 5, "memory-policy": 6}
STATUS_NAMES = {
    0: "OK", 1: "INVALID_ARGUMENT", 2: "NOT_INITIALIZED", 3: "PROTOCOL_UNSUPPORTED",
    4: "MESSAGE_TOO_LARGE", 5: "INVALID_REQUEST_ID", 6: "UNSUPPORTED_OPERATION",
    7: "BACKEND_FAILURE", 8: "CAPABILITY_UNAVAILABLE", 9: "MEMORY_POLICY_DENIED",
}


class CConfig(ctypes.Structure):
    _fields_ = [("struct_size", ctypes.c_uint32), ("backend", ctypes.c_int),
                ("timeout_ms", ctypes.c_uint32), ("mock_fail_requests", ctypes.c_int),
                ("logger", ctypes.c_void_p), ("logger_context", ctypes.c_void_p)]


class CRequest(ctypes.Structure):
    _fields_ = [("protocol_version", ctypes.c_uint32), ("request_id", ctypes.c_char_p),
                ("operation", ctypes.c_int), ("payload", ctypes.POINTER(ctypes.c_uint8)),
                ("payload_size", ctypes.c_size_t)]


class CReply(ctypes.Structure):
    _fields_ = [("protocol_version", ctypes.c_uint32), ("request_id", ctypes.c_char * 65),
                ("backend_id", ctypes.c_char * 32), ("status", ctypes.c_int),
                ("simulated", ctypes.c_int), ("native_process", ctypes.c_int),
                ("switch_native_execution", ctypes.c_int), ("result", ctypes.c_char * 2048)]


class CMemoryPolicy(ctypes.Structure):
    _fields_ = [("writable_executable_allocations", ctypes.c_int),
                ("code_data_permissions_separate", ctypes.c_int),
                ("effective_permissions_verifiable", ctypes.c_int),
                ("permission_verification", ctypes.c_char_p)]


class BridgeBackendError(Exception):
    def __init__(self, code, message, status=502):
        super().__init__(message)
        self.code = code
        self.status = status


class SimulatedRuntime:
    backend_id = "pc-simulated"

    def handshake(self):
        return {
            "backend": self.backend_id, "platform": "pc", "simulated": True,
            "architecture": platform.machine().lower(),
            "capabilities": sorted(OPERATIONS), "nativeLibraryLoaded": False,
            "nativeProcessConnected": False, "switchNativeExecution": False,
            "memoryPolicy": {"overall": "UNSUPPORTED", "verification": "Python simulator has no process-map access"},
        }

    def dispatch(self, request):
        operation = request["operation"]
        if operation == "ns2jb-compatibility":
            return ns2jb_compatibility_result(
                simulated=True,
                note="Python simulator: no NS2JB runtime or upstream IPC is connected",
            )
        if operation == "capabilities":
            return {"available": sorted(OPERATIONS), "backend": self.backend_id, "simulated": True}
        if operation == "diagnostic":
            return {"message": "Python HTTP simulator responded", "performed": True}
        if operation == "connectivity":
            return {"serviceReachable": True, "scope": "this HTTP exchange only"}
        if operation == "memory-policy":
            return {"abiVersion": 1, "backend": self.backend_id, "overall": "UNSUPPORTED",
                    "writableExecutableRegions": 0, "regions": [],
                    "simulated": True,
                    "reason": "simulator cannot inspect process memory permissions"}
        return {"message": request["payload"]["message"]}

    def execution(self):
        return {"mode": "simulated", "platform": "pc", "origin": "python-simulator",
                "architecture": platform.machine().lower(),
                "nativeLibraryLoaded": False, "nativeProcessConnected": False,
                "switchNativeExecution": False}

    def close(self):
        return None


class NativeCRuntime:
    def __init__(self, library_path, backend_id, c_backend, mock_failure=False):
        self.backend_id = backend_id
        self.c_backend = c_backend
        self.library_path = str(Path(library_path).resolve())
        self.library = ctypes.CDLL(self.library_path)
        self.handle = ctypes.c_void_p()
        self._configure_signatures()
        config = CConfig(ctypes.sizeof(CConfig), c_backend, 1500, int(mock_failure), None, None)
        status = self.library.w2jb_bridge_init(ctypes.byref(config), ctypes.byref(self.handle))
        self._raise_for_status(status, "bridge initialization failed")

    def _configure_signatures(self):
        self.library.w2jb_bridge_init.argtypes = [ctypes.POINTER(CConfig), ctypes.POINTER(ctypes.c_void_p)]
        self.library.w2jb_bridge_init.restype = ctypes.c_int
        self.library.w2jb_bridge_shutdown.argtypes = [ctypes.c_void_p]
        self.library.w2jb_bridge_shutdown.restype = None
        self.library.w2jb_bridge_request.argtypes = [ctypes.c_void_p, ctypes.POINTER(CRequest), ctypes.POINTER(CReply)]
        self.library.w2jb_bridge_request.restype = ctypes.c_int
        self.library.w2jb_bridge_detect_capabilities.argtypes = [ctypes.c_void_p, ctypes.POINTER(CReply)]
        self.library.w2jb_bridge_detect_capabilities.restype = ctypes.c_int
        self.library.w2jb_bridge_get_memory_policy.argtypes = []
        self.library.w2jb_bridge_get_memory_policy.restype = CMemoryPolicy
        self.library.w2jb_status_name.argtypes = [ctypes.c_int]
        self.library.w2jb_status_name.restype = ctypes.c_char_p

    def _raise_for_status(self, status, context):
        if status == 0:
            return
        code = STATUS_NAMES.get(status, "BACKEND_FAILURE")
        http_status = 413 if status == 4 else (503 if status == 8 else 502)
        raise BridgeBackendError(code, context + ": " + code, http_status)

    @staticmethod
    def _text(value):
        return bytes(value).split(b"\0", 1)[0].decode("utf-8", "replace")

    def _call(self, operation, request_id, payload=b""):
        request_id_bytes = request_id.encode("ascii")
        payload_buffer = ctypes.create_string_buffer(payload) if payload else None
        payload_pointer = (ctypes.cast(payload_buffer, ctypes.POINTER(ctypes.c_uint8))
                           if payload_buffer is not None else ctypes.POINTER(ctypes.c_uint8)())
        request = CRequest(W2JB_PROTOCOL_VERSION, request_id_bytes, OPERATION_IDS[operation],
                           payload_pointer, len(payload))
        reply = CReply()
        status = self.library.w2jb_bridge_request(self.handle, ctypes.byref(request), ctypes.byref(reply))
        self._raise_for_status(status, "C backend request failed")
        if self._text(reply.request_id) != request_id:
            raise BridgeBackendError("CORRELATION_MISMATCH", "C backend returned a different requestId")
        return reply

    def handshake(self):
        reply = CReply()
        status = self.library.w2jb_bridge_detect_capabilities(self.handle, ctypes.byref(reply))
        self._raise_for_status(status, "C backend capability request failed")
        memory = self.library.w2jb_bridge_get_memory_policy()
        capabilities = sorted(OPERATIONS)
        return {
            "backend": self.backend_id,
            "platform": "linux",
            "architecture": platform.machine().lower(),
            "simulated": bool(reply.simulated),
            "capabilities": capabilities,
            "nativeLibraryLoaded": True,
            "nativeProcessConnected": False,
            "switchNativeExecution": False,
            "cBackend": self._text(reply.backend_id),
            "capabilitySummary": self._text(reply.result),
            "memoryPolicy": {
                "codeDataPermissionsSeparate": bool(memory.code_data_permissions_separate),
                "effectivePermissionsVerifiable": bool(memory.effective_permissions_verifiable),
                "overall": "UNVERIFIED",
                "verification": self._text(memory.permission_verification),
            },
        }

    def dispatch(self, request):
        operation = request["operation"]
        payload = request["payload"].get("message", "").encode("utf-8") if operation == "echo" else b""
        reply = self._call(operation, request["requestId"], payload)
        text = self._text(reply.result)
        if operation == "echo":
            return {"message": text[5:] if text.startswith("echo:") else text}
        if operation == "diagnostic":
            return {"message": text, "performed": True}
        if operation == "connectivity":
            return {"serviceReachable": True, "scope": "C backend call in this server process", "message": text}
        if operation == "ns2jb-compatibility":
            try:
                result = json.loads(text)
            except (TypeError, ValueError) as error:
                raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C adapter returned invalid JSON") from error
            expected = ns2jb_compatibility_result(
                simulated=False, note=NS2JB_UNAVAILABLE_NOTE,
            )
            expected.pop("simulated")
            if result != expected:
                raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C adapter claimed unverified capability")
            result["simulated"] = self.c_backend == W2JB_BACKEND_MOCK
            return result
        if operation == "memory-policy":
            try:
                result = json.loads(text)
            except (TypeError, ValueError) as error:
                raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy result was not valid JSON") from error
            expected_backend = "linux-local" if self.c_backend == W2JB_BACKEND_LINUX else "mock"
            expected_regions = {"code": "r-x", "constant": "r--", "mutable": "rw-", "heap": "rw-", "stack": "rw-"}
            if (not isinstance(result, dict) or result.get("abiVersion") != 1 or
                    result.get("backend") != expected_backend or
                    result.get("overall") not in ("PASS", "FAIL", "UNVERIFIED", "UNSUPPORTED") or
                    not isinstance(result.get("writableExecutableRegions"), int) or
                    result.get("writableExecutableRegions") < 0 or
                    not isinstance(result.get("regions"), list)):
                raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy result failed schema validation")
            seen = set()
            for region in result["regions"]:
                if (not isinstance(region, dict) or
                        set(region) != {"name", "expected", "observed", "status"} or
                        region.get("name") not in expected_regions or
                        region.get("expected") != expected_regions[region["name"]] or
                        region.get("observed") not in ("r--", "rw-", "r-x", "rwx", "-w-", "--x", "-wx", "---") or
                        region.get("status") not in ("PASS", "FAIL", "UNVERIFIED", "UNSUPPORTED") or
                        ("w" in region["observed"] and "x" in region["observed"])):
                    raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy region failed schema validation")
                if region["status"] == "PASS" and region["observed"] != region["expected"]:
                    raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy PASS did not match expected permissions")
                if region["name"] in seen:
                    raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy result duplicated a region")
                seen.add(region["name"])
            if seen != set(expected_regions):
                raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy result omitted a region")
            sampled_rwx = sum(1 for region in result["regions"] if region["observed"] == "rwx")
            if sampled_rwx != result["writableExecutableRegions"]:
                raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy RWX count did not match sampled regions")
            if result["overall"] == "PASS" and any(region["status"] != "PASS" for region in result["regions"]):
                raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy PASS included an unverified region")
            if sampled_rwx and result["overall"] != "FAIL":
                raise BridgeBackendError("INVALID_BACKEND_RESPONSE", "C memory-policy RWX observation did not fail the policy")
            result["simulated"] = bool(reply.simulated)
            return result
        return {"available": sorted(OPERATIONS), "backend": self.backend_id, "simulated": bool(reply.simulated),
                "capabilitySummary": text}

    def execution(self):
        return {
            "mode": "simulated" if self.c_backend == W2JB_BACKEND_MOCK else "native-library",
            "platform": "linux",
            "architecture": platform.machine().lower(),
            "origin": "ctypes-loaded-library",
            "nativeLibraryLoaded": True,
            "nativeProcessConnected": False,
            "switchNativeExecution": False,
        }

    def close(self):
        if self.handle:
            self.library.w2jb_bridge_shutdown(self.handle)
            self.handle = ctypes.c_void_p()


class UnavailableRuntime:
    backend_id = "unavailable"

    def __init__(self, reason):
        self.reason = str(reason)[:240]

    def handshake(self):
        return {"backend": self.backend_id, "platform": "unknown", "simulated": False,
                "architecture": "unknown",
                "capabilities": [], "nativeLibraryLoaded": False, "nativeProcessConnected": False,
                "switchNativeExecution": False, "unavailableReason": self.reason}

    def execution(self):
        return {"mode": "none", "platform": "unknown", "architecture": "unknown", "origin": "unavailable",
                "nativeLibraryLoaded": False, "nativeProcessConnected": False,
                "switchNativeExecution": False}

    def dispatch(self, request):
        raise BridgeBackendError("CAPABILITY_UNAVAILABLE", self.reason, 503)

    def close(self):
        return None


def runtime_from_environment():
    requested = os.environ.get("NS2_BRIDGE_BACKEND", "linux-native").strip().lower()
    if requested == "pc-simulated":
        return SimulatedRuntime()
    if requested not in ("linux-native", "linux-mock"):
        return UnavailableRuntime("Backend is not available in this HTTP service: " + requested)
    default_path = Path(__file__).resolve().parents[1] / "build" / "libwebkit2jb_bridge.so"
    library_path = os.environ.get("NS2_BRIDGE_LIBRARY", str(default_path))
    c_backend = W2JB_BACKEND_LINUX if requested == "linux-native" else W2JB_BACKEND_MOCK
    try:
        return NativeCRuntime(library_path, requested, c_backend,
                              mock_failure=os.environ.get("NS2_BRIDGE_MOCK_FAIL", "0") == "1")
    except (OSError, AttributeError, BridgeBackendError) as error:
        return UnavailableRuntime("Could not load " + requested + ": " + str(error))
