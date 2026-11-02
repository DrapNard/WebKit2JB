/* Classic-script client for the bounded local HTTP bridge. No native loader or retries. */
(function (global) {
    'use strict';
    var protocol = 'webkit2jb-bridge/1';
    var backend = null;
    var allowed = {capabilities: true, diagnostic: true, connectivity: true, echo: true,
        'ns2jb-compatibility': true, 'memory-policy': true};
    var sequence = 0;

    function validEnvelope(value, requestId, operation) {
        return value && value.protocol === protocol && value.requestId === requestId &&
            value.operation === operation && typeof value.ok === 'boolean' &&
            value.execution && typeof value.execution.nativeProcessConnected === 'boolean' &&
            typeof value.execution.architecture === 'string' && value.execution.architecture.length > 0 &&
            typeof value.execution.nativeLibraryLoaded === 'boolean' &&
            typeof value.execution.switchNativeExecution === 'boolean' &&
            value.execution.switchNativeExecution === false;
    }
    function validMemoryPolicy(value) {
        var report = value && value.result;
        var expected = {code: 'r-x', constant: 'r--', mutable: 'rw-', heap: 'rw-', stack: 'rw-'};
        var seen = {};
        var rwx = 0;
        var i;
        var region;
        if (!report || typeof report !== 'object' ||
                !/^(PASS|FAIL|UNVERIFIED|UNSUPPORTED)$/.test(report.overall)) return false;
        if (value.backend === 'pc-simulated')
            return report.overall === 'UNSUPPORTED' && report.simulated === true &&
                Array.isArray(report.regions) && report.regions.length === 0;
        if (report.abiVersion !== 1 || !Array.isArray(report.regions) || report.regions.length !== 5 ||
                typeof report.writableExecutableRegions !== 'number' || report.writableExecutableRegions < 0 ||
                typeof report.simulated !== 'boolean') return false;
        for (i = 0; i < report.regions.length; i += 1) {
            region = report.regions[i];
            if (!region || typeof region.name !== 'string' || expected[region.name] !== region.expected ||
                    seen[region.name] || typeof region.observed !== 'string' ||
                    !/^(r--|rw-|r-x|rwx|-w-|--x|-wx|---)$/.test(region.observed) ||
                    !/^(PASS|FAIL|UNVERIFIED|UNSUPPORTED)$/.test(region.status)) return false;
            if (region.observed === 'rwx') rwx += 1;
            seen[region.name] = true;
        }
        if (rwx !== report.writableExecutableRegions) return false;
        if (report.overall === 'PASS') {
            if (rwx !== 0) return false;
            for (i = 0; i < report.regions.length; i += 1)
                if (report.regions[i].status !== 'PASS') return false;
        }
        if (rwx > 0 && report.overall !== 'FAIL') return false;
        return true;
    }
    function parse(xhr, requestId, operation) {
        var data = null;
        try { data = JSON.parse(xhr.responseText); } catch (_) { data = null; }
        if (!validEnvelope(data, requestId, operation))
            return {error: {code: 'INVALID_RESPONSE', message: 'Bridge response did not match the protocol'}};
        if (operation === 'memory-policy' && !validMemoryPolicy(data))
            return {error: {code: 'INVALID_MEMORY_POLICY', message: 'Memory-policy response failed validation'}};
        if (!data.ok) return {error: data.error || {code: 'BACKEND_ERROR', message: 'Bridge request failed'}, response: data};
        if (operation !== 'handshake' && backend && data.backend !== backend)
            return {error: {code: 'BACKEND_MISMATCH', message: 'Response backend differs from handshake'}};
        return {response: data};
    }
    function utf8Length(value) {
        var count = 0;
        var i;
        var first;
        var second;
        for (i = 0; i < value.length; i += 1) {
            first = value.charCodeAt(i);
            if (first <= 0x7f) count += 1;
            else if (first <= 0x7ff) count += 2;
            else if (first >= 0xd800 && first <= 0xdbff) {
                second = value.charCodeAt(i + 1);
                if (!(second >= 0xdc00 && second <= 0xdfff)) return Infinity;
                count += 4;
                i += 1;
            } else if (first >= 0xdc00 && first <= 0xdfff) return Infinity;
            else count += 3;
        }
        return count;
    }
    function call(method, body, expectedId, operation, callback) {
        var xhr;
        var done = false;
        function finish(error, response) {
            if (done) return;
            done = true;
            if (callback) callback(error, response || null);
        }
        if (typeof XMLHttpRequest !== 'function') {
            finish({code: 'UNSUPPORTED', message: 'XMLHttpRequest is unavailable'});
            return;
        }
        xhr = new XMLHttpRequest();
        xhr.open(method, '/api/bridge', true);
        try { xhr.timeout = 3000; } catch (_) {}
        if (method === 'POST') xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = function () {
            var parsed = parse(xhr, expectedId, operation);
            if (xhr.status !== 200 || parsed.error) finish(parsed.error || {code: 'HTTP_ERROR', message: 'HTTP ' + xhr.status}, parsed.response);
            else finish(null, parsed.response);
        };
        xhr.onerror = function () { finish({code: 'NETWORK_ERROR', message: 'Local bridge endpoint is unreachable'}); };
        xhr.ontimeout = function () { finish({code: 'TIMEOUT', message: 'Bridge request timed out'}); };
        try { xhr.send(body); } catch (error) { finish({code: 'REQUEST_ERROR', message: String(error)}); }
    }
    function handshake(callback) {
        call('GET', null, 'handshake', 'handshake', function (error, response) {
            if (error) { backend = null; if (callback) callback(error); return; }
            var identity = response.result || {};
            var execution = response.execution || {};
            var valid = identity.backend === response.backend &&
                typeof identity.architecture === 'string' && identity.architecture.length > 0 &&
                identity.nativeProcessConnected === false &&
                identity.switchNativeExecution === false &&
                execution.nativeProcessConnected === false &&
                execution.switchNativeExecution === false;
            if (response.backend === 'pc-simulated') {
                valid = valid && identity.platform === 'pc' && identity.simulated === true &&
                    identity.nativeLibraryLoaded === false && execution.mode === 'simulated' &&
                    execution.platform === 'pc' && execution.architecture === identity.architecture &&
                    execution.nativeLibraryLoaded === false;
            } else if (response.backend === 'linux-native') {
                valid = valid && identity.platform === 'linux' && identity.simulated === false &&
                    identity.nativeLibraryLoaded === true && execution.mode === 'native-library' &&
                    execution.platform === 'linux' && execution.origin === 'ctypes-loaded-library' &&
                    execution.architecture === identity.architecture &&
                    execution.nativeLibraryLoaded === true;
            } else if (response.backend === 'linux-mock') {
                valid = valid && identity.platform === 'linux' && identity.simulated === true &&
                    identity.nativeLibraryLoaded === true && execution.mode === 'simulated' &&
                    execution.platform === 'linux' && execution.origin === 'ctypes-loaded-library' &&
                    execution.architecture === identity.architecture &&
                    execution.nativeLibraryLoaded === true;
            } else if (response.backend === 'horizon-homebrew') {
                valid = valid && identity.platform === 'horizon' && identity.nativeLibraryLoaded === true &&
                    execution.mode === 'homebrew-process' && execution.platform === 'horizon' &&
                    execution.architecture === identity.architecture &&
                    execution.origin === 'libnx-homebrew' && execution.nativeLibraryLoaded === true;
            } else {
                valid = false;
            }
            if (!valid) {
                backend = null;
                if (callback) callback({code: 'INVALID_BACKEND_IDENTITY', message: 'Backend identity or execution origin is unsupported'});
                return;
            }
            backend = response.backend;
            if (callback) callback(null, response);
        });
    }
    function request(operation, payload, callback) {
        var requestId;
        var body;
        if (!backend) { if (callback) callback({code: 'HANDSHAKE_REQUIRED', message: 'Reconnect before requesting diagnostics'}); return; }
        if (!allowed[operation]) { if (callback) callback({code: 'UNSUPPORTED_OPERATION', message: 'Operation is not allowlisted'}); return; }
        payload = payload || {};
        if (operation === 'echo') {
            if (typeof payload.message !== 'string' || utf8Length(payload.message) > 256) {
                if (callback) callback({code: 'INVALID_PAYLOAD', message: 'Echo is limited to 256 UTF-8 bytes'});
                return;
            }
        } else if (Object.keys(payload).length !== 0) {
            if (callback) callback({code: 'INVALID_PAYLOAD', message: 'This operation takes no payload'});
            return;
        }
        sequence += 1;
        requestId = 'browser-' + Date.now().toString(36) + '-' + sequence.toString(36);
        body = JSON.stringify({protocol: protocol, requestId: requestId, operation: operation,
            backend: backend, payload: payload});
        if (body.length > 4096) { if (callback) callback({code: 'MESSAGE_TOO_LARGE', message: 'Request exceeds 4096 characters'}); return; }
        call('POST', body, requestId, operation, callback);
    }
    global.NS2BridgeClient = {handshake: handshake, reconnect: handshake, request: request};
}(window));
