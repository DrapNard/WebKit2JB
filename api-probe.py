#!/usr/bin/env python3
"""WebKit/WKC diagnostic server for the Nintendo captive portal.

Standard library only. Pages and JavaScript tests are stored in separate files
to keep HTML out of the Python server source.
"""

from __future__ import annotations

import json
import fcntl
import hashlib
import os
import re
import signal
import threading
import subprocess
import sys
import struct
import uuid
from base64 import b64decode
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from bridge.http_service import MAX_REQUEST_BYTES as MAX_BRIDGE_BYTES
from bridge.http_service import OPERATIONS as BRIDGE_OPERATIONS
from bridge.http_service import PROTOCOL as BRIDGE_PROTOCOL
from bridge.http_service import handshake as bridge_handshake_response
from bridge.http_service import process_request as process_bridge_request
from bridge.http_service import response as bridge_response
from bridge.http_service import validate_request as validate_bridge_request
from bridge.python.runtime import runtime_from_environment
from bridge.artifacts import inspect_file

ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("NS2_HOST", "127.0.0.1")
PORT = int(os.environ.get("NS2_PORT", "80"))
OUT = Path(os.environ.get("NS2_OUT", str(ROOT / "runs"))).expanduser()
MAX_REPORT_BYTES = 65536
REPORT_LOCK = threading.Lock()
BRIDGE_RUNTIME_LOCK = threading.Lock()
BRIDGE_RUNTIME = None
REPORT_IDS: dict[str, Path] = {}
SERVED_SCRIPT_NAMES = frozenset(("diagnostics.js", "portal.js", "bridge-client.js", "shared/capabilities.js", "shared/reporting.js"))
SERVED_RESOURCE_NAMES = frozenset(("style.css", "fonts/ns2-test-font.ttf", "schemas/ns2-diagnostic-envelope-v1.schema.json", "bridge/protocol/bridge-v1.schema.json"))
SERVED_ASSETS_LOCK = threading.Lock()
SERVED_ASSETS_BY_CLIENT: dict[str, dict[str, object]] = {}


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


SERVER_SOURCE_SHA256 = _file_sha256(Path(__file__).resolve())
REPORT_ENVELOPE_SCHEMA_PATH = ROOT / "schemas" / "ns2-diagnostic-envelope-v1.schema.json"
REPORT_ENVELOPE_SCHEMA = json.loads(REPORT_ENVELOPE_SCHEMA_PATH.read_text(encoding="utf-8"))
REPORT_SCHEMA_SHA256 = _file_sha256(REPORT_ENVELOPE_SCHEMA_PATH)
BRIDGE_SERVICE_SOURCE_SHA256 = _file_sha256(ROOT / "bridge" / "http_service.py")
BRIDGE_RUNTIME_SOURCE_SHA256 = _file_sha256(ROOT / "bridge" / "python" / "runtime.py")
HORIZON_BUILD_MANIFEST_PATH = ROOT / "bridge" / "build-horizon" / "build-info.json"
PC_RUNNER_MANIFEST_PATH = ROOT / "bridge" / "resources" / "pc-runner-example.manifest.json"


def get_bridge_runtime():
    global BRIDGE_RUNTIME
    if BRIDGE_RUNTIME is None:
        with BRIDGE_RUNTIME_LOCK:
            if BRIDGE_RUNTIME is None:
                BRIDGE_RUNTIME = runtime_from_environment()
    return BRIDGE_RUNTIME


