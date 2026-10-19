import QtQuick

// Mały przycisk-pastylka (presety wartości, filtry).
Rectangle {
    id: root
    property string text
    property bool active: false
    signal clicked()

    implicitWidth: label.implicitWidth + 22
    implicitHeight: 28
    radius: 14
    color: active ? Theme.accentSoft : (mouse.containsMouse ? Theme.surface3 : Theme.surface2)
    border.color: active ? Theme.accent : Theme.border
    opacity: enabled ? 1 : 0.5

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        font.family: Theme.fontDisplay
        font.pixelSize: 13
        color: root.active ? Theme.accent : Theme.textDim
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
