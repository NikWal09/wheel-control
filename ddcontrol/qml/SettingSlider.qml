import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Suwak jednego ustawienia bazy - styl "tuning menu".
ColumnLayout {
    id: root
    property string key
    property string label
    property string description: ""
    property string unit: "%"
    property real from: backend.limits[key] ? backend.limits[key].min : 0
    property real to: backend.limits[key] ? backend.limits[key].max : 100
    property real stepSize: 1
    property var presets: []
    property bool compact: false
    readonly property real deviceValue: backend.settings[key] !== undefined ? backend.settings[key] : from
    readonly property bool live: backend.baseConnected

    spacing: 8
    opacity: live ? 1 : 0.45

    RowLayout {
        Layout.fillWidth: true
        spacing: 8
        Text {
            text: root.label
            font.pixelSize: 14
            font.weight: Font.Medium
            color: Theme.text
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
        Text {
            text: root.live ? Math.round(slider.value) : "–"
            font.family: Theme.fontDisplay
            font.pixelSize: root.compact ? 20 : 24
            font.weight: Font.DemiBold
            color: slider.pressed ? Theme.accent : Theme.text
        }
        Text {
            text: root.unit
            font.family: Theme.fontDisplay
            font.pixelSize: 14
            color: Theme.textDim
            Layout.alignment: Qt.AlignBaseline
        }
    }

    Slider {
        id: slider
        Layout.fillWidth: true
        from: root.from
        to: root.to
        stepSize: root.stepSize
        snapMode: Slider.SnapAlways
        enabled: root.live
        padding: 0
        implicitHeight: 22
        onMoved: backend.setSetting(root.key, value)

        background: Rectangle {
            x: slider.leftPadding
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: slider.availableWidth
            height: 6
            radius: 3
            color: Theme.track
            Rectangle {
                width: slider.visualPosition * parent.width
                height: parent.height
                radius: 3
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: Qt.darker(Theme.accent, 1.6) }
                    GradientStop { position: 1; color: Theme.accent }
                }
            }
        }
        handle: Rectangle {
            x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: 20; height: 20; radius: 10
            color: Theme.text
            border.color: Theme.accent
            border.width: slider.pressed ? 6 : 4
            Behavior on border.width { NumberAnimation { duration: 120 } }
        }
    }

    Binding {
        target: slider
        property: "value"
        value: root.deviceValue
        when: !slider.pressed
        restoreMode: Binding.RestoreNone
    }

    Flow {
        visible: root.presets.length > 0
        Layout.fillWidth: true
        spacing: 6
        Repeater {
            model: root.presets
            delegate: Chip {
                required property var modelData
                text: modelData + root.unit
                active: root.live && Math.round(slider.value) === modelData
                enabled: root.live
                onClicked: backend.setSetting(root.key, modelData)
            }
        }
    }

    Text {
        visible: root.description !== "" && !root.compact
        text: root.description
        wrapMode: Text.WordWrap
        font.pixelSize: 12
        lineHeight: 1.15
        color: Theme.textDim
        Layout.fillWidth: true
    }
}
