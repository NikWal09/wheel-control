pragma Singleton
import QtQuick

QtObject {
    // Kolor akcentu ustawiany z Main.qml (backend.accent)
    property color accent: "#FF4D2E"
    readonly property color accentSoft: Qt.rgba(accent.r, accent.g, accent.b, 0.14)

    readonly property color bg: "#0A0C0F"
    readonly property color sidebar: "#0E1014"
    readonly property color surface: "#13161B"
    readonly property color surface2: "#1A1E25"
    readonly property color surface3: "#232832"
    readonly property color border: "#232831"
    readonly property color track: "#2A303A"
    readonly property color text: "#F2F4F7"
    readonly property color textDim: "#8B93A1"
    readonly property color textFaint: "#5A6270"
    readonly property color success: "#2ED47A"
    readonly property color warning: "#FFB020"
    readonly property color danger: "#FF4757"
    readonly property color info: "#3DA5FF"
    readonly property color throttle: "#2ED47A"
    readonly property color brake: "#FF4757"

    readonly property string fontDisplay: "Bahnschrift"
    readonly property string fontBody: "Segoe UI"
    readonly property string fontIcons: "Segoe MDL2 Assets"

    readonly property int radius: 14
    readonly property int gap: 18

    // Ikony (Segoe MDL2 Assets)
    readonly property string icDashboard: ""
    readonly property string icFfb: ""
    readonly property string icBase: ""
    readonly property string icPedals: ""
    readonly property string icWheel: ""
    readonly property string icProfiles: ""
    readonly property string icSettings: ""
    readonly property string icSave: ""
    readonly property string icRefresh: ""
    readonly property string icPower: ""
    readonly property string icInfo: ""
    readonly property string icWarning: ""
    readonly property string icCheck: ""
    readonly property string icClose: ""
    readonly property string icAdd: ""
    readonly property string icDelete: ""
    readonly property string icImport: ""
    readonly property string icExport: ""
    readonly property string icDetect: ""
    readonly property string icDiag: ""
    readonly property string icKey: ""
    readonly property string icChart: ""
    readonly property string icUndo: ""

    readonly property string icCenter: ""

    // Ikony po nazwie - używane przez opis ustawień z Pythona (sekcje, akcje).
    function icon(name) {
        return ({
            ffb: icFfb, wheel: icWheel, base: icBase, warning: icWarning, power: icPower,
            tune: icPedals, diag: icDiag, center: icCenter, sync: icRefresh, import: icImport,
            info: icInfo, save: icSave
        })[name] || icInfo
    }

    // Wartość pola do wyświetlenia (pole = backend.fieldMap[klucz]).
    function formatField(field, value) {
        if (value === undefined || value === null || !field)
            return "–"
        if (field.kind === "choice") {
            const opt = field.options.find(o => o.value === value)
            return opt ? opt.label : String(value)
        }
        if (field.kind === "toggle")
            return value ? "Wł." : "Wył."
        const shown = Math.round(value * field.scale)
        return field.unit === "%" || field.unit === "°" ? shown + field.unit
             : (shown + " " + field.unit).trim()
    }
}
