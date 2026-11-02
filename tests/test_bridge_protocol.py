import json
import importlib.util
import hashlib
import subprocess
import sys
import struct
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _fixture_elf_aarch64():
    data = bytearray(128)
    data[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHIQQQIHHHHHH", data, 16,
                     3, 183, 1, 0, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 120, 0, 0, 8, 8, 8)
    return bytes(data)


def _fixture_nro():
    main_size = 0x80
    nacp = bytearray(0x4000)
    nacp[:len(b"WebKit2JB Bridge Demo")] = b"WebKit2JB Bridge Demo"
    nacp[0x200:0x200 + len(b"WebKit2JB Lab")] = b"WebKit2JB Lab"
    nacp[0x3060:0x3060 + len(b"0.1.0")] = b"0.1.0"
    nro = bytearray(main_size + 0x38 + len(nacp))
    nro[0x10:0x14] = b"NRO0"
    struct.pack_into("<I", nro, 0x18, main_size)
    nro[main_size:main_size + 4] = b"ASET"
    struct.pack_into("<I", nro, main_size + 4, 0)
    struct.pack_into("<QQ", nro, main_size + 24, 0x38, len(nacp))
    nro[main_size + 0x38:] = nacp
    return bytes(nro), bytes(nacp)


class BridgeProtocolTests(unittest.TestCase):
    def node(self, source):
        return subprocess.run(["node", "-e", source], cwd=str(ROOT), capture_output=True, text=True, timeout=10)

    def test_server_request_validation_limits_and_backend_identity(self):
        spec = importlib.util.spec_from_file_location("api_probe_bridge_test", ROOT / "api-probe.py")
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        valid = {"protocol": api.BRIDGE_PROTOCOL, "requestId": "unit-01", "operation": "diagnostic",
                 "backend": "pc-simulated", "payload": {}}
        self.assertEqual(api.validate_bridge_request(valid), valid)
        compatibility = dict(valid, operation="ns2jb-compatibility")
        self.assertEqual(api.validate_bridge_request(compatibility), compatibility)
        status, compatibility_reply = api.process_bridge_request(json.dumps(compatibility).encode())
        self.assertEqual(status, 200)
        self.assertEqual(compatibility_reply["result"]["status"], "CAPABILITY_UNAVAILABLE")
        self.assertFalse(compatibility_reply["result"]["privilegedOperationsAvailable"])
        self.assertTrue(compatibility_reply["result"]["simulated"])
        memory_policy = dict(valid, operation="memory-policy")
        self.assertEqual(api.validate_bridge_request(memory_policy), memory_policy)
        status, memory_reply = api.process_bridge_request(json.dumps(memory_policy).encode())
        self.assertEqual(status, 200)
        self.assertEqual(memory_reply["result"]["overall"], "UNSUPPORTED")
        self.assertEqual(memory_reply["result"]["backend"], "pc-simulated")
        with self.assertRaises(ValueError):
            api.validate_bridge_request(dict(compatibility, payload={"message": "no-op"}))
        for invalid in (
            dict(valid, requestId="bad id"),
            dict(valid, protocol="webkit2jb-bridge/9"),
            dict(valid, operation="execute"),
            dict(valid, backend="horizon-homebrew"),
            dict(valid, backend=["linux-native"]),
            dict(valid, backend={"name": "linux-native"}),
            dict(valid, payload={"unexpected": True}),
        ):
            with self.assertRaises((ValueError, LookupError)):
                api.validate_bridge_request(invalid)
        with self.assertRaises(OverflowError):
            api.validate_bridge_request(dict(valid, operation="echo", payload={"message": "x" * 257}))
        status, reply = api.process_bridge_request(b'{"protocol":"webkit2jb-bridge/1","protocol":"webkit2jb-bridge/1"}')
        self.assertEqual(status, 400)
        self.assertEqual(reply["error"]["code"], "INVALID_REQUEST")

    def test_handshake_backend_failure_remains_versioned_json(self):
        spec = importlib.util.spec_from_file_location("api_probe_bridge_test", ROOT / "api-probe.py")
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)

        class BrokenRuntime:
            backend_id = "linux-native"

            def handshake(self):
                raise RuntimeError("native capability probe failed")

            def execution(self):
                return {"mode": "native-library", "platform": "linux",
                        "origin": "ctypes-loaded-library", "nativeLibraryLoaded": True,
                        "nativeProcessConnected": False, "switchNativeExecution": False}

        status, reply = api.bridge_handshake_response(BrokenRuntime())
        self.assertEqual(status, 502)
        self.assertEqual(reply["protocol"], "webkit2jb-bridge/1")
        self.assertEqual(reply["backend"], "linux-native")
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["code"], "BACKEND_FAILURE")
        self.assertIn("native capability probe failed", reply["error"]["message"])

    def test_missing_native_library_is_unavailable_not_a_simulator_fallback(self):
        from bridge.python.runtime import runtime_from_environment
        with patch.dict("os.environ", {
                "NS2_BRIDGE_BACKEND": "linux-native",
                "NS2_BRIDGE_LIBRARY": str(ROOT / "missing-native-bridge.so")}, clear=False):
            runtime = runtime_from_environment()
        self.assertEqual(runtime.backend_id, "unavailable")
        status, reply = self.bridge_runtime_handshake(runtime)
        self.assertEqual(status, 503)
        self.assertEqual(reply["error"]["code"], "CAPABILITY_UNAVAILABLE")

    @staticmethod
    def bridge_runtime_handshake(runtime):
        spec = importlib.util.spec_from_file_location("api_probe_bridge_test", ROOT / "api-probe.py")
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        return api.bridge_handshake_response(runtime)

    def test_horizon_compile_status_requires_matching_nro_manifest_and_never_claims_execution(self):
        spec = importlib.util.spec_from_file_location("api_probe_bridge_test", ROOT / "api-probe.py")
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        with tempfile.TemporaryDirectory() as temporary:
            build = Path(temporary)
            nro, nacp_data = _fixture_nro()
            elf_data = _fixture_elf_aarch64()
            artifact = build / "w2jb-horizon-demo.nro"
            artifact.write_bytes(nro)
            elf = build / "w2jb-horizon-demo.elf"
            elf.write_bytes(elf_data)
            nacp = build / "w2jb-horizon-demo.nacp"
            nacp.write_bytes(nacp_data)
            manifest = {
                "schema": "webkit2jb-horizon-build/1", "status": "HORIZON_COMPILED",
                "target": "horizon-homebrew", "architecture": "aarch64",
                "artifact": artifact.name, "artifactSize": len(nro),
                "artifactSha256": hashlib.sha256(nro).hexdigest(),
                "elfSha256": hashlib.sha256(elf_data).hexdigest(),
                "nacpSha256": hashlib.sha256(nacp_data).hexdigest(),
                "sourceCommit": "a" * 40, "sourceDirty": False,
                "toolchain": "devkitA64 GCC test", "executionConfirmed": False,
                "title": "WebKit2JB Bridge Demo", "author": "WebKit2JB Lab", "version": "0.1.0",
            }
            manifest_path = build / "build-info.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            evidence = api.horizon_build_evidence(manifest_path)
            self.assertEqual(evidence["status"], "HORIZON_COMPILED")
            self.assertFalse(evidence["executionConfirmed"])
            self.assertEqual(evidence["nacpSha256"], hashlib.sha256(nacp_data).hexdigest())
            self.assertEqual(api.platform_evidence("linux-native")["pc"], "PC_NATIVE")
            self.assertEqual(api.platform_evidence("linux-native")["horizonExecution"]["status"], "UNAVAILABLE")

            artifact.write_bytes(b"altered")
            self.assertEqual(api.horizon_build_evidence(manifest_path)["status"], "UNAVAILABLE")
            artifact.write_bytes(nro)
            elf.write_bytes(b"corrupt")
            self.assertEqual(api.horizon_build_evidence(manifest_path)["status"], "UNAVAILABLE")
            elf.write_bytes(elf_data)
            nacp.write_bytes(b"corrupt")
            self.assertEqual(api.horizon_build_evidence(manifest_path)["status"], "UNAVAILABLE")

    def test_pc_runner_elf_is_integrity_checked_and_never_claimed_as_executed(self):
        spec = importlib.util.spec_from_file_location("api_probe_runner_test", ROOT / "api-probe.py")
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        evidence = api.pc_runner_artifact_evidence()
        self.assertEqual(evidence["status"], "PC_ARTIFACT_VALIDATED")
        self.assertEqual(evidence["architecture"], "x86_64")
        self.assertEqual(evidence["size"], 9248)
        self.assertEqual(evidence["capacity"], 65536)
        self.assertEqual(evidence["sha256"],
                         "543e3c76b417585f8f30bb174d8d7dc276c242aa33b1c7ab028e03bdf97cf54e")
        self.assertFalse(evidence["executionConfirmed"])
        self.assertFalse(evidence["horizonCompatible"])
        self.assertEqual(api.platform_evidence("linux-native")["pcRunnerArtifact"], evidence)

        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            artifact = folder / "pc-runner-example.elf"
            artifact.write_bytes((ROOT / "bridge/resources/pc-runner-example.elf").read_bytes())
            manifest = json.loads((ROOT / "bridge/resources/pc-runner-example.manifest.json").read_text())
            manifest_path = folder / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            self.assertEqual(api.pc_runner_artifact_evidence(manifest_path)["status"],
                             "PC_ARTIFACT_VALIDATED")
            artifact.write_bytes(b"corrupt")
            self.assertEqual(api.pc_runner_artifact_evidence(manifest_path)["status"], "UNAVAILABLE")

    def test_client_handshake_correlates_response_and_labels_simulation(self):
        result = self.node(r'''const fs=require('fs'),vm=require('vm');let requests=[];
const box={Date,Math,JSON,Object};box.window=box;
box.XMLHttpRequest=function(){this.status=200;this.open=(m)=>{this.method=m;};this.setRequestHeader=()=>{};
this.send=(body)=>{requests.push({method:this.method,body});let q;
if(this.method==='GET')q={protocol:'webkit2jb-bridge/1',requestId:'handshake',operation:'handshake',backend:'pc-simulated',ok:true,error:null,result:{backend:'pc-simulated',platform:'pc',architecture:'x86_64',simulated:true,nativeLibraryLoaded:false,nativeProcessConnected:false,switchNativeExecution:false},execution:{mode:'simulated',platform:'pc',architecture:'x86_64',origin:'python-simulator',nativeLibraryLoaded:false,nativeProcessConnected:false,switchNativeExecution:false}};
else {const sent=JSON.parse(body);q={protocol:sent.protocol,requestId:sent.requestId,operation:sent.operation,backend:'pc-simulated',ok:true,error:null,result:{message:'ok'},execution:{mode:'simulated',platform:'pc',architecture:'x86_64',origin:'python-simulator',nativeLibraryLoaded:false,nativeProcessConnected:false,switchNativeExecution:false}};}
this.responseText=JSON.stringify(q);this.onload();};};
vm.runInNewContext(fs.readFileSync('bridge-client.js','utf8'),box);
let handshake=false,diagnostic=false;
box.NS2BridgeClient.handshake((e,r)=>{if(e)process.exit(1);handshake=r.execution.mode==='simulated';});
box.NS2BridgeClient.request('diagnostic',{},(e,r)=>{if(e)process.exit(2);diagnostic=r.requestId.indexOf('browser-')===0;});
if(!handshake||!diagnostic||requests.length!==2)process.exit(3);
console.log(JSON.stringify({handshake,diagnostic,requests:requests.length}));''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"handshake": True, "diagnostic": True, "requests": 2})

    def test_client_rejects_backend_claim_that_conflicts_with_execution(self):
        result = self.node(r'''const fs=require('fs'),vm=require('vm');let posted=0;const box={Date,Math,JSON,Object};box.window=box;
box.XMLHttpRequest=function(){this.status=200;this.open=(m)=>{this.method=m;};this.setRequestHeader=()=>{};this.send=()=>{this.responseText=JSON.stringify({protocol:'webkit2jb-bridge/1',requestId:'handshake',operation:'handshake',backend:'pc-simulated',ok:true,error:null,result:{backend:'pc-simulated',platform:'pc',architecture:'x86_64',simulated:true,nativeLibraryLoaded:false,nativeProcessConnected:true,switchNativeExecution:false},execution:{mode:'simulated',platform:'pc',architecture:'x86_64',origin:'python-simulator',nativeLibraryLoaded:false,nativeProcessConnected:true,switchNativeExecution:false}});this.onload();if(this.method==='POST')posted++;};};
vm.runInNewContext(fs.readFileSync('bridge-client.js','utf8'),box);let error=null;
box.NS2BridgeClient.handshake(e=>error=e&&e.code);
if(error!=='INVALID_BACKEND_IDENTITY'||posted)process.exit(2);
console.log('rejected');''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "rejected")

    def test_client_only_sends_allowlisted_operations(self):
        result = self.node(r'''const fs=require('fs'),vm=require('vm');let posts=0;const box={Date,Math,JSON,Object};box.window=box;
box.XMLHttpRequest=function(){this.status=200;this.open=(m)=>{this.method=m;};this.setRequestHeader=()=>{};this.send=()=>{if(this.method==='POST')posts++;this.responseText=JSON.stringify({protocol:'webkit2jb-bridge/1',requestId:'handshake',operation:'handshake',backend:'pc-simulated',ok:true,error:null,result:{backend:'pc-simulated',platform:'pc',architecture:'x86_64',simulated:true,nativeLibraryLoaded:false,nativeProcessConnected:false,switchNativeExecution:false},execution:{mode:'simulated',platform:'pc',architecture:'x86_64',origin:'python-simulator',nativeLibraryLoaded:false,nativeProcessConnected:false,switchNativeExecution:false}});this.onload();};};
vm.runInNewContext(fs.readFileSync('bridge-client.js','utf8'),box);let code=null;
box.NS2BridgeClient.handshake(e=>code=e&&e.code);if(code)process.exit(1);
box.NS2BridgeClient.request('execute',{},e=>code=e&&e.code);
if(code!=='UNSUPPORTED_OPERATION'||posts!==0)process.exit(2);console.log('allowlist enforced');''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "allowlist enforced")

    def test_client_rejects_inconsistent_memory_policy_claim(self):
        result = self.node(r'''const fs=require('fs'),vm=require('vm');const box={Date,Math,JSON,Object,Array};box.window=box;
box.XMLHttpRequest=function(){this.status=200;this.open=(m)=>{this.method=m;};this.setRequestHeader=()=>{};this.send=(body)=>{
const request=body?JSON.parse(body):null;const regions=[['code','r-x'],['constant','r--'],['mutable','rw-'],['heap','rw-'],['stack','rw-']].map(x=>({name:x[0],expected:x[1],observed:x[1],status:'PASS'}));regions[2].observed='rwx';
const result=request?{abiVersion:1,backend:'linux-local',overall:'PASS',writableExecutableRegions:1,regions:regions,simulated:false}:{backend:'linux-native',platform:'linux',architecture:'x86_64',simulated:false,nativeLibraryLoaded:true,nativeProcessConnected:false,switchNativeExecution:false};
this.responseText=JSON.stringify({protocol:'webkit2jb-bridge/1',requestId:request?request.requestId:'handshake',operation:request?request.operation:'handshake',backend:'linux-native',ok:true,error:null,result:result,execution:{mode:'native-library',platform:'linux',architecture:'x86_64',origin:'ctypes-loaded-library',nativeLibraryLoaded:true,nativeProcessConnected:false,switchNativeExecution:false}});this.onload();};};
vm.runInNewContext(fs.readFileSync('bridge-client.js','utf8'),box);let code=null;
box.NS2BridgeClient.handshake(function(e){if(e)return process.exit(1);box.NS2BridgeClient.request('memory-policy',{},function(error){code=error&&error.code;});});
if(code!=='INVALID_MEMORY_POLICY')process.exit(2);console.log('inconsistent RWX report rejected');''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "inconsistent RWX report rejected")

    def test_client_recognizes_c_library_without_claiming_switch_execution(self):
        result = self.node(r'''const fs=require('fs'),vm=require('vm');const box={Date,Math,JSON,Object};box.window=box;
box.XMLHttpRequest=function(){this.status=200;this.open=()=>{};this.setRequestHeader=()=>{};this.send=()=>{this.responseText=JSON.stringify({protocol:'webkit2jb-bridge/1',requestId:'handshake',operation:'handshake',backend:'linux-native',ok:true,error:null,result:{backend:'linux-native',platform:'linux',architecture:'x86_64',simulated:false,nativeLibraryLoaded:true,nativeProcessConnected:false,switchNativeExecution:false},execution:{mode:'native-library',platform:'linux',architecture:'x86_64',origin:'ctypes-loaded-library',nativeLibraryLoaded:true,nativeProcessConnected:false,switchNativeExecution:false}});this.onload();};};
vm.runInNewContext(fs.readFileSync('bridge-client.js','utf8'),box);let backend=null;
box.NS2BridgeClient.handshake((e,r)=>{if(e)process.exit(1);backend=r.backend;});
if(backend!=='linux-native')process.exit(2);console.log(backend);''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "linux-native")

    def test_client_times_out_without_retrying(self):
        result = self.node(r'''const fs=require('fs'),vm=require('vm');let calls=0;const box={Date,Math,JSON,Object};box.window=box;
box.XMLHttpRequest=function(){this.open=()=>{};this.setRequestHeader=()=>{};this.send=()=>{calls++;this.ontimeout();};};
vm.runInNewContext(fs.readFileSync('bridge-client.js','utf8'),box);let code=null;
box.NS2BridgeClient.handshake(e=>code=e&&e.code);
if(code!=='TIMEOUT'||calls!==1)process.exit(1);console.log('single timeout');''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "single timeout")

    def test_browser_scripts_keep_es5_compatible_syntax(self):
        for path in (ROOT / "bridge-client.js", ROOT / "portal.js"):
            source = path.read_text(encoding="utf-8")
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotRegex(source, r"=>|[\x60]|\b(?:let|const)\s")
        schema = json.loads((ROOT / "bridge/protocol/bridge-v1.schema.json").read_text(encoding="utf-8"))
        self.assertIn("oneOf", schema)
        self.assertIn("ns2jb-compatibility", schema["oneOf"][0]["properties"]["operation"]["enum"])
        self.assertIn("memory-policy", schema["oneOf"][0]["properties"]["operation"]["enum"])


if __name__ == "__main__":
    unittest.main()
