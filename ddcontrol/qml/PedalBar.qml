import QtQuick
import QtQuick.Layouts

// Pionowy wskaźnik wciśnięcia pedału.
ColumnLayout {
    id: root
    property string label
    property real value: 0          // 0..1
    property color barColor: Theme.accent
    property bool active: true

    spacing: 10

    Text {
        Layout.alignment: Qt.AlignHCenter
        text: root.active ? Math.round(root.value * 100) + "%" : "–"
        font.family: Theme.fontDisplay
        font.pixelSize: 22
        font.weight: Font.DemiBold
        color: Theme.text
    }

    Rectangle {
        Layout.alignment: Qt.AlignHCenter
        Layout.fillHeight: true
        Layout.preferredWidth: 46
        Layout.minimumHeight: 120
        radius: 10
        color: Theme.bg
        border.color: Theme.border
        clip: true

        Repeater {
            model: 9
            delegate: Rectangle {
                required property int index
                x: 0; width: parent.width
                y: parent.height * (index + 1) / 10
                height: 1
                color: "#1A1E25"
            }
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 3
            height: Math.max(0, (parent.height - 6) * (root.active ? root.value : 0))
            radius: 7
            gradient: Gradient {
                GradientStop { position: 0; color: root.barColor }
                GradientStop { position: 1; color: Qt.darker(root.barColor, 2.2) }
            }
        }
    }

    Text {
        Layout.alignment: Qt.AlignHCenter
        text: root.label.toUpperCase()
        font.family: Theme.fontDisplay
        font.pixelSize: 12
        font.letterSpacing: 1.5
        color: Theme.textDim
    }
}
