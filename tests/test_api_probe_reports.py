import importlib.util
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("api_probe", ROOT / "api-probe.py")
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class ReportServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        api.OUT = Path(cls.temp.name)
        api.REPORT_IDS.clear()
        with api.SERVED_ASSETS_LOCK:
            api.SERVED_ASSETS_BY_CLIENT.clear()
        cls.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def post(self, body, content_type="application/json"):
        request = Request(self.base + "/api/report", data=body,
                          headers={"Content-Type": content_type}, method="POST")
        with urlopen(request) as response:
            return response.status, json.loads(response.read())

    def test_ack_atomic_report_and_idempotent_retry(self):
        for route in ("/", "/diagnostics.js", "/portal.js", "/bridge-client.js", "/shared/capabilities.js", "/shared/reporting.js", "/fonts/ns2-test-font.ttf", "/schemas/ns2-diagnostic-envelope-v1.schema.json", "/bridge/protocol/bridge-v1.schema.json"):
            with urlopen(self.base + route) as response:
                response.read()
        payload = {"schema": "ns2-fontface-survey-safe-v2", "schemaVersion": 2,
                   "reportId": "test-report-1", "sessionId": "test-session-1",
                   "timestamp": "2026-10-31T12:00:00Z", "events": [{"name": "resolved"}]}
        status, ack = self.post(json.dumps(payload).encode())
        self.assertEqual(status, 201)
        self.assertTrue(ack["accepted"])
        self.assertEqual(ack["reportId"], payload["reportId"])
        self.assertEqual(ack["sessionId"], payload["sessionId"])
        report_file = next(api.OUT.rglob("*.json"))
        saved = json.loads(report_file.read_text())
        self.assertEqual(saved["receivedAt"], ack["receivedAt"])
        self.assertEqual(saved["clientIP"], "127.0.0.1")
        expected_scripts = {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("diagnostics.js", "portal.js", "bridge-client.js", "shared/capabilities.js", "shared/reporting.js")
        }
        self.assertEqual(saved["servedScriptsSha256"], expected_scripts)
        self.assertEqual(saved["servedResourcesSha256"], {
            "fonts/ns2-test-font.ttf": hashlib.sha256((ROOT / "fonts/ns2-test-font.ttf").read_bytes()).hexdigest(),
            "schemas/ns2-diagnostic-envelope-v1.schema.json": hashlib.sha256((ROOT / "schemas/ns2-diagnostic-envelope-v1.schema.json").read_bytes()).hexdigest(),
            "bridge/protocol/bridge-v1.schema.json": hashlib.sha256((ROOT / "bridge/protocol/bridge-v1.schema.json").read_bytes()).hexdigest(),
        })
        self.assertEqual(saved["reportSchemaSha256"], hashlib.sha256((ROOT / "schemas/ns2-diagnostic-envelope-v1.schema.json").read_bytes()).hexdigest())
        self.assertEqual(saved["bridgeServiceSha256"], hashlib.sha256((ROOT / "bridge/http_service.py").read_bytes()).hexdigest())
        self.assertEqual(saved["bridgeRuntimeSha256"], hashlib.sha256((ROOT / "bridge/python/runtime.py").read_bytes()).hexdigest())
        self.assertEqual(saved["gitCommit"], ack["gitCommit"])
        self.assertEqual(saved["buildId"], ack["buildId"])
        self.assertEqual(saved["comparison"]["baseline"], "none")
        status, retry = self.post(json.dumps(payload).encode())
        self.assertEqual(status, 200)
        self.assertTrue(retry["duplicate"])
        self.assertEqual(retry["buildId"], saved["buildId"])
        self.assertEqual(retry["servedScriptsSha256"], expected_scripts)
        self.assertEqual(retry["servedResourcesSha256"], saved["servedResourcesSha256"])
        self.assertEqual(len(list(api.OUT.rglob("*.json"))), 1)
        second = dict(payload, reportId="test-report-2", sessionId="test-session-2",
                      events=[{"name": "timeout"}])
        self.post(json.dumps(second).encode())
        stored = [json.loads(path.read_text()) for path in api.OUT.rglob("*.json")]
        changed = next(item for item in stored if item["reportId"] == "test-report-2")
        self.assertEqual(changed["comparison"]["baseline"], report_file.name)
        self.assertTrue(changed["comparison"]["changes"])

    def test_rejects_bad_json_non_json_and_nonfinite_numbers(self):
        with self.assertRaises(HTTPError) as error:
            self.post(b"{broken")
        self.assertEqual(error.exception.code, 400)
        error.exception.close()
        with self.assertRaises(HTTPError) as error:
            self.post(b"{}", "text/plain")
        self.assertEqual(error.exception.code, 415)
        error.exception.close()
        with self.assertRaises(HTTPError) as error:
            self.post(b'{"schema":"x","v":NaN}')
        self.assertEqual(error.exception.code, 400)
        error.exception.close()

    def test_summary_and_retired_unsafe_page_route(self):
        with urlopen(self.base + "/api/summary") as response:
            summary = json.loads(response.read())
        self.assertEqual(summary["schema"], "ns2-lab-summary-v1")
        self.assertGreaterEqual(summary["reportCount"], 1)
        for route in ("/diagnostics", "/diagnostics?test=api", "/fontface-safe", "/fontface-safe.html", "/fontface-survey", "/fontface-survey.js", "/fontface-custom.js", "/probes.js"):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base + route)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()

    def test_main_portal_contains_three_manual_in_page_diagnostics(self):
        with urlopen(self.base + "/") as response:
            html = response.read().decode("utf-8")
            get_length = int(response.headers["Content-Length"])
            self.assertEqual(response.headers["Content-Type"], "text/html; charset=utf-8")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
            csp = response.headers["Content-Security-Policy"]
            self.assertIn("script-src 'self'", csp)
            self.assertIn("connect-src 'self'", csp)
        request = Request(self.base + "/", method="HEAD")
        with urlopen(request) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"")
            self.assertEqual(int(response.headers["Content-Length"]), get_length)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("WebKit2JB — Switch 2 Research Lab", html)
        self.assertIn('id="home-view"', html)
        self.assertIn('id="diagnostic-view" hidden', html)
        for test_id in ("api", "font-load", "reentrancy"):
            self.assertIn('data-diagnostic="%s"' % test_id, html)
        self.assertNotIn('href="/diagnostics?', html)
        self.assertIn('src="/shared/capabilities.js"', html)
        self.assertIn('src="/shared/reporting.js"', html)
        self.assertIn('src="/bridge-client.js"', html)
        self.assertIn('id="bridge-status"', html)
        self.assertIn('src="/diagnostics.js"', html)
        self.assertIn('src="/portal.js"', html)
        with urlopen(self.base + "/diagnostics.js") as response:
            diagnostics_js = response.read().decode("utf-8")
        self.assertIn("global.NS2Diagnostics = {get: get, run: run}", diagnostics_js)
        self.assertNotIn("location.search", diagnostics_js)
        with urlopen(self.base + "/portal.js") as response:
            portal_js = response.read().decode("utf-8")
        self.assertIn("runButton.addEventListener('click'", portal_js)
        for route, mime in (("/shared/capabilities.js", "application/javascript; charset=utf-8"),
                            ("/shared/reporting.js", "application/javascript; charset=utf-8"),
                            ("/bridge-client.js", "application/javascript; charset=utf-8"),
                            ("/schemas/ns2-diagnostic-envelope-v1.schema.json", "application/schema+json; charset=utf-8"),
                            ("/bridge/protocol/bridge-v1.schema.json", "application/schema+json; charset=utf-8")):
            with urlopen(self.base + route) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Content-Type"], mime)

    def test_pc_runner_artifact_bridge_route_is_metadata_only(self):
        with urlopen(self.base + "/api/bridge/pc-runner-artifact") as response:
            self.assertEqual(response.status, 200)
            evidence = json.loads(response.read())
        self.assertEqual(evidence["status"], "PC_ARTIFACT_VALIDATED")
        self.assertEqual(evidence["architecture"], "x86_64")
        self.assertFalse(evidence["executionConfirmed"])
        self.assertFalse(evidence["horizonCompatible"])

    def test_versioned_json_schema_is_enforced_and_legacy_reports_remain_accepted(self):
        schema = json.loads((ROOT / "schemas/ns2-diagnostic-envelope-v1.schema.json").read_text(encoding="utf-8"))
        self.assertIn("reportEnvelopeVersion", schema["required"])
        valid = {
            "reportEnvelopeVersion": 1, "schema": "ns2-webkit-api-probe-1", "schemaVersion": 2,
            "reportId": "envelope-report", "sessionId": "envelope-session",
            "startedAt": "2026-11-01T12:00:00.000Z", "testId": "api", "testVersion": "1.0.0",
            "capabilities": {"schema": "ns2-capabilities-v1", "features": {}},
            "events": [{"name": "started", "timestamp": "2026-11-01T12:00:00.000Z", "elapsedMs": 0, "info": {}, "state": {}}],
            "errors": [], "result": "completed"
        }
        api.validate_report_envelope(valid)
        malformed = dict(valid, testId="unknown")
        with self.assertRaises(ValueError):
            api.validate_report_envelope(malformed)
        malformed_error = dict(valid, errors=[{"phase": "load"}])
        with self.assertRaises(ValueError):
            api.validate_report_envelope(malformed_error)
        malformed_state = dict(valid, events=[dict(valid["events"][0], state={"documentFontsSize": -1})])
        with self.assertRaises(ValueError):
            api.validate_report_envelope(malformed_state)
        legacy = {"schema": "older-schema", "events": [{"name": "legacy"}]}
        api.validate_report_envelope(legacy)



if __name__ == "__main__":
    unittest.main()
