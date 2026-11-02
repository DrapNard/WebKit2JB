/* Shared report envelope and acknowledged POST. ES5 syntax, no automatic retry. */
(function (global) {
    'use strict';

    function identifier(prefix) {
        return prefix + '-' + Date.now().toString(36) + '-' +
            Math.floor(Math.random() * 0x100000000).toString(36);
    }

    function createReport(options) {
        options = options || {};
        var now = new Date().toISOString();
        var reportId = identifier('report');
        return {
            reportEnvelopeVersion: 1,
            schema: options.schema || 'ns2-diagnostic-report-v1',
            schemaVersion: options.schemaVersion || 1,
            reportId: reportId,
            sessionId: identifier('session'),
            startedAt: now,
            timestamp: now,
            userAgent: options.userAgent || (global.navigator && global.navigator.userAgent) || null,
            origin: options.origin || (global.location && global.location.origin) || null,
            testId: options.testId || 'unknown',
            testVersion: options.testVersion || '1.0.0',
            capabilities: options.capabilities || {},
            events: [],
            errors: []
        };
    }

    function addEvent(report, name, elapsedMs, info) {
        var event = {
            name: String(name),
            timestamp: new Date().toISOString(),
            elapsedMs: Math.max(0, Number(elapsedMs) || 0),
            info: info && typeof info === 'object' ? info : {}
        };
        report.events.push(event);
        return event;
    }

    function errorRecord(error, phase) {
        return {
            phase: phase || 'unknown',
            name: (error && error.name) ? String(error.name) : 'Error',
            message: (error && error.message) ? String(error.message) : String(error)
        };
    }

    function post(report, callbacks) {
        callbacks = callbacks || {};
        var xhr;
        try {
            if (typeof global.XMLHttpRequest !== 'function' || !global.JSON || typeof global.JSON.stringify !== 'function') {
                throw new Error('XMLHttpRequest or JSON.stringify is unsupported');
            }
            xhr = new global.XMLHttpRequest();
            xhr.open('POST', '/api/report', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            try { xhr.timeout = 10000; } catch (_) {}
            xhr.onload = function () {
                var ack = null;
                try { ack = global.JSON.parse(xhr.responseText); } catch (_) { ack = null; }
                var statusAccepted = xhr.status === 200 || xhr.status === 201;
                var valid = statusAccepted && ack && ack.accepted === true &&
                    ack.reportId === report.reportId && ack.sessionId === report.sessionId;
                if (!valid) {
                    if (callbacks.onError) callbacks.onError({phase: 'acknowledgment', httpStatus: xhr.status, acknowledgment: ack});
                    return;
                }
                report.server = {
                    receivedAt: ack.receivedAt || null,
                    file: ack.file || null,
                    buildId: ack.buildId || null,
                    gitCommit: ack.gitCommit || null,
                    dirty: typeof ack.dirty === 'boolean' ? ack.dirty : null,
                    servedPageSha256: ack.servedPageSha256 || null,
                    servedScriptsSha256: ack.servedScriptsSha256 || {},
                    servedResourcesSha256: ack.servedResourcesSha256 || {},
                    serverSha256: ack.serverSha256 || null,
                    bridgeServiceSha256: ack.bridgeServiceSha256 || null,
                    bridgeRuntimeSha256: ack.bridgeRuntimeSha256 || null,
                    reportSchemaSha256: ack.reportSchemaSha256 || null,
                    duplicate: ack.duplicate === true
                };
                if (callbacks.onAck) callbacks.onAck(ack);
            };
            xhr.onerror = function () {
                if (callbacks.onError) callbacks.onError({phase: 'network', httpStatus: xhr.status || 0});
            };
            xhr.ontimeout = function () {
                if (callbacks.onError) callbacks.onError({phase: 'timeout', httpStatus: xhr.status || 0});
            };
            xhr.send(global.JSON.stringify(report));
        } catch (error) {
            if (callbacks.onError) callbacks.onError(errorRecord(error, 'submit'));
        }
    }

    global.NS2Reporting = {
        createReport: createReport,
        addEvent: addEvent,
        errorRecord: errorRecord,
        post: post
    };
}(window));
