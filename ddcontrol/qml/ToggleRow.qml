import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Wiersz z opisem i przełącznikiem.
RowLayout {
    id: root
    property string label
    property string description: ""
    property bool checked: false
    signal toggled(bool checked)

    spacing: 16

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 3
        Text {
            text: root.label
            font.pixelSize: 14
            font.weight: Font.Medium
            color: Theme.text
        }
        Text {
            visible: root.description !== ""
            text: root.description
            wrapMode: Text.WordWrap
            font.pixelSize: 12
            color: Theme.textDim
            Layout.fillWidth: true
        }
    }

    Switch {
        id: sw
        enabled: root.enabled
        onToggled: root.toggled(checked)
        indicator: Rectangle {
            implicitWidth: 46
            implicitHeight: 26
            radius: 13
            color: sw.checked ? Theme.accent : Theme.track
            Behavior on color { ColorAnimation { duration: 150 } }
            Rectangle {
                x: sw.checked ? parent.width - width - 3 : 3
                anchors.verticalCenter: parent.verticalCenter
                width: 20; height: 20; radius: 10
                color: "#FFFFFF"
                Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            }
        }
        HoverHandler { cursorShape: Qt.PointingHandCursor }
    }

    Binding { target: sw; property: "checked"; value: root.checked }
}
