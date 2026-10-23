import QtQuick
import QtQuick.Controls.Basic

// Kierownica DIY: rzut z modelu STL (assets/wheel_front.png, tools/render_wheel.py) + przyciski w miejscach
// otworów. Układ 620x315 (2 jednostki = 1 mm), skalowany do rozmiaru elementu.
// Numeracja pozycji w kształcie U: lewa góra 1 -> w dół 6, prawa strona od dołu 7 -> prawa góra 12,
// łopatki 13 (lewa) i 14 (prawa). buttonMap mówi, który przycisk kontrolera (HID) leży na danej pozycji.
Item {
    id: root
    property real wheelRotation: 0
    property bool showButtons: true
    property bool interactive: false
    property int pressedMask: 0
    property var buttonMap: []          // slot -> indeks przycisku kontrolera
    property int highlightSlot: -1      // slot w trakcie uczenia
    // diody na kierownicy: zasilanie, Bluetooth (mruga = szuka), ładowanie (-1 = brak danych)
    property bool wheelConnected: false
    property int charging: -1
    signal slotClicked(int slot)

    readonly property real canvasWidth: 620
    readonly property real canvasHeight: 315
    readonly property real aspect: canvasWidth / canvasHeight
    readonly property real imageX: 24   // miejsce na łopatki po bokach
    // środki otworów Ø12 mm z modelu (tools/render_wheel.py), kolejność U
    readonly property var slotPositions: [[89, 33], [138, 46], [164, 89], [174, 153], [171, 215], [167, 265],
                                          [404, 265], [400, 215], [398, 153], [408, 89], [434, 46], [482, 33]]
                                         .map(p => [p[0] + imageX, p[1]])

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

        // łopatki (za kierownicą)
        Repeater {
            model: 2
            delegate: Rectangle {
                required property int index
                readonly property int slot: 12 + index
                readonly property bool on: root.showButtons && root.isPressed(slot)
                x: index === 0 ? 0 : root.canvasWidth - width
                y: 100
                width: 46; height: 116; radius: 14
                color: on ? Theme.accent : "#22262D"
                border.color: slot === root.highlightSlot ? Theme.text : "#3A414C"
                border.width: slot === root.highlightSlot ? 2 : 1
                Text {
                    visible: root.showButtons
                    anchors.verticalCenter: parent.verticalCenter
                    x: index === 0 ? 5 : parent.width - width - 5
                    text: parent.slot + 1
                    font.family: Theme.fontDisplay
                    font.pixelSize: 13
                    color: parent.on ? "#fff" : Theme.textDim
                    rotation: -root.wheelRotation
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: root.interactive
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.slotClicked(parent.slot)
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

        // znacznik środka (12:00)
        Rectangle {
            x: root.canvasWidth / 2 - 9
            y: 78
            width: 18; height: 6; radius: 3
            color: Theme.accent
        }

        // diody statusu kierownicy
        Row {
            x: root.canvasWidth / 2 - width / 2
            y: 284
            spacing: 14
            Repeater {
                model: [
                    { name: "Zasilanie", c: Theme.success,
                      state: root.wheelConnected ? "on" : "off",
                      tip: root.wheelConnected ? "Kierownica włączona" : "Kierownica wyłączona albo nie wiadomo (brak połączenia)" },
                    { name: "Bluetooth", c: Theme.info,
                      state: root.wheelConnected ? "on" : "blink",
                      tip: root.wheelConnected ? "Połączona przez Bluetooth – świeci ciągle"
                                               : "Nie połączona – włączona kierownica mruga i szuka Bluetooth" },
                    { name: "Ładowanie", c: Theme.warning,
                      state: root.charging === 1 ? "on" : root.charging === 0 ? "off" : "unknown",
                      tip: root.charging === 1 ? "Ładuje się" : root.charging === 0 ? "Nie ładuje się"
                         : "Kontroler nie wysyła stanu ładowania – sprawdź diodę na kierownicy" }
                ]
                delegate: Item {
                    id: led
                    required property var modelData
                    readonly property bool lit: modelData.state === "on" || (modelData.state === "blink" && blink.lit)
                    width: 11; height: 11
                    Rectangle {
                        anchors.centerIn: parent
                        width: 24; height: 24; radius: 12
                        color: led.modelData.c
                        opacity: led.lit ? 0.22 : 0
                        Behavior on opacity { NumberAnimation { duration: 120 } }
                    }
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: led.lit ? led.modelData.c : "#1E2228"
                        border.color: led.modelData.state === "unknown" ? Theme.textFaint : "#0C0D10"
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
        }

        // przyciski panelu
        Repeater {
            model: root.showButtons ? 12 : 0
            delegate: Item {
                id: btn
                required property int index
                readonly property bool on: root.isPressed(index)
                readonly property bool learning: index === root.highlightSlot
                x: root.slotPositions[index][0] - 11
                y: root.slotPositions[index][1] - 11
                width: 22; height: 22

                Rectangle {
                    anchors.centerIn: parent
                    width: 32; height: 32; radius: 16
                    color: Theme.accent
                    opacity: btn.on ? 0.35 : 0
                    Behavior on opacity { NumberAnimation { duration: 80 } }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 11
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
                    text: btn.index + 1
                    font.family: Theme.fontDisplay
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    color: btn.on ? "#fff" : Theme.textDim
                    rotation: -root.wheelRotation
                }
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
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
