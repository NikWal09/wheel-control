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
        columns: 1
        columnSpacing: Theme.gap
        rowSpacing: Theme.gap

        Card {
            Layout.fillWidth: true
            Layout.preferredHeight: 700
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
                Layout.margins: 0
                interactive: true
                pressedMask: backend.buttons
                buttonMap: backend.wheelButtonMap
                highlightSlot: page.learningSlot
                wheelConnected: backend.wheelConnected
                onSlotClicked: slot => backend.learnWheelButton(slot)
            }

            // znaczenie diod na kierownicy
            Flow {
                Layout.fillWidth: true
                spacing: 18
                Repeater {
                    model: [
                        { c: "#B9F5CB", name: "Zasilanie",
                          state: backend.wheelConnected ? "włączona" : "nieznany (brak połączenia)" },
                        { c: "#3D7BFF", name: "Bluetooth",
                          state: backend.wheelConnected ? "połączona – świeci" : "mruga, gdy szuka połączenia" },
                        { c: "#E9F2FF", name: "Ładowanie", state: "brak danych z kontrolera" }
                    ]
                    delegate: Row {
                        required property var modelData
                        spacing: 8
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 10; height: 10; radius: 5
                            color: modelData.c
                        }
                        Text {
                            text: modelData.name + ": "
                            font.pixelSize: 12
                            font.weight: Font.Medium
                            color: Theme.text
                        }
                        Text {
                            text: modelData.state
                            font.pixelSize: 12
                            color: Theme.textDim
                        }
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true
            title: "Wszystkie przyciski"
            subtitle: "Stan surowy z kontrolera"
            icon: Theme.icDiag

            GridLayout {
                Layout.fillWidth: true
                columns: 7
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

            AppButton {
                text: "Przywróć domyślne przypisanie"
                glyph: Theme.icUndo
                onClicked: backend.resetWheelButtonMap()
            }
        }
    }

    Item { Layout.preferredHeight: 20 }
}
