import QtQuick
import QtQuick.Layouts

// Pole liczbowe z przyciskami -/+ dla ustawień całkowitych (pary biegunów, CPR, wzmocnienia).
ColumnLayout {
    id: root
    property var field: ({})
    readonly property string key: field.key || ""
    readonly property string label: field.label || ""
    readonly property string description: field.description || ""
    readonly property int step: field.step || 1
    readonly property int minimum: field.min !== undefined ? field.min : 0
    readonly property int maximum: field.max !== undefined ? field.max : 100
    readonly property var deviceValue: backend.settings[key]
    readonly property bool live: backend.baseConnected

    spacing: 8
    opacity: live ? 1 : 0.45

    function commit(v) {
        v = Math.max(minimum, Math.min(maximum, Math.round(v)))
        if (v !== deviceValue)  // np. wyjście z pola bez zmiany - nie wysyłaj (pary biegunów kasują kalibrację)
            backend.setSetting(key, v)
        input.text = v
        input.focus = false
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        Text {
            text: root.label
            font.pixelSize: 14
            font.weight: Font.Medium
            color: Theme.text
            Layout.fillWidth: true
        }
        Rectangle {
            implicitWidth: 150
            implicitHeight: 38
            radius: 10
            color: Theme.bg
            border.color: input.activeFocus ? Theme.accent : Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.margins: 3
                spacing: 0
                StepButton { glyph: ""; onClicked: root.commit(root.deviceValue - root.step) }
                TextInput {
                    id: input
                    Layout.fillWidth: true
                    horizontalAlignment: TextInput.AlignHCenter
                    font.family: Theme.fontDisplay
                    font.pixelSize: 17
                    font.weight: Font.DemiBold
                    color: Theme.text
                    selectionColor: Theme.accent
                    enabled: root.live
                    validator: IntValidator { bottom: root.minimum; top: root.maximum }
                    onEditingFinished: root.commit(parseInt(text))
                }
                StepButton { glyph: ""; onClicked: root.commit(root.deviceValue + root.step) }
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

    Binding {
        target: input
        property: "text"
        value: root.deviceValue !== undefined ? String(root.deviceValue) : "–"
        when: !input.activeFocus
        restoreMode: Binding.RestoreNone
    }

    component StepButton: Rectangle {
        property string glyph
        signal clicked()
        Layout.preferredWidth: 32
        Layout.fillHeight: true
        radius: 8
        color: sma.containsMouse ? Theme.surface3 : "transparent"
        Text {
            anchors.centerIn: parent
            text: parent.glyph
            font.family: Theme.fontIcons
            font.pixelSize: 11
            color: Theme.textDim
        }
        MouseArea {
            id: sma
            anchors.fill: parent
            hoverEnabled: true
            enabled: root.live
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }
}