def horizon_build_evidence(manifest_path: Path = HORIZON_BUILD_MANIFEST_PATH) -> dict:
    """Return compiled-only evidence after checking the NRO, ELF and embedded NACP hashes."""
    unavailable = {"status": "UNAVAILABLE", "executionConfirmed": False}
    try:
        manifest_path = Path(manifest_path)
        if manifest_path.stat().st_size > 8192:
            return unavailable
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        name = manifest.get("artifact") if isinstance(manifest, dict) else None
        if (manifest.get("schema") != "webkit2jb-horizon-build/1"
                or manifest.get("status") != "HORIZON_COMPILED"
                or manifest.get("target") != "horizon-homebrew"
                or manifest.get("architecture") != "aarch64"
                or manifest.get("executionConfirmed") is not False
                or type(manifest.get("sourceDirty")) is not bool
                or not isinstance(manifest.get("sourceCommit"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", manifest["sourceCommit"])
                or not isinstance(manifest.get("toolchain"), str)
                or not manifest["toolchain"]
                or not isinstance(name, str) or Path(name).name != name
                or name != "w2jb-horizon-demo.nro"):
            return unavailable
        artifact = manifest_path.parent / name
        if artifact.resolve().parent != manifest_path.parent.resolve():
            return unavailable
        elf = manifest_path.parent / "w2jb-horizon-demo.elf"
        nacp = manifest_path.parent / "w2jb-horizon-demo.nacp"
        if any(path.resolve().parent != manifest_path.parent.resolve() for path in (elf, nacp)):
            return unavailable
        nro_info = inspect_file(artifact)
        elf_info = inspect_file(elf)
        if (nro_info.get("format") != "NRO" or not nro_info.get("embeddedNacp")
                or elf_info.get("format") != "ELF64" or elf_info.get("architecture") != "aarch64"
                or type(manifest.get("artifactSize")) is not int
                or nro_info["size"] != manifest["artifactSize"]
                or nro_info["sha256"] != manifest.get("artifactSha256")
                or elf_info["sha256"] != manifest.get("elfSha256")):
            return unavailable
        nacp_bytes = nacp.read_bytes()
        if (len(nacp_bytes) != 0x4000
                or hashlib.sha256(nacp_bytes).hexdigest() != manifest.get("nacpSha256")
                or nro_info.get("embeddedNacpFileOffset") is None):
            return unavailable
        data = artifact.read_bytes()
        offset = nro_info["embeddedNacpFileOffset"]
        if data[offset:offset + 0x4000] != nacp_bytes:
            return unavailable
        title = nacp_bytes[:0x200].split(b"\0", 1)[0].decode("utf-8", "replace")
        author = nacp_bytes[0x200:0x300].split(b"\0", 1)[0].decode("utf-8", "replace")
        version = nacp_bytes[0x3060:0x3070].split(b"\0", 1)[0].decode("utf-8", "replace")
        if (title != manifest.get("title") or author != manifest.get("author")
                or version != manifest.get("version") or version != "0.1.0"):
            return unavailable
        return {
            "status": "HORIZON_COMPILED",
            "executionConfirmed": False,
            "artifact": name,
            "artifactSize": nro_info["size"],
            "artifactSha256": nro_info["sha256"],
            "elfSha256": elf_info["sha256"],
            "nacpSha256": hashlib.sha256(nacp_bytes).hexdigest(),
            "sourceCommit": manifest["sourceCommit"],
            "sourceDirty": manifest["sourceDirty"],
            "toolchain": manifest["toolchain"][:160],
        }
    except (OSError, ValueError, TypeError, AttributeError, struct.error):
        return unavailable


def pc_runner_artifact_evidence(manifest_path: Path = PC_RUNNER_MANIFEST_PATH) -> dict:
    """Read-only validation of the PC runner's example ELF; never extracts or executes it."""
    unavailable = {"status": "UNAVAILABLE", "executionConfirmed": False,
                   "execution": "not-run", "origin": "pc-artifact-inspector"}
    try:
        manifest_path = Path(manifest_path)
        if manifest_path.stat().st_size > 4096:
            return unavailable
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or set(manifest) != {
                "schema", "artifact", "format", "architecture", "elfType", "size",
                "capacity", "sha256", "origin", "execution"}:
            return unavailable
        if (manifest["schema"] != "webkit2jb-pc-runner-artifact/1"
                or manifest["artifact"] != "pc-runner-example.elf"
                or manifest["format"] != "ELF64"
                or manifest["architecture"] != "x86_64"
                or manifest["elfType"] != "ET_EXEC"
                or manifest["origin"] != "webkit-podman-lab/research/uaf-x86-lab/resources/embedded-program.elf"
                or manifest["execution"] != "metadata-only"
                or type(manifest["size"]) is not int or manifest["size"] < 1
                or type(manifest["capacity"]) is not int
                or not 1 <= manifest["capacity"] <= 65536
                or manifest["size"] > manifest["capacity"]
                or not isinstance(manifest["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", manifest["sha256"])):
            return unavailable
        artifact = manifest_path.parent / manifest["artifact"]
        if artifact.resolve().parent != manifest_path.parent.resolve():
            return unavailable
        info = inspect_file(artifact, max_bytes=manifest["capacity"])
        if (info.get("format") != "ELF64" or info.get("architecture") != "x86_64"
                or info.get("elfType") != "ET_EXEC"
                or info.get("size") != manifest["size"]
                or info.get("sha256") != manifest["sha256"]
                or info.get("executableStackRequested") is not False):
            return unavailable
        return {
            "status": "PC_ARTIFACT_VALIDATED",
            "executionConfirmed": False,
            "execution": "not-run",
            "inspection": "format-and-integrity-only",
            "origin": "pc-artifact-inspector",
            "artifact": manifest["artifact"],
            "format": info["format"],
            "architecture": info["architecture"],
            "elfType": info["elfType"],
            "size": info["size"],
            "capacity": manifest["capacity"],
            "sha256": info["sha256"],
            "executableStackRequested": info["executableStackRequested"],
            "loadSegments": info["loadSegments"],
            "horizonCompatible": False,
        }
    except (OSError, ValueError, TypeError, AttributeError, struct.error):
        return unavailable


def platform_evidence(backend: str) -> dict:
    return {
        "pc": "PC_NATIVE" if backend == "linux-native" else "UNAVAILABLE",
        "pcRunnerArtifact": pc_runner_artifact_evidence(),
        "horizonBuild": horizon_build_evidence(),
        # No console execution proof is available in this HTTP service.
        "horizonExecution": {"status": "UNAVAILABLE", "executionConfirmed": False},
    }


def validate_report_envelope(report: dict) -> None:
    """Validate reports opting into the versioned envelope; legacy reports remain accepted."""
    if "reportEnvelopeVersion" not in report:
        return
    if report.get("reportEnvelopeVersion") != REPORT_ENVELOPE_SCHEMA["properties"]["reportEnvelopeVersion"]["const"]:
        raise ValueError("reportEnvelopeVersion non pris en charge")
    required = tuple(REPORT_ENVELOPE_SCHEMA["required"])
    missing = [key for key in required if key not in report]
    if missing:
        raise ValueError("Missing report fields: " + ", ".join(missing))
    schema_limits = REPORT_ENVELOPE_SCHEMA["properties"]["schema"]
    if not isinstance(report["schema"], str) or not schema_limits["minLength"] <= len(report["schema"]) <= schema_limits["maxLength"]:
        raise ValueError("invalid schema")
    if type(report["schemaVersion"]) is not int or report["schemaVersion"] < 1:
        raise ValueError("invalid schemaVersion")
    for key, maximum in (("reportId", 80), ("sessionId", 100), ("testVersion", 32)):
        value = report[key]
        if not isinstance(value, str) or not 1 <= len(value) <= maximum:
            raise ValueError(key + " is invalid")
    if report["testId"] not in REPORT_ENVELOPE_SCHEMA["properties"]["testId"]["enum"]:
        raise ValueError("testId inconnu")
    if not isinstance(report["startedAt"], str) or not 20 <= len(report["startedAt"]) <= 40:
        raise ValueError("startedAt is invalid")
    if not isinstance(report["capabilities"], dict):
        raise ValueError("capabilities must be an object")
    for key in ("userAgent", "origin"):
        if key in report and report[key] is not None and not isinstance(report[key], str):
            raise ValueError(key + " must be a string or null")
    if "result" in report and (not isinstance(report["result"], str) or len(report["result"]) > 64):
        raise ValueError("result is invalid")
    events = report["events"]
    errors = report["errors"]
    if not isinstance(events, list) or len(events) > REPORT_ENVELOPE_SCHEMA["properties"]["events"]["maxItems"]:
        raise ValueError("events is invalid or too long")
    if not isinstance(errors, list) or len(errors) > REPORT_ENVELOPE_SCHEMA["properties"]["errors"]["maxItems"]:
        raise ValueError("errors is invalid or too long")
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("name"), str) or not 1 <= len(event["name"]) <= 100:
            raise ValueError("invalid event")
        if not isinstance(event.get("timestamp"), str) or not 20 <= len(event["timestamp"]) <= 40:
            raise ValueError("timestamp d’invalid event")
        if type(event.get("elapsedMs")) is not int or event["elapsedMs"] < 0:
            raise ValueError("elapsedMs is invalid")
        if not isinstance(event.get("info"), dict):
            raise ValueError("event info must be an object")
        state = event.get("state")
        if state is not None and not isinstance(state, dict):
            raise ValueError("event state must be an object")
        if state is not None:
            for key in ("documentFontsStatus", "fontFaceStatus"):
                if key in state and state[key] is not None and not isinstance(state[key], str):
                    raise ValueError("state." + key + " must be a string or null")
            if "documentFontsSize" in state and state["documentFontsSize"] is not None:
                if type(state["documentFontsSize"]) is not int or state["documentFontsSize"] < 0:
                    raise ValueError("state.documentFontsSize is invalid")
    for error in errors:
        if not isinstance(error, dict):
            raise ValueError("invalid report error")
        missing_error_fields = [key for key in ("phase", "name", "message") if key not in error]
        if missing_error_fields:
            raise ValueError("Missing error fields: " + ", ".join(missing_error_fields))
        for key, maximum in (("phase", 64), ("name", 128), ("message", 1024)):
            if not isinstance(error[key], str) or len(error[key]) > maximum:
                raise ValueError("invalid error field: " + key)


def start_served_page(client_ip: str, data: bytes) -> None:
    """Start a per-client asset record when the portal document is served."""
    with SERVED_ASSETS_LOCK:
        if client_ip not in SERVED_ASSETS_BY_CLIENT and len(SERVED_ASSETS_BY_CLIENT) >= 256:
            SERVED_ASSETS_BY_CLIENT.pop(next(iter(SERVED_ASSETS_BY_CLIENT)))
        SERVED_ASSETS_BY_CLIENT[client_ip] = {
            "pageSha256": hashlib.sha256(data).hexdigest(),
            "scriptsSha256": {},
            "resourcesSha256": {},
        }


def record_served_script(client_ip: str, filename: str, data: bytes) -> None:
    if filename not in SERVED_SCRIPT_NAMES:
        return
    with SERVED_ASSETS_LOCK:
        assets = SERVED_ASSETS_BY_CLIENT.setdefault(
            client_ip, {"pageSha256": None, "scriptsSha256": {}, "resourcesSha256": {}}
        )
        scripts = assets["scriptsSha256"]
        if isinstance(scripts, dict):
            scripts[filename] = hashlib.sha256(data).hexdigest()


def record_served_resource(client_ip: str, filename: str, data: bytes) -> None:
    if filename not in SERVED_RESOURCE_NAMES:
        return
    with SERVED_ASSETS_LOCK:
        assets = SERVED_ASSETS_BY_CLIENT.setdefault(
            client_ip, {"pageSha256": None, "scriptsSha256": {}, "resourcesSha256": {}}
        )
        resources = assets.setdefault("resourcesSha256", {})
        if isinstance(resources, dict):
            resources[filename] = hashlib.sha256(data).hexdigest()


def build_provenance(client_ip: str) -> dict:
    """Bind a saved report to Git state and the static app bytes sent to its client."""
    commit = None
    dirty = None
    try:
        commit_result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True, timeout=3,
        )
        commit = commit_result.stdout.strip()
        status_result = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
            check=True, capture_output=True, text=True, timeout=3,
        )
        dirty = bool(status_result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass

    with SERVED_ASSETS_LOCK:
        assets = dict(SERVED_ASSETS_BY_CLIENT.get(client_ip, {}))
        scripts = dict(assets.get("scriptsSha256", {}))
        resources = dict(assets.get("resourcesSha256", {}))
    page_hash = assets.get("pageSha256")
    identity = {
        "gitCommit": commit,
        "dirty": dirty,
        "serverSha256": SERVER_SOURCE_SHA256,
        "bridgeServiceSha256": BRIDGE_SERVICE_SOURCE_SHA256,
        "bridgeRuntimeSha256": BRIDGE_RUNTIME_SOURCE_SHA256,
        "servedPageSha256": page_hash,
        "servedScriptsSha256": scripts,
        "servedResourcesSha256": resources,
        "reportSchemaSha256": REPORT_SCHEMA_SHA256,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        **identity,
        "buildId": "ns2-" + hashlib.sha256(encoded).hexdigest()[:20],
    }


def instance_lock_path() -> Path:
    override = os.environ.get("NS2_LOCK_PATH")
    if override:
        return Path(override).expanduser()
    safe_host = re.sub(r"[^A-Za-z0-9_.-]", "_", HOST)
    return ROOT / "runs" / f".api-probe-{safe_host}-{PORT}.lock"


def acquire_instance_lock(path: Path | None = None):
    """Hold a per-bind-address lock until the HTTP server exits."""
    lock_path = path or instance_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("a+", encoding="ascii")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.seek(0)
        owner = lock_file.read().strip() or "unknown PID"
        lock_file.close()
        raise RuntimeError(f"A portal HTTP instance already holds {lock_path} ({owner}).")
    lock_file.seek(0)
    lock_file.truncate()
    lock_file.write(f"pid={os.getpid()} host={HOST} port={PORT}\n")
    lock_file.flush()
    return lock_file

HOME_CSP = (
    "default-src 'self' blob:; "
    "script-src 'self' 'unsafe-inline' blob:; "
    "worker-src 'self' blob:; "
    "child-src 'self' blob:; "
    "connect-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'"
)

HEADERS = {
    "plain": ("text/plain", []),
    "nosniff": ("text/plain", ["nosniff"]),
    "invalid-first": ("text/plain", ["invalid", "nosniff"]),
    "nosniff-first": ("text/plain", ["nosniff", "invalid"]),
    "double-nosniff": ("text/plain", ["nosniff", "nosniff"]),
    "javascript": ("application/javascript", ["nosniff"]),
}

CSP = {
    "baseline": [("Content-Security-Policy", "script-src 'self' 'unsafe-inline'")],
    "last-allows": [
        ("Content-Security-Policy", "script-src 'none'"),
        ("Content-Security-Policy", "script-src 'self' 'unsafe-inline'"),
    ],
    "last-blocks": [
        ("Content-Security-Policy", "script-src 'self' 'unsafe-inline'"),
        ("Content-Security-Policy", "script-src 'none'"),
    ],
    "comma": [("Content-Security-Policy", "script-src 'none', script-src 'self' 'unsafe-inline'")],
    "duplicate-directive": [
        ("Content-Security-Policy", "script-src 'none'; script-src 'self' 'unsafe-inline'")
    ],
    "empty-directives": [
        ("Content-Security-Policy", ";;; script-src 'self' 'unsafe-inline';;")
    ],
    "invalid-source": [
        ("Content-Security-Policy", "script-src http://example.com:99999 'self' 'unsafe-inline'")
    ],
    "report-only": [("Content-Security-Policy-Report-Only", "script-src 'none'")],
}

REDIRECT_CODES = {"post302": 302, "post303": 303, "post307": 307}
FILE_TESTS = {
    "/probe-a": ("text/plain", False),
    "/probe-b": ("text/plain", True),
    "/probe-c": ("application/octet-stream", False),
}
GIF_1PX = b64decode("R0lGODlhAQABAAD/ACwAAAAAAQABAAACAUwAOw==")


def save_report(data: dict, client_ip: str) -> Path:
    """Store FontFace diagnostics separately from legacy probes."""
    report = dict(data)
    report.setdefault("schemaVersion", 2)
    report.setdefault("reportId", uuid.uuid4().hex)
    report.setdefault("sessionId", "legacy-" + report["reportId"])
    report["receivedAt"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    report["clientIP"] = client_ip
    if report.get("reportEnvelopeVersion") == 1:
        report["schemaValidation"] = "ns2-diagnostic-envelope-v1"
    report.update(build_provenance(client_ip))
    try:
        from analyze_runs import analyze_report
        report["comparison"] = analyze_report(report, OUT)
    except (OSError, ValueError, ImportError) as error:
        report["comparison"] = {"error": str(error)}
    schema = str(report.get("schema", report.get("test", "")))
    is_fontface = schema.startswith(("ns2-fontface-survey", "ns2-fontface-custom-load"))
    directory = OUT / "fontface-survey" if is_fontface else OUT
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    prefix = "fontface" if directory != OUT else "api-probe"
    path = directory / f"{prefix}-{stamp}-{uuid.uuid4().hex[:6]}.json"
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)
    print("[REPORT]", path, flush=True)
    return path


class Handler(BaseHTTPRequestHandler):
    server_version = "NS2-WebKit-Lab/2.0"

    def send_bytes(
        self,
        content: bytes = b"",
        *,
        status: int = 200,
        mime: str = "text/plain; charset=utf-8",
        headers: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
        cache: str = "no-store",
    ) -> None:
        self.send_response(status)
        if status not in (204, 304):
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", cache)
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD" and status not in (204, 304):
            self.wfile.write(content)

    def send_file(self, filename: str, mime: str, *, csp: bool = False) -> None:
        """Sert uniquement des noms statiques connus, pas de chemin client."""
        path = ROOT / filename
        try:
            data = path.read_bytes()
        except OSError:
            self.send_error(404, f"Fichier manquant : {filename}")
            return
        if filename == "index.html" and self.command == "GET":
            start_served_page(self.client_address[0], data)
        headers = [
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
        ]
        if csp:
            headers.append(("Content-Security-Policy", HOME_CSP))
        self.send_bytes(data, mime=mime, headers=headers)
        if self.command == "GET":
            record_served_script(self.client_address[0], filename, data)
            record_served_resource(self.client_address[0], filename, data)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        args = parse_qs(parsed.query)

        pages = {
            "/": ("index.html", "text/html; charset=utf-8", True),
            "/index.html": ("index.html", "text/html; charset=utf-8", True),
            "/diagnostics.js": ("diagnostics.js", "application/javascript; charset=utf-8", False),
            "/portal.js": ("portal.js", "application/javascript; charset=utf-8", False),
            "/shared/capabilities.js": ("shared/capabilities.js", "application/javascript; charset=utf-8", False),
            "/shared/reporting.js": ("shared/reporting.js", "application/javascript; charset=utf-8", False),
            "/bridge-client.js": ("bridge-client.js", "application/javascript; charset=utf-8", False),
            "/schemas/ns2-diagnostic-envelope-v1.schema.json": ("schemas/ns2-diagnostic-envelope-v1.schema.json", "application/schema+json; charset=utf-8", False),
            "/bridge/protocol/bridge-v1.schema.json": ("bridge/protocol/bridge-v1.schema.json", "application/schema+json; charset=utf-8", False),
            "/style.css": ("style.css", "text/css; charset=utf-8", False),
            "/fonts/ns2-test-font.ttf": ("fonts/ns2-test-font.ttf", "font/ttf", False),
        }
        if path in pages:
            filename, mime, csp = pages[path]
            self.send_file(filename, mime, csp=csp)
        elif path == "/favicon.ico":
            self.send_bytes(status=204)
        elif path == "/__ns2_ff_report":
            self.get_legacy_fontface_report(args)
        elif path == "/api/summary":
            self.summary_get()
        elif path == "/api/bridge":
            self.bridge_handshake()
        elif path == "/api/bridge/pc-runner-artifact":
            self.send_json(200, pc_runner_artifact_evidence())
        elif path == "/redir-target":
            self.redirect_target(args, "GET")
        elif path.startswith("/hdr-"):
            self.header_probe(path, args)
        elif path.startswith("/csp-"):
            self.csp_probe(path, args)
        elif path in ("/wkc-disk-candidate", "/wkc-disk-control"):
            self.disk_probe(path)
        elif path in ("/wkc-cacheable.gif", "/wkc-nostore.gif"):
            self.gif_probe(path)
        elif path in FILE_TESTS:
            mime, attachment = FILE_TESTS[path]
            headers = [("Content-Disposition", 'attachment; filename="uwu.txt"')] if attachment else []
            self.send_bytes(b"UwU from switch 2\n", mime=mime, headers=headers)
            print("[FILE-PROBE]", path, mime, attachment, flush=True)
        elif path == "/download-test":
            self.send_bytes(
                b"UwU from switch 2\n",
                mime="application/octet-stream",
                headers=[("Content-Disposition", 'attachment; filename="uwu-switch2.txt"')],
            )
            print("[DOWNLOAD] HTTP attachment requested", flush=True)
        else:
            self.send_error(404, "Route inconnue")

    def get_legacy_fontface_report(self, args: dict) -> None:
        """Compatibility with the legacy fontface-survey.html GET endpoint."""
        try:
            raw = args.get("data", [""])[0]
            if not raw or len(raw) > 16000:
                raise ValueError("Invalid or oversized report")
            report = json.loads(raw)
            if not isinstance(report, dict):
                raise ValueError("JSON object required")
            report.setdefault("schema", "ns2-fontface-survey-legacy")
            save_report(report, self.client_address[0])
        except (ValueError, TypeError, OSError) as error:
            print("[REPORT ERROR]", error, flush=True)
            self.send_error(400, "Invalid report")
            return
        self.send_bytes(status=204)

    def redirect_target(self, args: dict, method: str) -> None:
        case = args.get("case", [""])[0]
        if case not in REDIRECT_CODES:
            self.send_error(404)
            return
        print("[REDIR-TARGET]", case, method, flush=True)
        self.send_bytes(f"FINAL {method} {case}".encode("utf-8"))

    def header_probe(self, path: str, args: dict) -> None:
        name = args.get("name", [""])[0]
        if name not in HEADERS:
            self.send_error(404)
            return
        if path == "/hdr-beacon":
            print("[HEADER-BEACON]", name, args.get("kind", ["unknown"])[0], flush=True)
            self.send_bytes(status=204)
        elif path == "/hdr-script":
            mime, values = HEADERS[name]
            control = args.get("control", ["0"])[0] == "1"
            kind = "control" if control else "plain-script"
            js = f'new Image().src="/hdr-beacon?name={name}&kind={kind}";'
            headers = [] if control else [("X-Content-Type-Options", value) for value in values]
            self.send_bytes(js.encode(), mime="application/javascript" if control else mime, headers=headers)
            print("[HEADER-SCRIPT]", name, "control=" + str(control), flush=True)
        elif path == "/hdr-case":
            # name is constrained to HEADERS; no arbitrary HTML/query injection.
            html = (
                '<!doctype html><meta charset="utf-8">'
                f'<h2>Header test: {name}</h2><p>Document loaded.</p>'
                '<a href="/">Retour</a>'
                f'<script>new Image().src="/hdr-beacon?name={name}&kind=page";</script>'
                f'<script src="/hdr-script?name={name}"></script>'
                f'<script src="/hdr-script?name={name}&control=1"></script>'
            )
            self.send_bytes(html.encode(), mime="text/html; charset=utf-8")
            print("[HEADER-CASE]", name, flush=True)
        else:
            self.send_error(404)

    def csp_probe(self, path: str, args: dict) -> None:
        name = args.get("name", ["baseline"])[0]
        if name not in CSP:
            self.send_error(404)
            return
        if path == "/csp-beacon":
            print("[CSP-BEACON]", name, args.get("kind", ["unknown"])[0], flush=True)
            self.send_bytes(status=204)
        elif path == "/csp-js":
            js = f'new Image().src="/csp-beacon?name={name}&kind=external";'
            self.send_bytes(js.encode(), mime="text/javascript")
        elif path == "/csp-case":
            html = (
                '<!doctype html><meta charset="utf-8">'
                f'<title>CSP {name}</title><h2>CSP TEST: {name}</h2>'
                '<p>PAGE RENDERED: document is visible.</p>'
                '<a href="/">Retour aux tests</a>'
                f'<script>new Image().src="/csp-beacon?name={name}&kind=inline";</script>'
                f'<script src="/csp-js?name={name}"></script>'
            )
            self.send_bytes(html.encode(), mime="text/html; charset=utf-8", headers=CSP[name])
            print("[CSP-CASE]", name, flush=True)
        else:
            self.send_error(404)

    def disk_probe(self, path: str) -> None:
        cacheable = path == "/wkc-disk-candidate"
        data = b"UwU from switch 2\n" * 8192
        headers = [("ETag", '"ns2-wkc-disk-v1"')] if cacheable else []
        cache = "public, max-age=3600" if cacheable else "no-store"
        self.send_bytes(data, mime="text/plain; charset=utf-8", headers=headers, cache=cache)
        print("[WKC-DISK]", path, "If-None-Match=", self.headers.get("If-None-Match"), flush=True)

    def gif_probe(self, path: str) -> None:
        cacheable = path == "/wkc-cacheable.gif"
        etag = '"ns2-wkc-cache-v1"'
        cache = "public, max-age=600" if cacheable else "no-store"
        if cacheable and self.headers.get("If-None-Match") == etag:
            self.send_bytes(status=304, cache=cache, headers=[("ETag", etag)])
        else:
            self.send_bytes(GIF_1PX, mime="image/gif", cache=cache, headers=[("ETag", etag)])
        print("[WKC-CACHE-PROBE]", path, "If-None-Match=", self.headers.get("If-None-Match"), flush=True)

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        if path in ("/redir-start", "/redir-target"):
            self.redirect_post(path, parse_qs(parsed.query))
        elif path == "/api/bridge":
            self.bridge_post()
        elif path == "/api/report":
            self.report_post()
        else:
            self.send_error(404)

    def read_body(self, limit: int) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            self.send_error(400, "Content-Length incorrect")
            return None
        if not 0 <= length <= limit:
            self.send_error(413, "Request body too large")
            return None
        data = self.rfile.read(length)
        if len(data) != length:
            self.send_error(400, "Truncated request body")
            return None
        return data

    def bridge_handshake(self) -> None:
        status, response = bridge_handshake_response(get_bridge_runtime())
        if response.get("ok") and isinstance(response.get("result"), dict):
            response["result"]["platformEvidence"] = platform_evidence(response.get("backend", "unavailable"))
        self.send_json(status, response)

    def bridge_post(self) -> None:
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, bridge_response("invalid", "unknown", ok=False,
                error={"code": "CONTENT_TYPE_REQUIRED", "message": "application/json is required"}))
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length < 0:
            self.send_json(400, bridge_response("invalid", "unknown", ok=False,
                error={"code": "INVALID_LENGTH", "message": "Content-Length is invalid"}))
            return
        if length > MAX_BRIDGE_BYTES:
            self.send_json(413, bridge_response("invalid", "unknown", ok=False,
                error={"code": "MESSAGE_TOO_LARGE", "message": "Bridge request exceeds 4096 bytes"}))
            return
        raw = self.rfile.read(length)
        if len(raw) != length:
            self.send_json(400, bridge_response("invalid", "unknown", ok=False,
                error={"code": "TRUNCATED_MESSAGE", "message": "Bridge request was truncated"}))
            return
        status, response = process_bridge_request(raw, get_bridge_runtime())
        operation = response.get("operation", "unknown")
        logged_operation = operation if operation in BRIDGE_OPERATIONS else "invalid"
        print("[BRIDGE]", status, logged_operation,
              "backend=" + str(response.get("backend", "none")), flush=True)
        self.send_json(status, response)

    def redirect_post(self, path: str, args: dict) -> None:
        case = args.get("case", [""])[0]
        if case not in REDIRECT_CODES:
            self.send_error(404)
            return
        data = self.read_body(1024)
        if data is None:
            return
        if path == "/redir-start":
            print("[REDIR-START]", case, "POST", len(data), flush=True)
            self.send_bytes(
                status=REDIRECT_CODES[case],
                headers=[("Location", f"/redir-target?case={case}")],
            )
        else:
            print("[REDIR-TARGET]", case, "POST", len(data), flush=True)
            self.redirect_target(args, "POST")

    def report_post(self) -> None:
        if self.headers.get_content_type() != "application/json":
            self.send_error(415, "Content-Type application/json required")
            return
        raw = self.read_body(MAX_REPORT_BYTES)
        if raw is None:
            return
        try:
            data = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Invalid JSON number: " + value)))
            if not isinstance(data, dict):
                raise ValueError("A JSON object is required")
            validate_report_envelope(data)
            report_id = data.get("reportId")
            if report_id is not None and (not isinstance(report_id, str) or len(report_id) > 80):
                raise ValueError("reportId is invalid")
            session_id = data.get("sessionId")
            if session_id is not None and (not isinstance(session_id, str) or len(session_id) > 100):
                raise ValueError("sessionId is invalid")
            report_id = report_id or uuid.uuid4().hex
            data["reportId"] = report_id
            with REPORT_LOCK:
                existing = REPORT_IDS.get(report_id)
                if existing is None:
                    for candidate in OUT.rglob("*.json"):
                        try:
                            if json.loads(candidate.read_text(encoding="utf-8")).get("reportId") == report_id:
                                existing = candidate
                                REPORT_IDS[report_id] = candidate
                                break
                        except (OSError, ValueError, AttributeError):
                            continue
                if existing and existing.exists():
                    existing_report = json.loads(existing.read_text(encoding="utf-8"))
                    ack = {"accepted": True, "duplicate": True, "reportId": report_id,
                           "sessionId": existing_report.get("sessionId", "legacy-" + report_id),
                           "receivedAt": existing_report.get("receivedAt"), "file": existing.name,
                           "buildId": existing_report.get("buildId"),
                           "gitCommit": existing_report.get("gitCommit"),
                           "dirty": existing_report.get("dirty"),
                           "servedScriptsSha256": existing_report.get("servedScriptsSha256", {}),
                           "servedResourcesSha256": existing_report.get("servedResourcesSha256", {}),
                           "servedPageSha256": existing_report.get("servedPageSha256"),
                           "serverSha256": existing_report.get("serverSha256"),
                           "bridgeServiceSha256": existing_report.get("bridgeServiceSha256"),
                           "bridgeRuntimeSha256": existing_report.get("bridgeRuntimeSha256"),
                           "reportSchemaSha256": existing_report.get("reportSchemaSha256")}
                    self.send_json(200, ack)
                    return
                path = save_report(data, self.client_address[0])
                REPORT_IDS[report_id] = path
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.send_json(201, {"accepted": True, "duplicate": False, "reportId": report_id,
                                 "sessionId": stored["sessionId"], "receivedAt": stored["receivedAt"],
                                 "file": path.name, "buildId": stored["buildId"],
                                 "gitCommit": stored["gitCommit"], "dirty": stored["dirty"],
                                 "servedScriptsSha256": stored["servedScriptsSha256"],
                                 "servedResourcesSha256": stored.get("servedResourcesSha256", {}),
                                 "servedPageSha256": stored.get("servedPageSha256"),
                                 "serverSha256": stored.get("serverSha256"),
                                 "bridgeServiceSha256": stored.get("bridgeServiceSha256"),
                                 "bridgeRuntimeSha256": stored.get("bridgeRuntimeSha256"),
                                 "reportSchemaSha256": stored.get("reportSchemaSha256")})
        except (ValueError, UnicodeDecodeError, OSError) as error:
            print("[REPORT ERROR]", repr(error), flush=True)
            self.send_error(400, "Invalid report")
            return
    def send_json(self, status: int, value: dict) -> None:
        self.send_bytes(json.dumps(value, ensure_ascii=False).encode("utf-8"), status=status,
                        mime="application/json; charset=utf-8")

    def summary_get(self) -> None:
        try:
            from analyze_runs import build_summary
            self.send_json(200, build_summary(OUT))
        except (OSError, ValueError) as error:
            print("[SUMMARY ERROR]", repr(error), flush=True)
            self.send_error(500, "Report analysis unavailable")


