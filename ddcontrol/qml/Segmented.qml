import QtQuick
import QtQuick.Layouts

// Przełącznik segmentowy. options: [{label, value}]
ColumnLayout {
    id: root
    property string label: ""
    property string description: ""
    property var options: []
    property var value
    signal picked(var value)

    spacing: 8
    opacity: enabled ? 1 : 0.45

    Text {
        visible: root.label !== ""
        text: root.label
        font.pixelSize: 14
        font.weight: Font.Medium
        color: Theme.text
    }

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 38
        radius: 10
        color: Theme.bg
        border.color: Theme.border

        RowLayout {
            anchors.fill: parent
            anchors.margins: 3
            spacing: 3
            Repeater {
                model: root.options
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool selected: modelData.value === root.value
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: selected ? Theme.surface3 : (ma.containsMouse ? Theme.surface : "transparent")
                    border.color: selected ? Theme.accent : "transparent"
                    Behavior on color { ColorAnimation { duration: 120 } }
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        font.pixelSize: 13
                        font.weight: selected ? Font.DemiBold : Font.Normal
                        color: selected ? Theme.text : Theme.textDim
                    }
                    MouseArea {
                        id: ma
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        enabled: root.enabled
                        onClicked: root.picked(modelData.value)
                    }
                }
            }
        }
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
