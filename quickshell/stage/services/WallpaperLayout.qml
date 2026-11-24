pragma Singleton

import QtQuick

QtObject {
    function cleanPath(path) {
        return path ? String(path) : "";
    }
    function registerPainter(screen, live, path) {}
    function unregisterPainter(screen) {}
    function publishGeometry(screen, w, h, imgW, imgH, fit) {}
    function framingFor(screen, key) {
        return { zoom: 1.0, offsetX: 0.0, offsetY: 0.0, angle: 0.0 };
    }
    function angleFor(screen, key) {
        return 0.0;
    }
}