class BridgeHTTPServer(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True


def _stop_on_sigterm(server, signum, frame):
    # shutdown() must run outside serve_forever's thread.
    threading.Thread(target=server.shutdown, name="http-shutdown", daemon=True).start()


def main() -> int:
    print(f"[READY] NS2 API Probe: {HOST}:{PORT}", flush=True)
    print("[OUTPUT]", OUT, flush=True)
    try:
        lock_file = acquire_instance_lock()
    except (OSError, RuntimeError) as error:
        print("[START ERROR]", error, file=sys.stderr, flush=True)
        return 1
    runtime = get_bridge_runtime()
    print("[BRIDGE BACKEND]", runtime.backend_id, flush=True)
    try:
        try:
            server = BridgeHTTPServer((HOST, PORT), Handler)
        except OSError as error:
            print(f"[BIND ERROR] {HOST}:{PORT}: {error}", file=sys.stderr, flush=True)
            return 1
        previous_sigterm = signal.signal(signal.SIGTERM,
                                         lambda signum, frame: _stop_on_sigterm(server, signum, frame))
        with server:
            server.serve_forever()
            print("\n[STOP] Server stopped", flush=True)
    finally:
        if "previous_sigterm" in locals():
            signal.signal(signal.SIGTERM, previous_sigterm)
        runtime.close()
        lock_file.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
