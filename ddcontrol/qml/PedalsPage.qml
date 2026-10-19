import QtQuick
import QtQuick.Layouts

PageBase {
    id: page

    Card {
        Layout.fillWidth: true
        title: "Kontroler pedałów"
        subtitle: "ESP32-S3 jako gamepad USB · kalibracja i martwe strefy są w firmware pedałów"
        icon: Theme.icPedals

        DevicePicker {
            Layout.fillWidth: true
            role: "pedals"
            currentKey: backend.pedalsDevice
            connected: backend.pedalsConnected
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        columnSpacing: Theme.gap
        rowSpacing: Theme.gap

        Repeater {
            model: [
                { key: "throttle", label: "Gaz", sub: "Potencjometr liniowy", color: Theme.throttle },
                { key: "brake", label: "Hamulec", sub: "Belka tensometryczna 120 kg + HX711", color: Theme.brake }
            ]
            delegate: Card {
                id: pedalCard
                required property var modelData
                readonly property var cfg: backend.pedalMap[modelData.key]
                readonly property real value: modelData.key === "throttle" ? backend.throttle : backend.brake
                readonly property bool learning: backend.learning === "pedal:" + modelData.key
                Layout.fillWidth: true
                title: modelData.label
                subtitle: modelData.sub
                icon: Theme.icPedals

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 28

                    PedalBar {
                        Layout.preferredHeight: 260
                        label: pedalCard.modelData.label
                        value: pedalCard.value
                        barColor: pedalCard.modelData.color
                        active: backend.pedalsConnected
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        spacing: 18

                        Segmented {
                            Layout.fillWidth: true
                            label: "Oś"
                            options: backend.axisNames.map((n, i) => ({ label: n, value: i }))
                            value: pedalCard.cfg.axis
                            onPicked: v => backend.setPedalMapping(pedalCard.modelData.key, v, pedalCard.cfg.invert)
                        }
                        ToggleRow {
                            Layout.fillWidth: true
                            label: "Odwróć oś"
                            description: "Gdy pedał w spoczynku pokazuje 100%."
                            checked: pedalCard.cfg.invert
                            onToggled: c => backend.setPedalMapping(pedalCard.modelData.key, pedalCard.cfg.axis, c)
                        }
                        AppButton {
                            text: pedalCard.learning ? "Wciśnij pedał do oporu…" : "Wykryj oś automatycznie"
                            glyph: Theme.icDetect
                            variant: pedalCard.learning ? "primary" : "secondary"
                            enabled: backend.pedalsConnected
                            onClicked: pedalCard.learning ? backend.cancelLearning() : backend.learnPedal(pedalCard.modelData.key)
                        }
                    }
                }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        title: "Surowe osie"
        subtitle: "Wszystkie osie wybranego kontrolera – przydatne przy szukaniu właściwej"
        icon: Theme.icChart

        GridLayout {
            Layout.fillWidth: true
            columns: page.wide ? 3 : 2
            columnSpacing: 28
            rowSpacing: 14
            Repeater {
                model: backend.axisNames.length
                delegate: RowLayout {
                    required property int index
                    readonly property real v: backend.pedalRaw[index] || 0
                    Layout.fillWidth: true
                    spacing: 12
                    Text {
                        Layout.preferredWidth: 18
                        text: backend.axisNames[index]
                        font.family: Theme.fontDisplay
                        font.pixelSize: 14
                        color: Theme.textDim
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 8
                        radius: 4
                        color: Theme.bg
                        border.color: Theme.border
                        Rectangle {
                            width: parent.width * Math.max(0, Math.min(1, parent.parent.v))
                            height: parent.height
                            radius: 4
                            color: Theme.accent
                        }
                    }
                    Text {
                        Layout.preferredWidth: 44
                        horizontalAlignment: Text.AlignRight
                        text: backend.pedalsConnected ? Math.round(parent.v * 100) + "%" : "–"
                        font.family: Theme.fontDisplay
                        font.pixelSize: 14
                        color: Theme.text
                    }
                }
            }
        }
    }

    Item { Layout.preferredHeight: 20 }
}
