import QtQuick
import QtQuick.Shapes

// Wektorowa grafika kierownicy DIY (kształt formułowy, 12 przycisków + 2 łopatki).
// Rysowana w układzie 440x280 i skalowana do rozmiaru elementu.
Item {
    id: root
    property real wheelRotation: 0
    property bool showButtons: true
    property bool interactive: false
    property int pressedMask: 0
    property var buttonMap: []          // slot -> indeks przycisku
    property int highlightSlot: -1      // slot w trakcie uczenia
    property bool ledBase: false
    property bool ledWheel: false
    property bool ledPedals: false
    signal slotClicked(int slot)

    // Pozycje 12 przycisków panelu (lewa strona + lustrzane odbicie) i 2 łopatek.
    readonly property var slotPositions: {
        const left = [[64, 58], [112, 47], [140, 98], [140, 137], [140, 176], [140, 215]]
        let all = left.map(p => p)
        for (const p of left)
            all.push([440 - p[0], p[1]])
        return all
    }

    implicitWidth: 440
    implicitHeight: 280

    function isPressed(slot) {
        const idx = buttonMap.length > slot ? buttonMap[slot] : slot
        return (pressedMask & (1 << idx)) !== 0
    }

    Item {
        id: canvas
        width: 440
        height: 280
        anchors.centerIn: parent
        scale: Math.min(root.width / 440, root.height / 280)
        rotation: root.wheelRotation

        // Łopatki (za kierownicą)
        Repeater {
            model: 2
            delegate: Rectangle {
                required property int index
                readonly property int slot: 12 + index
                readonly property bool on: root.showButtons && root.isPressed(slot)
                x: index === 0 ? -30 : 426
                y: 104
                width: 44; height: 92; radius: 12
                color: on ? Theme.accent : "#262B33"
                border.color: slot === root.highlightSlot ? Theme.text : "#3A414C"
                border.width: slot === root.highlightSlot ? 2 : 1
                Text {
                    visible: root.showButtons
                    anchors.verticalCenter: parent.verticalCenter
                    x: index === 0 ? 6 : parent.width - width - 6
                    text: index === 0 ? "L" : "P"
                    font.family: Theme.fontDisplay
                    font.pixelSize: 13
                    color: parent.on ? "#fff" : Theme.textDim
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: root.interactive
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.slotClicked(parent.slot)
                }
            }
        }

        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                fillRule: ShapePath.OddEvenFill
                strokeColor: "#3A404B"
                strokeWidth: 1.5
                fillGradient: LinearGradient {
                    x1: 0; y1: 0; x2: 0; y2: 280
                    GradientStop { position: 0; color: "#22262E" }
                    GradientStop { position: 1; color: "#111317" }
                }
                PathSvg {
                    path: "M 30 58 Q 30 34 56 30 L 150 22 Q 168 20 178 34 L 196 62 Q 220 84 244 62 "
                        + "L 262 34 Q 272 20 290 22 L 384 30 Q 410 34 410 58 L 418 120 "
                        + "Q 428 200 404 246 Q 392 266 366 262 L 300 250 Q 220 262 140 250 "
                        + "L 74 262 Q 48 266 36 246 Q 12 200 22 120 Z "
                        // otwory uchwytów
                        + "M 52 94 Q 52 84 64 84 L 92 86 Q 102 87 102 98 L 104 200 "
                        + "Q 104 214 92 216 L 70 220 Q 56 222 55 208 Z "
                        + "M 388 94 Q 388 84 376 84 L 348 86 Q 338 87 338 98 L 336 200 "
                        + "Q 336 214 348 216 L 370 220 Q 384 222 385 208 Z"
                }
            }
            // jasna krawędź płyty czołowej, jak na prawdziwej kierownicy
            ShapePath {
                fillColor: "transparent"
                strokeColor: Qt.rgba(1, 1, 1, 0.22)
                strokeWidth: 2
                PathSvg {
                    path: "M 38 60 Q 40 40 60 38 L 150 30 Q 164 29 172 40 L 192 70 "
                        + "Q 220 94 248 70 L 268 40 Q 276 29 290 30 L 380 38 Q 400 40 402 60"
                }
            }
            // znacznik środka (12:00)
            ShapePath {
                fillColor: Theme.accent
                strokeColor: "transparent"
                PathSvg { path: "M 212 76 L 228 76 L 226 88 L 214 88 Z" }
            }
        }

        // piasta
        Rectangle {
            x: 220 - 34; y: 150 - 34
            width: 68; height: 68; radius: 34
            color: "#15181D"
            border.color: "#2E333C"
            Repeater {
                model: 6
                delegate: Rectangle {
                    required property int index
                    readonly property real a: index * Math.PI / 3
                    x: 34 + 22 * Math.cos(a) - 3
                    y: 34 + 22 * Math.sin(a) - 3
                    width: 6; height: 6; radius: 3
                    color: "#3A404B"
                }
            }
            Text {
                anchors.centerIn: parent
                text: "DD"
                font.family: Theme.fontDisplay
                font.pixelSize: 15
                font.weight: Font.Bold
                color: Theme.textFaint
            }
        }

        // diody statusu (baza / kierownica / pedały)
        Row {
            x: 220 - width / 2
            y: 230
            spacing: 10
            Repeater {
                model: [
                    { on: root.ledBase, c: "#2ED47A" },
                    { on: root.ledWheel, c: "#3DA5FF" },
                    { on: root.ledPedals, c: "#F2F4F7" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: 9; height: 9; radius: 4.5
                    color: modelData.on ? modelData.c : "#2A2F37"
                    Rectangle {
                        visible: modelData.on
                        anchors.centerIn: parent
                        width: 20; height: 20; radius: 10
                        color: modelData.c
                        opacity: 0.18
                    }
                }
            }
        }

        // przyciski panelu
        Repeater {
            model: root.showButtons ? 12 : 0
            delegate: Item {
                id: btn
                required property int index
                readonly property bool on: root.isPressed(index)
                readonly property bool learning: index === root.highlightSlot
                x: root.slotPositions[index][0] - 13
                y: root.slotPositions[index][1] - 13
                width: 26; height: 26

                Rectangle {
                    anchors.centerIn: parent
                    width: 34; height: 34; radius: 17
                    color: Theme.accent
                    opacity: btn.on ? 0.3 : 0
                    Behavior on opacity { NumberAnimation { duration: 80 } }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 13
                    gradient: Gradient {
                        GradientStop { position: 0; color: btn.on ? Qt.lighter(Theme.accent, 1.2) : "#3A3F48" }
                        GradientStop { position: 1; color: btn.on ? Theme.accent : "#1B1E24" }
                    }
                    border.color: btn.learning ? Theme.text : "#0C0D10"
                    border.width: btn.learning ? 2 : 1
                    SequentialAnimation on opacity {
                        running: btn.learning
                        loops: Animation.Infinite
                        alwaysRunToEnd: true
                        NumberAnimation { to: 0.35; duration: 400 }
                        NumberAnimation { to: 1; duration: 400 }
                    }
                }
                Text {
                    anchors.centerIn: parent
                    text: (root.buttonMap.length > index ? root.buttonMap[index] : index) + 1
                    font.family: Theme.fontDisplay
                    font.pixelSize: 10
                    color: btn.on ? "#fff" : Theme.textDim
                    rotation: -root.wheelRotation
                }
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    enabled: root.interactive
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.slotClicked(index)
                }
            }
        }
    }
}
