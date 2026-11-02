import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = "node"


class SharedBrowserCoreTests(unittest.TestCase):
    def run_node(self, script):
        return subprocess.run([NODE, "-e", script], cwd=str(ROOT), capture_output=True, text=True, timeout=10)

    def test_capability_detection_returns_unsupported_without_throwing(self):
        result = self.run_node(r'''const fs=require('fs'),vm=require('vm');
const box={Date,Math,JSON,Object,navigator:{userAgent:'test'},location:{href:'http://local/'},document:{}};
box.window=box; vm.runInNewContext(fs.readFileSync('shared/capabilities.js','utf8'),box);
const snap=box.NS2Capabilities.detect();
const req=box.NS2Capabilities.missingFor('reentrancy',snap);
if(snap.features.fontFaceSet || req.supported || req.missing.indexOf('fontFaceSetLoad')<0) process.exit(1);
console.log(JSON.stringify({schema:snap.schema,supported:req.supported,missing:req.missing}));''')
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "ns2-capabilities-v1")
        self.assertFalse(payload["supported"])
        self.assertIn("fontFaceSetLoad", payload["missing"])

    def test_report_envelope_and_acknowledgment_validation(self):
        result = self.run_node(r'''const fs=require('fs'),vm=require('vm');
const box={Date,Math,JSON, navigator:{userAgent:'test'}, location:{origin:'http://local'}};
box.window=box; box.XMLHttpRequest=function(){this.status=201;this.responseText='';this.open=function(){};this.setRequestHeader=function(){};this.send=function(body){const sent=JSON.parse(body);this.responseText=JSON.stringify({accepted:true,reportId:sent.reportId,sessionId:sent.sessionId,buildId:'ns2-test',gitCommit:'a'.repeat(40),dirty:true,servedPageSha256:'b'.repeat(64),servedScriptsSha256:{'shared/reporting.js':'c'.repeat(64)},servedResourcesSha256:{'fonts/x.ttf':'d'.repeat(64)},serverSha256:'e'.repeat(64),reportSchemaSha256:'f'.repeat(64)});this.onload();};};
vm.runInNewContext(fs.readFileSync('shared/reporting.js','utf8'),box);
const report=box.NS2Reporting.createReport({schema:'ns2-webkit-api-probe-1',testId:'api',testVersion:'1.0.0',capabilities:{features:{}}});
box.NS2Reporting.addEvent(report,'started',3,{ok:true});
let ack=null,err=null;box.NS2Reporting.post(report,{onAck:x=>ack=x,onError:x=>err=x});
if(err || !ack || !report.server || report.server.buildId!=='ns2-test' || report.events[0].elapsedMs!==3) process.exit(1);
console.log(JSON.stringify({ack:true,buildId:report.server.buildId,resourceCount:Object.keys(report.server.servedResourcesSha256).length}));''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"ack": True, "buildId": "ns2-test", "resourceCount": 1})

    def test_invalid_acknowledgment_is_not_treated_as_persisted(self):
        result = self.run_node(r'''const fs=require('fs'),vm=require('vm');
const box={Date,Math,JSON,navigator:{},location:{}};box.window=box;
box.XMLHttpRequest=function(){this.status=201;this.responseText='{}';this.open=function(){};this.setRequestHeader=function(){};this.send=function(){this.onload();};};
vm.runInNewContext(fs.readFileSync('shared/reporting.js','utf8'),box);
const r=box.NS2Reporting.createReport({testId:'api'});let failed=false;
box.NS2Reporting.post(r,{onAck:function(){process.exitCode=1;},onError:function(e){failed=e.phase==='acknowledgment';}});
if(!failed) process.exit(1);''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_diagnostic_reports_unsupported_without_touching_fontface_apis(self):
        result = self.run_node(r'''const fs=require('fs'),vm=require('vm');
const box={Date,Math,JSON,Object,navigator:{userAgent:'test'},location:{origin:'http://local',href:'http://local/'},document:{}};
box.window=box;box.XMLHttpRequest=function(){this.status=201;this.open=function(){};this.setRequestHeader=function(){};this.send=function(body){const r=JSON.parse(body);this.responseText=JSON.stringify({accepted:true,reportId:r.reportId,sessionId:r.sessionId});this.onload();};};
vm.runInNewContext(fs.readFileSync('shared/capabilities.js','utf8'),box);
vm.runInNewContext(fs.readFileSync('shared/reporting.js','utf8'),box);
vm.runInNewContext(fs.readFileSync('diagnostics.js','utf8'),box);
let report=null;box.NS2Diagnostics.run('font-load',{onReport:r=>report=r});
if(!report||report.result!=='unsupported'||report.unsupported.indexOf('fontFaceSetLoad')<0)process.exit(1);
if(!report.events.some(e=>e.name==='api-unavailable'))process.exit(2);
console.log(JSON.stringify({result:report.result,missing:report.unsupported}));''')
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "unsupported")
        self.assertIn("fontFaceSetLoad", payload["missing"])

    def test_shared_portal_scripts_use_conservative_syntax(self):
        files = [ROOT / "shared/capabilities.js", ROOT / "shared/reporting.js", ROOT / "diagnostics.js", ROOT / "bridge-client.js", ROOT / "portal.js"]
        for path in files:
            result = subprocess.run([NODE, "--check", str(path)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, path.name + ": " + result.stderr)
            source = path.read_text(encoding="utf-8")
            self.assertNotRegex(source, r"=>|`|\b(?:let|const)\s")


if __name__ == "__main__":
    unittest.main()
