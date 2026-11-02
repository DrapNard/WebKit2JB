(function () {
    'use strict';
    var home = document.getElementById('home-view');
    var diagnosticView = document.getElementById('diagnostic-view');
    var title = document.getElementById('diagnostic-title');
    var description = document.getElementById('diagnostic-description');
    var runButton = document.getElementById('run-diagnostic');
    var backButton = document.getElementById('back-home');
    var status = document.getElementById('diagnostic-status');
    var eventLog = document.getElementById('event-log');
    var reportOutput = document.getElementById('report-json');
    var selected = null;

    function clearEvents(message) {
        eventLog.textContent = message || '';
    }

    function showHome() {
        selected = null;
        diagnosticView.hidden = true;
        home.hidden = false;
    }

    function showDiagnostic(testId) {
        var config = window.NS2Diagnostics && window.NS2Diagnostics.get(testId);
        if (!config) return;
        selected = testId;
        title.textContent = config.title;
        description.textContent = config.description;
        status.textContent = 'Ready. No diagnostic has run.';
        runButton.disabled = false;
        backButton.disabled = false;
        clearEvents('Waiting for manual start.');
        reportOutput.textContent = 'No report yet. Press “Run” to start.';
        home.hidden = true;
        diagnosticView.hidden = false;
        runButton.focus();
    }

    Array.prototype.forEach.call(document.querySelectorAll('[data-diagnostic]'), function (button) {
        button.addEventListener('click', function () { showDiagnostic(button.getAttribute('data-diagnostic')); });
    });

    backButton.addEventListener('click', showHome);

    runButton.addEventListener('click', function () {
        if (!selected || !window.NS2Diagnostics) return;
        runButton.disabled = true;
        backButton.disabled = true;
        clearEvents('Initializing diagnostic…');
        reportOutput.textContent = 'Creating report…';
        var started = window.NS2Diagnostics.run(selected, {
            onEvent: function (event) {
                if (eventLog.textContent === 'Initializing diagnostic…') clearEvents();
                var row = document.createElement('p');
                row.textContent = event.timestamp + ' · +' + event.elapsedMs + ' ms · ' + event.name +
                    (event.info && Object.keys(event.info).length ? ' · ' + JSON.stringify(event.info) : '');
                eventLog.appendChild(row);
                eventLog.scrollTop = eventLog.scrollHeight;
            },
            onReport: function (report) { reportOutput.textContent = JSON.stringify(report, null, 2); },
            onStatus: function (message) { status.textContent = message; },
            onBusy: function (busy) {
                runButton.disabled = busy;
                backButton.disabled = busy;
            }
        });
        if (!started) {
            runButton.disabled = false;
            backButton.disabled = false;
            status.textContent = 'Diagnostic unavailable: required browser core or API is missing.';
        }
    });

    // This summary does not run diagnostics; it only displays reports already stored.
    var summaryStatus = document.getElementById('summaryStatus');
    var summaryOutput = document.getElementById('summary');
    var summaryRequest = new XMLHttpRequest();
    summaryRequest.open('GET', '/api/summary', true);
    summaryRequest.onload = function () {
        if (summaryRequest.status !== 200) {
            summaryStatus.textContent = 'Historical summary unavailable (HTTP ' + summaryRequest.status + ').';
            summaryOutput.textContent = 'Diagnostics remain available.';
            return;
        }
        try {
            var summary = JSON.parse(summaryRequest.responseText);
            summaryStatus.textContent = summary.reportCount + ' historical reports indexed · comparison by schema.';
            var all = summary.bySchema || {};
            var relevant = {};
            [
                'ns2-webkit-api-probe-1',
                'ns2-fontface-survey-safe-v2',
                'ns2-fontface-survey-rule-lifecycle-v1',
                'ns2-fontface-survey-css-wrapper-lifetime-v1'
            ].forEach(function (schema) {
                relevant[schema] = all[schema] || {count: 0, note: 'No historical reports for this schema.'};
            });
            summaryOutput.textContent = JSON.stringify(relevant, null, 2);
        } catch (error) {
            summaryStatus.textContent = 'Invalid summary response.';
            summaryOutput.textContent = String(error);
        }
    };
    summaryRequest.onerror = function () {
        summaryStatus.textContent = 'Local server is unreachable.';
        summaryOutput.textContent = 'Diagnostics require the lab server.';
    };
    summaryRequest.send();

    // The handshake identifies the HTTP backend and does not trigger any Switch action.
    var bridgeStatus = document.getElementById('bridge-status');
    var bridgeResult = document.getElementById('bridge-result');
    var bridgeReconnect = document.getElementById('bridge-reconnect');
    var bridgeDiagnostic = document.getElementById('bridge-diagnostic');
    var bridgeNs2jb = document.getElementById('bridge-ns2jb-compatibility');
    var bridgeMemoryPolicy = document.getElementById('bridge-memory-policy');
    function showBridgeError(error) {
        bridgeStatus.textContent = 'Bridge service unavailable · ' + error.code;
        bridgeResult.textContent = JSON.stringify(error, null, 2);
        bridgeDiagnostic.disabled = true;
        bridgeNs2jb.disabled = true;
        bridgeMemoryPolicy.disabled = true;
    }
    function connectBridge() {
        bridgeReconnect.disabled = true;
        bridgeStatus.textContent = 'Checking local HTTP service…';
        if (!window.NS2BridgeClient || typeof window.NS2BridgeClient.reconnect !== 'function') {
            bridgeReconnect.disabled = false;
            showBridgeError({code: 'UNSUPPORTED', message: 'Bridge client unavailable'});
            return;
        }
        window.NS2BridgeClient.reconnect(function (error, response) {
            bridgeReconnect.disabled = false;
            if (error) { showBridgeError(error); return; }
            var evidence = response.result && response.result.platformEvidence || {};
            var pcRunner = evidence.pcRunnerArtifact || {};
            var horizonBuild = evidence.horizonBuild || {};
            var horizonBuilt = horizonBuild.status === 'HORIZON_COMPILED';
            var horizonExecuted = evidence.horizonExecution &&
                evidence.horizonExecution.status === 'HORIZON_EXECUTED' &&
                evidence.horizonExecution.executionConfirmed === true;
            var pcStatus = evidence.pc === 'PC_NATIVE' && response.backend === 'linux-native' ?
                'PC_NATIVE (C library in the PC server)' : 'UNAVAILABLE';
            var buildStatus = horizonBuilt ? 'HORIZON_COMPILED' : 'UNAVAILABLE';
            var executionStatus = horizonExecuted ? 'HORIZON_EXECUTED' : 'UNAVAILABLE (no console evidence)';
            bridgeStatus.textContent = pcStatus + ' · ' + buildStatus + ' · ' + executionStatus;
            if (pcRunner.status === 'PC_ARTIFACT_VALIDATED' && pcRunner.executionConfirmed === false &&
                    pcRunner.architecture === 'x86_64') {
                bridgeStatus.textContent += ' · PC ELF validated (x86-64, not executed) SHA-256 ' +
                    pcRunner.sha256.slice(0, 12) + '…';
            }
            if (horizonBuilt) {
                bridgeStatus.textContent += ' · NRO SHA-256 ' + horizonBuild.artifactSha256.slice(0, 12) + '…';
            }
            if (response.backend === 'linux-native') {
                bridgeStatus.textContent += ' · WebKit does not execute native code.';
            } else if (response.backend === 'linux-mock') {
                bridgeStatus.textContent += ' · simulated C mock backend.';
            } else if (response.backend === 'horizon-homebrew') {
                bridgeStatus.textContent += ' · homebrew backend reported separately from the portal.';
            } else {
                bridgeStatus.textContent += ' · simulated HTTP service.';
            }
            bridgeDiagnostic.disabled = false;
            bridgeNs2jb.disabled = false;
            bridgeMemoryPolicy.disabled = false;
            bridgeResult.textContent = JSON.stringify(response, null, 2);
        });
    }
    bridgeReconnect.addEventListener('click', connectBridge);
    bridgeDiagnostic.addEventListener('click', function () {
        bridgeDiagnostic.disabled = true;
        window.NS2BridgeClient.request('diagnostic', {}, function (error, response) {
            bridgeDiagnostic.disabled = false;
            if (error) { showBridgeError(error); return; }
            bridgeResult.textContent = JSON.stringify(response, null, 2);
        });
    });
    bridgeNs2jb.addEventListener('click', function () {
        bridgeNs2jb.disabled = true;
        window.NS2BridgeClient.request('ns2jb-compatibility', {}, function (error, response) {
            bridgeNs2jb.disabled = false;
            if (error) { showBridgeError(error); return; }
            bridgeResult.textContent = JSON.stringify(response, null, 2);
        });
    });
    bridgeMemoryPolicy.addEventListener('click', function () {
        bridgeMemoryPolicy.disabled = true;
        window.NS2BridgeClient.request('memory-policy', {}, function (error, response) {
            bridgeMemoryPolicy.disabled = false;
            if (error) { showBridgeError(error); return; }
            bridgeResult.textContent = JSON.stringify(response, null, 2);
        });
    });
    connectBridge();
})();
