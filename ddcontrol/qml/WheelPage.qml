import QtQuick
import QtQuick.Layouts

PageBase {
    id: page
    readonly property int learningSlot: backend.learning.startsWith("button:")
                                        ? parseInt(backend.learning.split(":")[1]) : -1

    Card {
        Layout.fillWidth: true
        title: "Kontroler kierownicy"
        subtitle: "ESP32-S3 przez Bluetooth LE · 12 przycisków + 2 łopatki"
        icon: Theme.icWheel

        DevicePicker {
            Layout.fillWidth: true
            role: "wheel"
            currentKey: backend.wheelDevice
            connected: backend.wheelConnected
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: page.wide ? 3 : 1
        columnSpacing: Theme.gap
        rowSpacing: Theme.gap

        Card {
            Layout.columnSpan: page.wide ? 2 : 1
            Layout.fillWidth: true
            Layout.preferredHeight: 520
            title: "Test przycisków"
            fillBody: true
            subtitle: page.learningSlot >= 0 ? "Naciśnij przycisk na kierownicy, który ma trafić w podświetlone miejsce…"
                                             : "Kliknij przycisk na grafice, aby przypisać mu fizyczny przycisk"
            icon: Theme.icWheel

            actions: [
                AppButton {
                    visible: page.learningSlot >= 0
                    text: "Anuluj"
                    variant: "ghost"
                    onClicked: backend.cancelLearning()
                }
            ]

            WheelGraphic {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 30
                interactive: true
                pressedMask: backend.buttons
                buttonMap: backend.wheelButtonMap
                highlightSlot: page.learningSlot
                ledBase: backend.baseConnected
                ledWheel: backend.wheelConnected
                ledPedals: backend.pedalsConnected
                onSlotClicked: slot => backend.learnWheelButton(slot)
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Wszystkie przyciski"
            fillBody: true
            subtitle: "Stan surowy z kontrolera"
            icon: Theme.icDiag

            GridLayout {
                Layout.fillWidth: true
                columns: 4
                columnSpacing: 8
                rowSpacing: 8
                Repeater {
                    model: Math.max(14, Math.min(32, backend.wheelButtonCount))
                    delegate: Rectangle {
                        required property int index
                        readonly property bool on: (backend.buttons & (1 << index)) !== 0
                        Layout.fillWidth: true
                        implicitHeight: 38
                        radius: 9
                        color: on ? Theme.accent : Theme.surface2
                        border.color: on ? Theme.accent : Theme.border
                        Text {
                            anchors.centerIn: parent
                            text: index + 1
                            font.family: Theme.fontDisplay
                            font.pixelSize: 14
                            color: parent.on ? "#fff" : Theme.textDim
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true }

            AppButton {
                text: "Przywróć domyślne przypisanie"
                glyph: Theme.icUndo
                onClicked: backend.resetWheelButtonMap()
            }
        }
    }

    Item { Layout.preferredHeight: 20 }
}
