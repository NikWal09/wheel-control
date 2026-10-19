import QtQuick
import QtQuick.Layouts

// Jedno ustawienie bazy - kontrolka dobierana do rodzaju pola (field.kind).
Loader {
    id: root
    property var field: ({})

    Layout.fillWidth: true
    // pole, którego podłączony firmware nie obsługuje (brak odpowiedzi), znika
    visible: !backend.baseConnected || backend.settings[field.key] !== undefined
    sourceComponent: field.kind === "toggle" ? toggle
                   : field.kind === "choice" ? choice
                   : field.kind === "stepper" ? stepper
                   : field.kind === "readonly" ? readonly
                   : slider

    Component {
        id: slider
        SettingSlider { field: root.field }
    }
    Component {
        id: stepper
        NumberStepper { field: root.field }
    }
    Component {
        id: toggle
        ToggleRow {
            label: root.field.label
            description: root.field.description
            checked: backend.settings[root.field.key] === 1
            enabled: backend.baseConnected
            opacity: enabled ? 1 : 0.45
            onToggled: c => backend.setSetting(root.field.key, c ? 1 : 0)
        }
    }
    Component {
        id: choice
        Segmented {
            label: root.field.label
            description: root.field.description
            enabled: backend.baseConnected
            options: root.field.options
            value: backend.settings[root.field.key]
            onPicked: v => backend.setSetting(root.field.key, v)
        }
    }
    Component {
        id: readonly
        ColumnLayout {
            spacing: 4
            opacity: backend.baseConnected ? 1 : 0.45
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: root.field.label
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    color: Theme.text
                    Layout.fillWidth: true
                }
                Text {
                    text: Theme.formatField(root.field, backend.settings[root.field.key])
                    font.family: Theme.fontDisplay
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    color: Theme.textDim
                }
            }
            Text {
                visible: root.field.description !== ""
                text: root.field.description
                wrapMode: Text.WordWrap
                font.pixelSize: 12
                color: Theme.textDim
                Layout.fillWidth: true
            }
        }
    }
}
