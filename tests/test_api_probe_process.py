import json
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
OPENER = build_opener(ProxyHandler({}))


class ApiProbeProcessTests(unittest.TestCase):
    def test_http_to_native_c_library_and_mock_backend_lifecycle(self):
        if not shutil.which("cmake") or not shutil.which("cc"):
            self.skipTest("CMake and a C compiler are required for the ctypes integration test")
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            build = temp / "cmake-build"
            subprocess.run(["cmake", "-S", str(ROOT / "bridge"), "-B", str(build),
                            "-DW2JB_BUILD_TESTS=OFF"], check=True, capture_output=True, text=True, timeout=20)
            subprocess.run(["cmake", "--build", str(build), "--target", "webkit2jb_bridge_shared", "--parallel", "2"],
                           check=True, capture_output=True, text=True, timeout=30)
            library = build / "libwebkit2jb_bridge.so"
            self.assertTrue(library.is_file())

            def launch(backend, mock_failure=False, default_runtime=False):
                reservation = socket.socket()
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
                reservation.close()
                env = os.environ.copy()
                env.update({
                    "NS2_HOST": "127.0.0.1", "NS2_PORT": str(port),
                    "NS2_OUT": str(temp / (backend + "-reports")),
                    "NS2_LOCK_PATH": str(temp / (backend + ".lock")),
                    "NS2_BRIDGE_BACKEND": backend, "NS2_BRIDGE_LIBRARY": str(library),
                    "NS2_BRIDGE_MOCK_FAIL": "1" if mock_failure else "0",
                    "PYTHONUNBUFFERED": "1",
                })
                if default_runtime:
                    env.pop("NS2_BRIDGE_BACKEND", None)
                    env.pop("NS2_BRIDGE_LIBRARY", None)
                process = subprocess.Popen([sys.executable, str(ROOT / "api-probe.py")], cwd=str(ROOT),
                                           env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                base = "http://127.0.0.1:%d" % port
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        self.fail("native bridge server exited: " + (process.stdout.read() or ""))
                    try:
                        with OPENER.open(base + "/api/bridge", timeout=0.3) as response:
                            return process, base, json.loads(response.read())
                    except (OSError, URLError):
                        time.sleep(0.05)
                process.terminate()
                process.wait(timeout=5)
                self.fail("native bridge server did not become ready")

            process, base, hello = launch("linux-native")
            try:
                self.assertEqual(hello["backend"], "linux-native")
                self.assertTrue(hello["result"]["nativeLibraryLoaded"])
                self.assertEqual(hello["result"]["architecture"], hello["execution"]["architecture"])
                self.assertTrue(hello["execution"]["architecture"])
                self.assertEqual(hello["execution"]["origin"], "ctypes-loaded-library")
                self.assertEqual(hello["execution"]["mode"], "native-library")
                self.assertFalse(hello["execution"]["switchNativeExecution"])
                self.assertEqual(hello["result"]["cBackend"], "linux-local")

                self.assertTrue(shutil.which("node"), "Node.js is required for the real client-to-C loopback test")
                client_script = r'''var fs=require('fs'),vm=require('vm'),http=require('http');
var port=Number(process.argv[1]),box={Date:Date,Math:Math,JSON:JSON,Object:Object};box.window=box;
box.XMLHttpRequest=function(){this.headers={};};
box.XMLHttpRequest.prototype.open=function(method,path){this.method=method;this.path=path;};
box.XMLHttpRequest.prototype.setRequestHeader=function(key,value){this.headers[key]=value;};
box.XMLHttpRequest.prototype.send=function(body){var self=this,req=http.request({host:'127.0.0.1',port:port,path:this.path,method:this.method,headers:this.headers},function(res){var chunks=[];self.status=res.statusCode;res.on('data',function(chunk){chunks.push(chunk);});res.on('end',function(){self.responseText=Buffer.concat(chunks).toString('utf8');self.onload();});});
req.setTimeout(this.timeout,function(){req.destroy();if(self.ontimeout)self.ontimeout();});req.on('error',function(){if(self.onerror)self.onerror();});req.end(body||undefined);};
vm.runInNewContext(fs.readFileSync('bridge-client.js','utf8'),box);
function fail(error){process.stderr.write(String(error&&error.code||error)+'\n');process.exit(1);}
box.NS2BridgeClient.handshake(function(error,hello){if(error)return fail(error);if(hello.backend!=='linux-native'||hello.execution.origin!=='ctypes-loaded-library'||hello.execution.switchNativeExecution!==false)return fail('wrong handshake');
box.NS2BridgeClient.request('diagnostic',{},function(diagError,diag){if(diagError)return fail(diagError);if(!diag.result.message||diag.backend!=='linux-native')return fail('diagnostic did not return C result');
box.NS2BridgeClient.request('echo',{message:'client-js-to-c'},function(echoError,echo){if(echoError)return fail(echoError);if(echo.result.message!=='client-js-to-c')return fail('echo mismatch');
box.NS2BridgeClient.request('ns2jb-compatibility',{},function(compatError,compat){if(compatError)return fail(compatError);
if(compat.result.status!=='CAPABILITY_UNAVAILABLE'||compat.result.capabilityFlags!==0||compat.result.privilegedOperationsAvailable!==false)return fail('NS2JB availability was overstated');
box.NS2BridgeClient.request('memory-policy',{},function(policyError,policy){if(policyError)return fail(policyError);
if(policy.result.overall!=='PASS'||policy.result.backend!=='linux-local'||policy.result.simulated!==false||policy.result.regions.length!==5)return fail('memory-policy was not returned by native C');
if(policy.result.regions.some(function(region){return region.observed==='rwx';}))return fail('RWX mapping reported');
process.stdout.write('client JS -> HTTP -> C adapter: PASS\n');process.exit(0);});});});});});'''
                client_port = base.rsplit(":", 1)[1]
                client_result = subprocess.run(["node", "-e", client_script, client_port], cwd=str(ROOT),
                                               capture_output=True, text=True, timeout=6)
                self.assertEqual(client_result.returncode, 0, client_result.stderr)
                self.assertIn("client JS -> HTTP -> C adapter: PASS", client_result.stdout)

                wx_request = {"protocol": "webkit2jb-bridge/1", "requestId": "native-wx-004",
                              "operation": "memory-policy", "backend": "linux-native", "payload": {}}
                request = Request(base + "/api/bridge", data=json.dumps(wx_request).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with OPENER.open(request, timeout=2) as response:
                    wx_reply = json.loads(response.read())
                self.assertTrue(wx_reply["ok"])
                self.assertEqual(wx_reply["requestId"], wx_request["requestId"])
                self.assertEqual(wx_reply["result"]["overall"], "PASS")
                self.assertEqual(wx_reply["result"]["writableExecutableRegions"], 0)

                diagnostic = {"protocol": "webkit2jb-bridge/1", "requestId": "native-diag-001",
                              "operation": "diagnostic", "backend": "linux-native", "payload": {}}
                request = Request(base + "/api/bridge", data=json.dumps(diagnostic).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with OPENER.open(request, timeout=2) as response:
                    reply = json.loads(response.read())
                self.assertTrue(reply["ok"])
                self.assertEqual(reply["backend"], "linux-native")
                self.assertEqual(reply["requestId"], diagnostic["requestId"])
                self.assertIn("RWX denied", reply["result"]["message"])

                echo = dict(diagnostic, requestId="native-echo-002", operation="echo",
                            payload={"message": "hello from HTTP"})
                request = Request(base + "/api/bridge", data=json.dumps(echo).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with OPENER.open(request, timeout=2) as response:
                    echo_reply = json.loads(response.read())
                self.assertEqual(echo_reply["requestId"], echo["requestId"])
                self.assertEqual(echo_reply["result"]["message"], "hello from HTTP")
            finally:
                process.terminate()
                self.assertEqual(process.wait(timeout=5), 0)
                if process.stdout:
                    process.stdout.close()

            process, base, hello = launch("linux-native", default_runtime=True)
            try:
                self.assertEqual(hello["backend"], "linux-native")
                self.assertTrue(hello["result"]["nativeLibraryLoaded"])
                self.assertEqual(hello["execution"]["origin"], "ctypes-loaded-library")
            finally:
                process.terminate()
                self.assertEqual(process.wait(timeout=5), 0)
                if process.stdout:
                    process.stdout.close()

            process, base, hello = launch("linux-mock", mock_failure=True)
            try:
                self.assertEqual(hello["backend"], "linux-mock")
                diagnostic = {"protocol": "webkit2jb-bridge/1", "requestId": "mock-fail-003",
                              "operation": "diagnostic", "backend": "linux-mock", "payload": {}}
                request = Request(base + "/api/bridge", data=json.dumps(diagnostic).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(HTTPError) as error:
                    OPENER.open(request, timeout=2)
                self.assertEqual(error.exception.code, 502)
                failed = json.loads(error.exception.read())
                self.assertEqual(failed["requestId"], diagnostic["requestId"])
                self.assertEqual(failed["backend"], "linux-mock")
                self.assertEqual(failed["error"]["code"], "BACKEND_FAILURE")
                error.exception.close()
            finally:
                process.terminate()
                self.assertEqual(process.wait(timeout=5), 0)
                if process.stdout:
                    process.stdout.close()

    def test_real_server_routes_headers_report_and_single_instance_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            reservation = socket.socket()
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
            reservation.close()
            env = os.environ.copy()
            env.update({
                "NS2_HOST": "127.0.0.1",
                "NS2_PORT": str(port),
                "NS2_OUT": str(temp / "reports"),
                "NS2_LOCK_PATH": str(temp / "api-probe.lock"),
                "NS2_BRIDGE_BACKEND": "pc-simulated",
                "PYTHONUNBUFFERED": "1",
            })
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "api-probe.py")],
                cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True,
            )
            base = "http://127.0.0.1:%d" % port
            try:
                deadline = time.monotonic() + 8
                response = None
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        self.fail("api-probe.py exited: " + (process.stdout.read() or ""))
                    try:
                        response = OPENER.open(base + "/", timeout=0.3)
                        break
                    except (OSError, URLError):
                        time.sleep(0.05)
                self.assertIsNotNone(response, "api-probe.py did not accept HTTP connections")
                with response:
                    home = response.read()
                    self.assertEqual(response.status, 200)
                    get_length = int(response.headers["Content-Length"])
                    self.assertEqual(get_length, len(home))
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    csp = response.headers["Content-Security-Policy"]
                    self.assertIn("script-src 'self'", csp)
                    self.assertIn("connect-src 'self'", csp)
                    self.assertIn(b'data-diagnostic="api"', home)
                    self.assertIn(b'data-diagnostic="font-load"', home)
                    self.assertIn(b'data-diagnostic="reentrancy"', home)

                with OPENER.open(Request(base + "/", method="HEAD"), timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b"")
                    self.assertEqual(int(response.headers["Content-Length"]), get_length)
                for route in ("/portal.js", "/diagnostics.js", "/bridge-client.js", "/shared/capabilities.js", "/shared/reporting.js", "/fonts/ns2-test-font.ttf", "/schemas/ns2-diagnostic-envelope-v1.schema.json", "/bridge/protocol/bridge-v1.schema.json"):
                    with OPENER.open(base + route, timeout=2) as response:
                        body = response.read()
                        self.assertEqual(response.status, 200)
                        self.assertGreater(int(response.headers["Content-Length"]), 0)
                        self.assertEqual(len(body), int(response.headers["Content-Length"]))

                with OPENER.open(base + "/api/bridge", timeout=2) as response:
                    handshake = json.loads(response.read())
                    self.assertEqual(response.status, 200)
                    self.assertEqual(handshake["protocol"], "webkit2jb-bridge/1")
                    self.assertEqual(handshake["backend"], "pc-simulated")
                    self.assertTrue(handshake["execution"]["mode"] == "simulated")
                    self.assertFalse(handshake["result"]["nativeProcessConnected"])
                    self.assertFalse(handshake["result"]["switchNativeExecution"])
                bridge_request = {"protocol": "webkit2jb-bridge/1", "requestId": "http-001",
                                  "operation": "diagnostic", "backend": "pc-simulated", "payload": {}}
                request = Request(base + "/api/bridge", data=json.dumps(bridge_request).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with OPENER.open(request, timeout=2) as response:
                    bridge_reply = json.loads(response.read())
                    self.assertEqual(bridge_reply["requestId"], "http-001")
                    self.assertTrue(bridge_reply["ok"])
                    self.assertEqual(bridge_reply["result"]["performed"], True)
                    self.assertFalse(bridge_reply["execution"]["switchNativeExecution"])
                malformed = dict(bridge_request, backend="horizon-homebrew")
                request = Request(base + "/api/bridge", data=json.dumps(malformed).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(HTTPError) as error:
                    OPENER.open(request, timeout=2)
                self.assertEqual(error.exception.code, 409)
                mismatch = json.loads(error.exception.read())
                self.assertEqual(mismatch["error"]["code"], "BACKEND_MISMATCH")
                error.exception.close()
                oversized = dict(bridge_request, operation="echo", payload={"message": "x" * 257})
                request = Request(base + "/api/bridge", data=json.dumps(oversized).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(HTTPError) as error:
                    OPENER.open(request, timeout=2)
                self.assertEqual(error.exception.code, 413)
                self.assertEqual(json.loads(error.exception.read())["error"]["code"], "MESSAGE_TOO_LARGE")
                error.exception.close()

                payload = {
                    "schema": "ns2-api-probe-process-test-v1",
                    "reportId": "process-report-1",
                    "sessionId": "process-session-1",
                    "result": "host-http-observed",
                }
                body = json.dumps(payload).encode("utf-8")
                request = Request(
                    base + "/api/report", data=body,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with OPENER.open(request, timeout=2) as response:
                    ack = json.loads(response.read())
                    self.assertEqual(response.status, 201)
                    self.assertTrue(ack["accepted"])
                    self.assertTrue(ack["buildId"].startswith("ns2-"))
                    self.assertEqual(ack["servedScriptsSha256"], {
                        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in ("diagnostics.js", "portal.js", "bridge-client.js", "shared/capabilities.js", "shared/reporting.js")
                    })
                    self.assertEqual(ack["servedResourcesSha256"], {
                        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in ("fonts/ns2-test-font.ttf", "schemas/ns2-diagnostic-envelope-v1.schema.json", "bridge/protocol/bridge-v1.schema.json")
                    })
                stored_path = next((temp / "reports").glob("api-probe-*.json"))
                stored = json.loads(stored_path.read_text(encoding="utf-8"))
                self.assertEqual(len(stored["gitCommit"]), 40)
                self.assertIs(type(stored["dirty"]), bool)
                self.assertEqual(len(stored["serverSha256"]), 64)
                self.assertEqual(len(stored["servedPageSha256"]), 64)
                self.assertEqual(stored["servedScriptsSha256"], ack["servedScriptsSha256"])
                self.assertEqual(stored["servedResourcesSha256"], ack["servedResourcesSha256"])
                self.assertEqual(len(stored["reportSchemaSha256"]), 64)
                self.assertEqual(len(stored["bridgeServiceSha256"]), 64)
                self.assertEqual(len(stored["bridgeRuntimeSha256"]), 64)
                self.assertEqual(stored["buildId"], ack["buildId"])
                with OPENER.open(base + "/api/summary", timeout=2) as response:
                    summary = json.loads(response.read())
                    self.assertEqual(response.status, 200)
                    self.assertEqual(summary["schema"], "ns2-lab-summary-v1")
                    self.assertGreaterEqual(summary["reportCount"], 1)

                second = subprocess.run(
                    [sys.executable, str(ROOT / "api-probe.py")],
                    cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=5,
                )
                self.assertNotEqual(second.returncode, 0)
                self.assertIn("already holds", second.stderr)

                for route in ("/diagnostics", "/fontface-safe.html", "/fontface-custom.js", "/probes.js"):
                    with self.assertRaises(HTTPError) as error:
                        OPENER.open(base + route, timeout=2)
                    self.assertEqual(error.exception.code, 404)
                    error.exception.close()
            finally:
                process.terminate()
                process.wait(timeout=5)
                if process.stdout:
                    process.stdout.close()


if __name__ == "__main__":
    unittest.main()
