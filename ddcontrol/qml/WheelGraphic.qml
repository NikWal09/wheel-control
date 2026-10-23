import QtQuick
import QtQuick.Controls.Basic

// Kierownica DIY: rzut z modelu STL (assets/wheel_front.png, tools/render_wheel.py) + przyciski w miejscach
// otworów, łopatki wystające po bokach, diody w module na dole. Układ 620x315 (2 jednostki = 1 mm).
Item {
    id: root
    property real wheelRotation: 0
    property bool showButtons: true
    property bool interactive: false
    property int pressedMask: 0
    property var buttonMap: []          // slot -> indeks przycisku
    property int highlightSlot: -1      // slot w trakcie uczenia
    // diody na kierownicy: zasilanie, Bluetooth (mruga = szuka), ładowanie (-1 = brak danych)
    property bool wheelConnected: false
    property int charging: -1
    signal slotClicked(int slot)

    readonly property real canvasWidth: 620
    readonly property real canvasHeight: 315
    readonly property real aspect: canvasWidth / canvasHeight
    // najdalszy punkt (narożnik łopatki) od środka / szerokość - obrócona kierownica mieści się w kole o tym promieniu
    readonly property real boundRatio: 0.515
    readonly property real imageX: 24   // obraz kierownicy jest węższy o miejsce na łopatki
    // środki otworów Ø12 mm z modelu: lewa kolumna od góry (sloty 0-5), prawa od góry (6-11)
    readonly property var slotPositions: [[89, 33], [138, 46], [164, 89], [174, 153], [171, 215], [167, 265],
                                          [482, 33], [434, 46], [408, 89], [398, 153], [400, 215], [404, 265]]
                                         .map(p => [p[0] + imageX, p[1]])
    readonly property var ledPositions: [[261, 293], [286, 293], [311, 293]].map(p => [p[0] + imageX, p[1]])

    implicitWidth: canvasWidth
    implicitHeight: canvasHeight

    function isPressed(slot) {
        const idx = buttonMap.length > slot ? buttonMap[slot] : slot
        return (pressedMask & (1 << idx)) !== 0
    }

    Item {
        id: canvas
        width: root.canvasWidth
        height: root.canvasHeight
        anchors.centerIn: parent
        scale: Math.min(root.width / root.canvasWidth, root.height / root.canvasHeight)
        rotation: root.wheelRotation

        // łopatki za kierownicą - wystają po bokach
        Repeater {
            model: 2
            delegate: Rectangle {
                id: paddle
                required property int index
                readonly property int slot: 12 + index
                readonly property bool on: root.showButtons && root.isPressed(slot)
                readonly property bool learning: slot === root.highlightSlot
                x: index === 0 ? 0 : root.canvasWidth - width
                y: root.canvasHeight / 2 - height / 2
                width: 46; height: 116; radius: 12
                color: on ? Theme.accent : "#262B33"
                border.color: learning ? Theme.text : "#3A414C"
                border.width: learning ? 2 : 1
                Text {
                    visible: root.showButtons
                    anchors.verticalCenter: parent.verticalCenter
                    x: paddle.index === 0 ? 6 : parent.width - width - 6
                    text: paddle.index === 0 ? "L" : "P"
                    font.family: Theme.fontDisplay
                    font.pixelSize: 13
                    color: paddle.on ? "#fff" : Theme.textDim
                    rotation: -root.wheelRotation
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: root.interactive
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.slotClicked(paddle.slot)
                }
            }
        }

        Image {
            x: root.imageX
            width: root.canvasWidth - 2 * root.imageX
            height: root.canvasHeight
            source: "../assets/wheel_front.png"
            smooth: true
            mipmap: true
        }

        // diody w module na dole: zasilanie, Bluetooth, ładowanie (kolory jak na kierownicy)
        Repeater {
            model: [
                { name: "Zasilanie", c: "#B9F5CB",
                  state: root.wheelConnected ? "on" : "off",
                  tip: root.wheelConnected ? "Kierownica włączona" : "Kierownica wyłączona albo nie wiadomo (brak połączenia)" },
                { name: "Bluetooth", c: "#3D7BFF",
                  state: root.wheelConnected ? "on" : "blink",
                  tip: root.wheelConnected ? "Połączona przez Bluetooth – świeci ciągle"
                                           : "Nie połączona – włączona kierownica mruga i szuka Bluetooth" },
                { name: "Ładowanie", c: "#E9F2FF",
                  state: root.charging === 1 ? "on" : root.charging === 0 ? "off" : "unknown",
                  tip: root.charging === 1 ? "Ładuje się" : root.charging === 0 ? "Nie ładuje się"
                     : "Kontroler nie wysyła stanu ładowania – sprawdź diodę na kierownicy" }
            ]
            delegate: Item {
                id: led
                required property var modelData
                required property int index
                readonly property bool lit: modelData.state === "on" || (modelData.state === "blink" && blink.lit)
                x: root.ledPositions[index][0] - 6
                y: root.ledPositions[index][1] - 6
                width: 12; height: 12
                Rectangle {
                    anchors.centerIn: parent
                    width: 30; height: 30; radius: 15
                    color: led.modelData.c
                    opacity: led.lit ? 0.25 : 0
                    Behavior on opacity { NumberAnimation { duration: 120 } }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: width / 2
                    color: led.lit ? led.modelData.c : "#2A2D33"
                    border.color: led.lit ? Qt.lighter(led.modelData.c, 1.2) : "#4A4F58"
                    Behavior on color { ColorAnimation { duration: 120 } }
                }
                MouseArea {
                    id: ledMouse
                    anchors.fill: parent
                    anchors.margins: -6
                    enabled: root.interactive
                    hoverEnabled: true
                }
                ToolTip.visible: ledMouse.containsMouse
                ToolTip.text: led.modelData.name + ": " + led.modelData.tip
            }
        }

        // przyciski: kopułka z kołnierzem jak na kierownicy
        Repeater {
            model: root.showButtons ? 12 : 0
            delegate: Item {
                id: btn
                required property int index
                readonly property bool on: root.isPressed(index)
                readonly property bool learning: index === root.highlightSlot
                x: root.slotPositions[index][0] - 16
                y: root.slotPositions[index][1] - 16
                width: 32; height: 32

                Rectangle {   // poświata naciśnięcia
                    anchors.centerIn: parent
                    width: 46; height: 46; radius: 23
                    color: Theme.accent
                    opacity: btn.on ? 0.35 : 0
                    Behavior on opacity { NumberAnimation { duration: 80 } }
                }
                Rectangle {   // kołnierz
                    anchors.fill: parent
                    radius: width / 2
                    color: "#16181C"
                    border.color: btn.learning ? Theme.text : "#5A606B"
                    border.width: btn.learning ? 2.5 : 1.2
                    SequentialAnimation on opacity {
                        running: btn.learning
                        loops: Animation.Infinite
                        alwaysRunToEnd: true
                        NumberAnimation { to: 0.35; duration: 400 }
                        NumberAnimation { to: 1; duration: 400 }
                    }
                }
                Rectangle {   // kopułka
                    anchors.centerIn: parent
                    width: 22; height: 22; radius: 11
                    gradient: Gradient {
                        GradientStop { position: 0; color: btn.on ? Qt.lighter(Theme.accent, 1.25) : "#4A4E57" }
                        GradientStop { position: 0.55; color: btn.on ? Theme.accent : "#24272D" }
                        GradientStop { position: 1; color: btn.on ? Qt.darker(Theme.accent, 1.3) : "#141519" }
                    }
                    border.color: "#0A0B0D"
                    Rectangle {   // odblask
                        x: 5; y: 3
                        width: 9; height: 5; radius: 2.5
                        color: Qt.rgba(1, 1, 1, btn.on ? 0.35 : 0.18)
                    }
                }
                Text {
                    anchors.centerIn: parent
                    text: (root.buttonMap.length > btn.index ? root.buttonMap[btn.index] : btn.index) + 1
                    font.family: Theme.fontDisplay
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    color: btn.on ? "#fff" : "#B8BEC8"
                    rotation: -root.wheelRotation
                }
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -3
                    enabled: root.interactive
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.slotClicked(btn.index)
                }
            }
        }
    }

    // mruganie diody Bluetooth jak na kierownicy, gdy szuka połączenia
    Timer {
        id: blink
        property bool lit: true
        interval: 500
        repeat: true
        running: !root.wheelConnected
        onTriggered: lit = !lit
        onRunningChanged: lit = true
    }
}
