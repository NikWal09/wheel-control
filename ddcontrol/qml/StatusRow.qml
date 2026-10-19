import QtQuick
import QtQuick.Layouts

// Wiersz statusu urządzenia w pasku bocznym.
RowLayout {
    id: root
    property string label
    property string detail: ""
    property bool ok: false

    spacing: 10

    Rectangle {
        width: 8; height: 8; radius: 4
        color: root.ok ? Theme.success : Theme.textFaint
        Rectangle {
            visible: root.ok
            anchors.centerIn: parent
            width: 18; height: 18; radius: 9
            color: Theme.success
            opacity: 0.18
        }
    }
    ColumnLayout {
        spacing: 0
        Layout.fillWidth: true
        Text {
            text: root.label
            font.pixelSize: 12
            font.weight: Font.DemiBold
            color: root.ok ? Theme.text : Theme.textDim
        }
        Text {
            text: root.ok ? (root.detail || "Połączono") : "Brak połączenia"
            font.pixelSize: 11
            color: Theme.textFaint
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }
}
