import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

PageBase {
    id: page

    NoBaseBanner {}

    GridLayout {
        Layout.fillWidth: true
        columns: 3
        columnSpacing: Theme.gap
        rowSpacing: Theme.gap

        // ---------- kierownica na żywo ----------
        Card {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            Layout.preferredHeight: 520
            title: "Kierownica"
            fillBody: true
            subtitle: backend.baseConnected ? "Pozycja i moment z bazy w czasie rzeczywistym" : "Czekam na bazę…"
            icon: Theme.icWheel

            actions: [
                AppButton {
                    text: "Wycentruj"
                    glyph: Theme.icCenter
                    variant: "primary"
                    visible: backend.canCenter
                    enabled: backend.baseConnected
                    ToolTip.visible: hovered
                    ToolTip.delay: 400
                    ToolTip.text: "Ustaw kierownicę prosto i kliknij – obecna pozycja stanie się środkiem (0°)"
                    onClicked: backend.centerWheel()
                },
                Text {
                    visible: !backend.canCenter && backend.baseConnected
                    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                    text: "Centrowanie: firmware " + backend.firmwareName + " nie udostępnia tej komendy"
                    font.pixelSize: 12
                    color: Theme.textDim
                }
            ]

            Item {
                id: stage
                Layout.fillWidth: true
                Layout.fillHeight: true
                // średnica łuku: zmieści się nad odczytem kąta i paskiem momentu
                readonly property real dial: Math.max(160, Math.min(width * 0.62, height - 96))

                // łuk zakresu obrotu
                Canvas {
                    id: arc
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 0
                    width: stage.dial
                    height: stage.dial
                    property real angle: backend.angle
                    property real range: backend.motionRange || 900
                    property color accent: Theme.accent
                    onAngleChanged: requestPaint()
                    onAccentChanged: requestPaint()
                    onPaint: {
                        const ctx = getContext("2d")
                        ctx.reset()
                        const cx = width / 2, cy = height / 2, r = width / 2 - 4
                        const start = -Math.PI / 2
                        ctx.lineCap = "round"
                        ctx.lineWidth = 4
                        ctx.strokeStyle = "#1E232B"
                        ctx.beginPath()
                        ctx.arc(cx, cy, r, Math.PI * 0.8, Math.PI * 2.2)
                        ctx.stroke()
                        // pełna skala łuku = połowa zakresu obrotu w każdą stronę
                        const frac = Math.max(-1, Math.min(1, angle / (range / 2)))
                        const sweep = frac * Math.PI * 0.7
                        ctx.strokeStyle = accent
                        ctx.beginPath()
                        ctx.arc(cx, cy, r, start + Math.min(0, sweep), start + Math.max(0, sweep))
                        ctx.stroke()
                    }
                }

                WheelGraphic {
                    id: wheel
                    anchors.centerIn: arc
                    width: stage.dial - 34
                    height: width * 280 / 440
                    wheelRotation: backend.angle
                    pressedMask: backend.buttons
                    buttonMap: backend.wheelButtonMap
                    ledBase: backend.baseConnected
                    ledWheel: backend.wheelConnected
                    ledPedals: backend.pedalsConnected
                }

                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: torqueRow.top
                    anchors.bottomMargin: 16
                    spacing: 0
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: backend.baseConnected ? (backend.angle >= 0 ? "+" : "−") + Math.abs(backend.angle).toFixed(1) + "°" : "—"
                        font.family: Theme.fontDisplay
                        font.pixelSize: 46
                        font.weight: Font.DemiBold
                        color: Theme.text
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "zakres " + (backend.motionRange || "–") + "°"
                        font.pixelSize: 12
                        color: Theme.textDim
                    }
                }

                // moment: pasek od środka
                RowLayout {
                    id: torqueRow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    spacing: 14
                    Text {
                        text: "MOMENT"
                        font.family: Theme.fontDisplay
                        font.pixelSize: 11
                        font.letterSpacing: 1.2
                        color: Theme.textDim
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 10
                        radius: 5
                        color: Theme.bg
                        border.color: Theme.border
                        Rectangle {
                            readonly property real t: Math.max(-1, Math.min(1, backend.torque))
                            x: t < 0 ? parent.width / 2 * (1 + t) : parent.width / 2
                            width: Math.abs(t) * parent.width / 2
                            height: parent.height
                            radius: 5
                            color: Math.abs(t) > 0.9 ? Theme.danger : Theme.accent
                        }
                        Rectangle { x: parent.width / 2 - 1; width: 2; height: parent.height; color: Theme.textFaint }
                    }
                    Text {
                        Layout.preferredWidth: 52
                        horizontalAlignment: Text.AlignRight
                        text: Math.round(backend.torque * 100) + "%"
                        font.family: Theme.fontDisplay
                        font.pixelSize: 16
                        color: Theme.text
                    }
                }
            }
        }

        // ---------- pedały ----------
        Card {
            Layout.fillWidth: true
            Layout.preferredHeight: 520
            title: "Pedały"
            fillBody: true
            subtitle: backend.pedalsConnected ? backend.pedalsName : "Niepodłączone"
            icon: Theme.icPedals

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 20
                Item { Layout.fillWidth: true }
                PedalBar {
                    Layout.fillHeight: true
                    label: "Hamulec"
                    value: backend.brake
                    barColor: Theme.brake
                    active: backend.pedalsConnected
                }
                PedalBar {
                    Layout.fillHeight: true
                    label: "Gaz"
                    value: backend.throttle
                    barColor: Theme.throttle
                    active: backend.pedalsConnected
                }
                Item { Layout.fillWidth: true }
            }
        }

        // ---------- wykres momentu ----------
        Card {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            Layout.preferredHeight: 300
            title: "Moment obrotowy"
            fillBody: true
            subtitle: "Ostatnie ~6 sekund"
            icon: Theme.icChart

            actions: [
                Column {
                    Text {
                        anchors.right: parent.right
                        text: Math.round(backend.peakTorque * 100) + "%"
                        font.family: Theme.fontDisplay
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: backend.peakTorque > 0.9 ? Theme.danger : Theme.text
                    }
                    Text {
                        anchors.right: parent.right
                        text: "szczyt"
                        font.pixelSize: 11
                        color: Theme.textDim
                    }
                }
            ]

            TorqueGraph {
                id: graph
                Layout.fillWidth: true
                Layout.fillHeight: true
                Connections {
                    target: backend
                    function onStateChanged() { graph.push(backend.torque) }
                    function onBaseChanged() { if (!backend.baseConnected) graph.clear() }
                }
            }
        }

        // ---------- szybki tuning ----------
        Card {
            Layout.fillWidth: true
            Layout.preferredHeight: 300
            title: "Szybki tuning"
            icon: Theme.icFfb

            SettingSlider {
                Layout.fillWidth: true
                field: backend.strengthField
                compact: true
            }
            Segmented {
                Layout.fillWidth: true
                label: "Kąt obrotu"
                enabled: backend.baseConnected
                options: [360, 540, 900, 1080].map(v => ({ label: v + "°", value: v }))
                value: backend.motionRange
                onPicked: v => backend.setSetting(backend.rangeField.key, v)
            }
            Item { Layout.fillHeight: true }
        }

        // ---------- przyciski ----------
        Card {
            Layout.columnSpan: 3
            Layout.fillWidth: true
            title: "Przyciski kierownicy"
            subtitle: backend.wheelConnected ? backend.wheelName : "Kierownica niepołączona (Bluetooth)"
            icon: Theme.icWheel

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: 14
                    delegate: Rectangle {
                        required property int index
                        readonly property int button: backend.wheelButtonMap[index]
                        readonly property bool on: (backend.buttons & (1 << button)) !== 0
                        Layout.fillWidth: true
                        implicitHeight: 44
                        radius: 10
                        color: on ? Theme.accent : Theme.surface2
                        border.color: on ? Theme.accent : Theme.border
                        Text {
                            anchors.centerIn: parent
                            text: index < 12 ? (button + 1) : (index === 12 ? "L" : "P")
                            font.family: Theme.fontDisplay
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                            color: parent.on ? "#fff" : Theme.textDim
                        }
                    }
                }
            }
        }
    }

    Item { Layout.preferredHeight: 20 }
}
