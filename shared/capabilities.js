/* Shared capability checks. ES5 syntax; inspection never invokes a diagnostic. */
(function (global) {
    'use strict';

    function readType(object, key) {
        try {
            if (object === null || typeof object === 'undefined') return 'unsupported';
            return typeof object[key];
        } catch (error) {
            return 'error';
        }
    }

    function detect() {
        var fonts = null;
        var fontFacePrototype = null;
        try { fonts = global.document && global.document.fonts; } catch (_) { fonts = null; }
        try { fontFacePrototype = global.FontFace && global.FontFace.prototype; } catch (_) { fontFacePrototype = null; }

        var features = {
            fontFace: readType(global, 'FontFace') === 'function',
            fontFaceSet: !!fonts,
            fontFaceSetLoad: readType(fonts, 'load') === 'function',
            fontFaceSetAdd: readType(fonts, 'add') === 'function',
            fontFaceSetDelete: readType(fonts, 'delete') === 'function',
            fontFaceSetReady: readType(fonts, 'ready') !== 'unsupported' && readType(fonts, 'ready') !== 'error',
            fontFaceSetEvents: readType(fonts, 'addEventListener') === 'function',
            fontFaceEvents: readType(fontFacePrototype, 'addEventListener') === 'function',
            promise: readType(global, 'Promise') === 'function',
            xhr: readType(global, 'XMLHttpRequest') === 'function',
            json: readType(global, 'JSON') === 'object' && readType(global.JSON, 'stringify') === 'function',
            propertyDescriptor: readType(global.Object, 'getOwnPropertyDescriptor') === 'function',
            defineProperty: readType(global.Object, 'defineProperty') === 'function'
        };
        return {
            schema: 'ns2-capabilities-v1',
            userAgent: (global.navigator && global.navigator.userAgent) || null,
            url: (global.location && global.location.href) || null,
            features: features
        };
    }

    function missingFor(testId, snapshot) {
        var features = (snapshot || detect()).features;
        var required = ['xhr', 'json'];
        if (testId === 'font-load') {
            required = required.concat(['fontFace', 'fontFaceSet', 'fontFaceSetLoad', 'fontFaceSetAdd', 'fontFaceSetDelete', 'promise']);
        } else if (testId === 'reentrancy') {
            required = required.concat(['fontFace', 'fontFaceSet', 'fontFaceSetLoad', 'fontFaceSetAdd', 'fontFaceSetDelete', 'promise', 'propertyDescriptor', 'defineProperty']);
        }
        var missing = [];
        for (var i = 0; i < required.length; i++) {
            if (!features[required[i]]) missing.push(required[i]);
        }
        return {supported: missing.length === 0, missing: missing};
    }

    global.NS2Capabilities = {detect: detect, missingFor: missingFor};
}(window));
