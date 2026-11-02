import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from email.message import Message


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("api_probe_compat", ROOT / "api-probe.py")
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class PortalCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        api.OUT = Path(self.temp.name)
        api.REPORT_IDS.clear()

    def tearDown(self):
        self.temp.cleanup()

    def handler(self, path="/", method="GET", body=b"", headers=None):
        handler = object.__new__(api.Handler)
        handler.path = path
        handler.command = method
        handler.client_address = ("127.0.0.1", 43210)
        handler.headers = Message()
        for key, value in (headers or {}).items():
            handler.headers[key] = value
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.response_status = None
        handler.response_headers = {}
        handler.send_response = lambda status: setattr(handler, "response_status", status)
        handler.send_header = lambda key, value: handler.response_headers.__setitem__(key, value)
        handler.end_headers = lambda: None
        handler.send_error = lambda status, message="": setattr(handler, "response_status", status)
        return handler

    @staticmethod
    def dns_config(path):
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        active = [line.strip() for line in lines
                  if line.strip() and not line.lstrip().startswith("#")]
        bindings = {line.split("=", 1)[0]: line.split("=", 1)[1]
                    for line in active if "=" in line and not line.startswith("address=")}
        records = {}
        for line in active:
            if line.startswith("address=/"):
                _, host, address = line.split("/", 2)
                records[host] = address
        return active, bindings, records


    def test_root_does_not_redirect_and_redirect_probe_is_explicit(self):
        root = self.handler(headers={"Host": "ctest.p01.ctest.srv.nintendo.net"})
        root.do_GET()
        self.assertEqual(root.response_status, 200)
        self.assertNotIn("Location", root.response_headers)

        redirect = self.handler(
            path="/redir-start?case=post302",
            method="POST",
            body=b"probe",
            headers={"Content-Length": "5"},
        )
        redirect.do_POST()
        self.assertEqual(redirect.response_status, 302)
        self.assertEqual(redirect.response_headers["Location"], "/redir-target?case=post302")
        self.assertIn("no-store", redirect.response_headers["Cache-Control"])

    def test_main_portal_routes_and_csp(self):
        root = self.handler()
        root.do_GET()
        self.assertEqual(root.response_status, 200)
        self.assertIn("default-src 'self'", root.response_headers["Content-Security-Policy"])
        self.assertIn("script-src 'self'", root.response_headers["Content-Security-Policy"])
        self.assertIn("connect-src 'self'", root.response_headers["Content-Security-Policy"])
        self.assertEqual(root.response_headers["Cache-Control"], "no-store")
        self.assertEqual(int(root.response_headers["Content-Length"]), len(root.wfile.getvalue()))
        self.assertEqual(root.response_headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(root.response_headers["Referrer-Policy"], "no-referrer")

        for route, mime in (
            ("/portal.js", "application/javascript; charset=utf-8"),
            ("/diagnostics.js", "application/javascript; charset=utf-8"),
            ("/shared/capabilities.js", "application/javascript; charset=utf-8"),
            ("/shared/reporting.js", "application/javascript; charset=utf-8"),
            ("/bridge-client.js", "application/javascript; charset=utf-8"),
            ("/schemas/ns2-diagnostic-envelope-v1.schema.json", "application/schema+json; charset=utf-8"),
            ("/bridge/protocol/bridge-v1.schema.json", "application/schema+json; charset=utf-8"),
            ("/fonts/ns2-test-font.ttf", "font/ttf"),
        ):
            response = self.handler(path=route)
            response.do_GET()
            self.assertEqual(response.response_status, 200)
            self.assertEqual(response.response_headers["Content-Type"], mime)
            self.assertEqual(response.response_headers["Cache-Control"], "no-store")

        head = self.handler(method="HEAD")
        head.do_HEAD()
        self.assertEqual(head.response_status, 200)
        self.assertEqual(head.wfile.getvalue(), b"")
        self.assertEqual(head.response_headers["Content-Length"], root.response_headers["Content-Length"])

    def test_legacy_diagnostic_and_crash_routes_are_not_served(self):
        for route in (
            "/diagnostics",
            "/fontface-safe",
            "/fontface-safe.html",
            "/fontface-survey",
            "/fontface-survey.js",
            "/fontface-custom.js",
            "/probes.js",
            "/scenario.html",
        ):
            with self.subTest(route=route):
                response = self.handler(path=route)
                response.do_GET()
                self.assertEqual(response.response_status, 404)

    def test_instance_lock_rejects_a_second_same_bind_instance(self):
        lock_path = Path(self.temp.name) / "portal.lock"
        first = api.acquire_instance_lock(lock_path)
        try:
            with self.assertRaisesRegex(RuntimeError, "already holds"):
                api.acquire_instance_lock(lock_path)
        finally:
            first.close()
        second = api.acquire_instance_lock(lock_path)
        second.close()

    def test_home_exposes_manual_safe_diagnostics_only(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        portal = (ROOT / "portal.js").read_text(encoding="utf-8")
        diagnostics = (ROOT / "diagnostics.js").read_text(encoding="utf-8")
        for diagnostic in ("api", "font-load", "reentrancy"):
            self.assertIn('data-diagnostic="%s"' % diagnostic, html)
        self.assertIn('id="bridge-ns2jb-compatibility"', html)
        self.assertIn('id="bridge-memory-policy"', html)
        self.assertIn("api:", diagnostics)
        self.assertIn("'font-load':", diagnostics)
        self.assertIn("reentrancy:", diagnostics)
        self.assertIn('id="diagnostic-view" hidden', html)
        self.assertIn("No diagnostic has run", portal)
        self.assertEqual(portal.count("NS2Diagnostics.run("), 1)
        self.assertIn("runButton.addEventListener('click'", portal)
        self.assertIn('src="/shared/capabilities.js"', html)
        self.assertIn('src="/shared/reporting.js"', html)
        self.assertIn('src="/bridge-client.js"', html)
        self.assertIn('id="bridge-status"', html)
        portal_js = (ROOT / "portal.js").read_text(encoding="utf-8")
        self.assertIn("pcRunnerArtifact", portal_js)
        self.assertIn("PC ELF validated (x86-64, not executed)", portal_js)
        self.assertIn('src="/diagnostics.js"', html)
        self.assertIn('src="/portal.js"', html)

    def test_report_ack_and_summary_remain_json(self):
        payload = {
            "schema": "ns2-portal-compatibility-test-v1",
            "reportId": "portal-compat-report",
            "sessionId": "portal-compat-session",
            "result": "host-http-observed",
        }
        body = json.dumps(payload).encode("utf-8")
        report = self.handler(
            path="/api/report",
            method="POST",
            body=body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
        )
        report.do_POST()
        ack = json.loads(report.wfile.getvalue())
        self.assertEqual(report.response_status, 201)
        self.assertEqual(report.response_headers["Content-Type"].split(";")[0], "application/json")
        self.assertTrue(ack["accepted"])
        self.assertEqual(ack["reportId"], payload["reportId"])
        saved_files = list(Path(self.temp.name).rglob("*.json"))
        self.assertEqual(len(saved_files), 1)
        saved = json.loads(saved_files[0].read_text(encoding="utf-8"))
        self.assertEqual(saved["reportId"], payload["reportId"])
        self.assertIn("receivedAt", saved)

        retry = self.handler(
            path="/api/report",
            method="POST",
            body=body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
        )
        retry.do_POST()
        duplicate_ack = json.loads(retry.wfile.getvalue())
        self.assertEqual(retry.response_status, 200)
        self.assertTrue(duplicate_ack["accepted"])
        self.assertTrue(duplicate_ack["duplicate"])
        self.assertEqual(len(list(Path(self.temp.name).rglob("*.json"))), 1)

        summary_handler = self.handler(path="/api/summary")
        summary_handler.do_GET()
        summary = json.loads(summary_handler.wfile.getvalue())
        self.assertEqual(summary_handler.response_status, 200)
        self.assertEqual(summary["schema"], "ns2-lab-summary-v1")
        self.assertGreaterEqual(summary["reportCount"], 1)




if __name__ == "__main__":
    unittest.main()
