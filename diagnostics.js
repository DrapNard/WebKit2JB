(function (global) {
    'use strict';

    var catalog = {
        api: {
            title: 'API availability',
            description: 'Read available APIs, run a minimal Canvas 2D check, and inspect FontFaceSet.',
            schema: 'ns2-webkit-api-probe-1',
            version: '1.0.0'
        },
        'font-load': {
            title: 'Local font loading',
            description: 'Load one local system FontFace, then remove it from the set after resolution.',
            schema: 'ns2-fontface-survey-font-load-v1',
            version: '1.0.0'
        },
        reentrancy: {
            title: 'JavaScript reentrancy',
            description: 'Observe the then getter during one document.fonts.load() call without changing CSS rules during the call.',
            schema: 'ns2-fontface-survey-safe-v2',
            version: '2.0.0'
        }
    };

    function id() {
        return 'ns2-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
    }

    function errorText(error) {
        return error && error.name ? error.name + ': ' + error.message : String(error);
    }

    function get(testId) {
        return catalog[testId] || null;
    }

    function run(testId, ui) {
        var cfg = catalog[testId];
        if (!cfg) return false;

        var started = Date.now();
        var capabilities = global.NS2Capabilities ? global.NS2Capabilities.detect() : {schema: 'ns2-capabilities-v1', features: {}};
        if (!global.NS2Reporting || typeof global.NS2Reporting.createReport !== 'function' ||
                !global.NS2Capabilities || typeof global.NS2Capabilities.missingFor !== 'function') {
            if (ui && ui.onStatus) ui.onStatus('unsupported · shared browser core unavailable');
            return false;
        }
        var report = global.NS2Reporting.createReport({
            schema: cfg.schema,
            schemaVersion: 2,
            testId: testId,
            testVersion: cfg.version,
            capabilities: capabilities
        });
        report.timestamp = report.startedAt;
        var finished = false;
        var activeFace = null;

        function update() {
            if (ui && ui.onReport) ui.onReport(report);
        }

        function stateSnapshot() {
            var state = {documentFontsStatus: null, documentFontsSize: null, fontFaceStatus: null};
            try { state.documentFontsStatus = document.fonts ? String(document.fonts.status) : null; } catch (_) { state.documentFontsStatus = 'error'; }
            try { state.documentFontsSize = document.fonts ? Number(document.fonts.size) : null; } catch (_) { state.documentFontsSize = null; }
            try { state.fontFaceStatus = activeFace ? String(activeFace.status) : null; } catch (_) { state.fontFaceStatus = 'error'; }
            return state;
        }

        function event(name, info) {
            var item = global.NS2Reporting.addEvent(report, name, Date.now() - started, info || {});
            item.state = stateSnapshot();
            if (ui && ui.onEvent) ui.onEvent(item);
            update();
        }

        function setStatus(message) {
            if (ui && ui.onStatus) ui.onStatus(message);
        }

        function complete() {
            if (finished) return;
            finished = true;
            report.completedAt = new Date().toISOString();
            update();
            setStatus('Report ready · sending to local server…');
            global.NS2Reporting.post(report, {
                onAck: function (acknowledgment) {
                    report.acknowledgment = acknowledgment;
                    event('server-acknowledged', {status: acknowledgment.duplicate ? 200 : 201,
                        duplicate: !!acknowledgment.duplicate, receivedAt: acknowledgment.receivedAt || null,
                        buildId: acknowledgment.buildId || null});
                    setStatus('Acknowledgement received · ' + (acknowledgment.receivedAt || 'date inconnue') +
                        ' · ' + acknowledgment.reportId + (acknowledgment.duplicate ? ' · duplicate recognized' : ' · saved'));
                    update();
                    if (ui && ui.onBusy) ui.onBusy(false);
                },
                onError: function (error) {
                    report.errors.push(global.NS2Reporting.errorRecord(error, error.phase || 'report-submit'));
                    report.acknowledgment = {accepted: false, phase: error.phase || 'acknowledgment', httpStatus: error.httpStatus || 0};
                    event(error.phase === 'network' ? 'server-unreachable' : 'server-rejected', report.acknowledgment);
                    setStatus('Report not confirmed · keep the displayed JSON before any retry.');
                    update();
                    if (ui && ui.onBusy) ui.onBusy(false);
                }
            });
        }

        function begin() {
            if (ui && ui.onBusy) ui.onBusy(true);
            setStatus('Test manuel en cours… session ' + report.sessionId);
            event('test-started', {sessionId: report.sessionId, startedAt: report.startedAt});
            update();
        }

        function runApiInventory() {
            var names = ['FontFace', 'FontFaceSet', 'Blob', 'File', 'FileReader', 'fetch', 'Worker', 'OffscreenCanvas', 'WebAssembly', 'indexedDB', 'localStorage', 'sessionStorage'];
            report.apis = {};
            report.functional = {};
            event('api-inventory-started', {count: names.length});
            names.forEach(function (name) {
                try { report.apis[name] = typeof global[name]; }
                catch (error) { report.apis[name] = errorText(error); }
            });
            try { report.apis.documentFonts = typeof document.fonts; report.apis.fontsLoad = document.fonts ? typeof document.fonts.load : 'unavailable'; }
            catch (error) { report.apis.documentFonts = errorText(error); }
            event('api-inventory-read', {apiCount: Object.keys(report.apis).length});
            try {
                var canvas = document.createElement('canvas');
                canvas.width = 2; canvas.height = 2;
                report.functional.canvas2D = !!canvas.getContext('2d');
            } catch (error) { report.functional.canvas2D = errorText(error); }
            try { report.functional.fontsCheck = document.fonts && document.fonts.check('12px sans-serif'); }
            catch (error) { report.functional.fontsCheck = errorText(error); }
            report.result = 'completed';
            event('functional-checks-complete', report.functional);
            complete();
        }

        function runFontLoad() {
            var requirement = global.NS2Capabilities.missingFor('font-load', capabilities);
            if (!requirement.supported) {
                report.result = 'unsupported'; report.unsupported = requirement.missing;
                event('api-unavailable', {missing: requirement.missing}); complete(); return;
            }
            var family = 'NS2Local' + Date.now();
            var face;
            var settled = false;
            function finish(result, info, cleanup) {
                if (settled) return;
                settled = true;
                report.result = result;
                event(result, info || {});
                if (cleanup) {
                    try { report.cleanup = {removed: document.fonts.delete(face)}; }
                    catch (error) {
                        report.cleanup = {error: errorText(error)};
                        report.errors.push(global.NS2Reporting.errorRecord(error, 'font-load-cleanup'));
                    }
                    event('cleanup-complete', report.cleanup);
                } else {
                    report.cleanup = 'skipped-while-state-uncertain';
                    event('cleanup-skipped', {reason: 'promise state uncertain'});
                }
                complete();
            }
            try {
                face = new FontFace(family, 'local("systemfont")');
                activeFace = face;
                document.fonts.add(face);
                event('face-added', {family: family, status: face.status});
                var promise = document.fonts.load('16px "' + family + '"', 'AB');
                event('load-called', {status: face.status});
                var timer = setTimeout(function () { finish('timeout-no-mutation', {reason: 'cleanup skipped while promise state is uncertain'}, false); }, 8000);
                promise.then(function (faces) {
                    clearTimeout(timer);
                    finish('resolved', {count: faces.length, status: face.status}, true);
                }, function (error) {
                    clearTimeout(timer);
                    report.error = errorText(error);
                    finish('rejected', {error: report.error}, true);
                });
            } catch (error) {
                report.error = errorText(error);
                report.errors.push(global.NS2Reporting.errorRecord(error, 'fontface-load'));
                report.result = 'exception';
                event('exception', {error: report.error});
                try { if (face) document.fonts.delete(face); }
                catch (cleanupError) { report.errors.push(global.NS2Reporting.errorRecord(cleanupError, 'font-load-exception-cleanup')); }
                complete();
            }
        }

        function runReentrancy() {
            var requirement = global.NS2Capabilities.missingFor('reentrancy', capabilities);
            if (!requirement.supported) {
                report.result = 'unsupported'; report.unsupported = requirement.missing;
                event('api-unavailable', {missing: requirement.missing}); complete(); return;
            }
            var family = 'NS2Safe' + Date.now();
            var style = null;
            var face;
            var prior = null;
            var hooked = false;
            var insideLoad = false;
            var settled = false;

            function restore() {
                if (!hooked) return;
                hooked = false;
                try {
                    if (prior) Object.defineProperty(FontFace.prototype, 'then', prior);
                    else delete FontFace.prototype.then;
                } catch (error) {
                    report.errors.push(global.NS2Reporting.errorRecord(error, 'restore-then-getter'));
                }
            }

            function finish(result, info, cleanup) {
                if (settled) return;
                settled = true;
                restore();
                report.result = result;
                event(result, info || {});
                if (cleanup) {
                    try {
                        if (face) document.fonts.delete(face);
                        if (style && style.parentNode) style.parentNode.removeChild(style);
                        report.cleanup = 'complete';
                    } catch (error) {
                        report.cleanup = errorText(error);
                        report.errors.push(global.NS2Reporting.errorRecord(error, 'reentrancy-cleanup'));
                    }
                    event('cleanup-complete', {result: report.cleanup});
                } else {
                    report.cleanup = 'skipped-while-state-uncertain';
                    event('cleanup-skipped', {reason: 'promise state uncertain'});
                }
                complete();
            }

            try {
                style = document.createElement('style');
                style.textContent = '@font-face{font-family:' + family + ';src:local("systemfont");unicode-range:U+0042}';
                document.head.appendChild(style);
                face = new FontFace(family, 'local("systemfont")', {unicodeRange: 'U+0041'});
                activeFace = face;
                document.fonts.add(face);
                prior = Object.getOwnPropertyDescriptor(FontFace.prototype, 'then');
                // Keep the ordering from the observed safe-v2 run: touch the
                // face's load promise before forcing style resolution and
                // installing the then getter.
                void face.loaded;
                void document.body.offsetTop;
                Object.defineProperty(FontFace.prototype, 'then', {
                    configurable: true,
                    get: function () {
                        event(this === face ? 'getter-A' : 'getter-other', {insideLoad: insideLoad, status: this.status});
                        return undefined;
                    }
                });
                hooked = true;
                event('before-load', {faceStatus: face.status, cssRules: style.sheet ? style.sheet.cssRules.length : null});
                var promise;
                try {
                    insideLoad = true;
                    promise = document.fonts.load('16px ' + family, 'AB');
                } finally {
                    insideLoad = false;
                    restore();
                }
                event('after-load-return', {faceStatus: face.status});
                var timer = setTimeout(function () { finish('timeout-no-mutation', {reason: 'cleanup skipped because promise state is uncertain'}, false); }, 8000);
                promise.then(function (faces) {
                    clearTimeout(timer);
                    finish('resolved', {matchingFaces: faces.length, faceStatus: face.status}, true);
                }, function (error) {
                    clearTimeout(timer);
                    finish('rejected', {error: errorText(error)}, true);
                });
            } catch (error) {
                insideLoad = false;
                restore();
                report.error = errorText(error);
                report.errors.push(global.NS2Reporting.errorRecord(error, 'fontface-reentrancy'));
                finish('exception', {error: report.error}, true);
            }
        }

        begin();
        if (testId === 'api') runApiInventory();
        else if (testId === 'font-load') runFontLoad();
        else runReentrancy();
        return true;
    }

    global.NS2Diagnostics = {get: get, run: run};
})(window);
