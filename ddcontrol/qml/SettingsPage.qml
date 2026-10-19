import QtQuick
import QtQuick.Layouts

PageBase {
    id: page

    GridLayout {
        Layout.fillWidth: true
        columns: page.wide ? 2 : 1
        columnSpacing: Theme.gap
        rowSpacing: Theme.gap

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Tryb demo"
            subtitle: "Symulowana baza, pedały i kierownica"
            icon: Theme.icDiag

            ToggleRow {
                Layout.fillWidth: true
                label: "Symulacja sprzętu"
                description: "Aplikacja działa bez podłączonej bazy – przydatne do prezentacji i nauki interfejsu. "
                    + "Zmiany trafiają do wirtualnej bazy, nie do prawdziwej."
                checked: backend.simulation
                onToggled: c => backend.setSimulation(c)
            }
            Segmented {
                Layout.fillWidth: true
                label: "Firmware symulowanej bazy"
                options: [{ label: "FFBeast", value: "ffbeast" }, { label: "OpenFFBoard", value: "openffboard" }]
                value: backend.demoFirmware
                onPicked: v => backend.setDemoFirmware(v)
                description: "Bez symulacji aplikacja sama wykrywa, który firmware jest podłączony."
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Wygląd"
            subtitle: "Kolor akcentu interfejsu"
            icon: Theme.icSettings

            Flow {
                Layout.fillWidth: true
                spacing: 12
                Repeater {
                    model: ["#FF4D2E", "#E10600", "#FF2D7A", "#7C5CFF", "#3DA5FF", "#00C2B8", "#2ED47A", "#FFB020"]
                    delegate: Rectangle {
                        required property string modelData
                        readonly property bool current: Qt.colorEqual(Theme.accent, modelData)
                        width: 44; height: 44; radius: 22
                        color: "transparent"
                        border.color: current ? Theme.text : "transparent"
                        border.width: 2
                        Rectangle {
                            anchors.centerIn: parent
                            width: 32; height: 32; radius: 16
                            color: parent.modelData
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: backend.setAccent(parent.modelData)
                        }
                    }
                }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        title: "O aplikacji"
        icon: Theme.icInfo

        Text {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            textFormat: Text.StyledText
            font.pixelSize: 13
            lineHeight: 1.3
            color: Theme.textDim
            text: "<b style='color:#F2F4F7'>DD Control " + appVersion + "</b> – oprogramowanie do zestawu DIY Direct Drive "
                + "(Politechnika Poznańska).<br>"
                + "<b style='color:#F2F4F7'>OpenFFBoard</b> (MKS XDrive Mini z MotorXDrive): wirtualny port COM, "
                + "USB 1209:FFB0, komendy tekstowe <i>klasa.instancja.komenda</i>. Windows pozwala otworzyć "
                + "port COM tylko jednemu programowi – zamknij OpenFFBoard Configurator przed użyciem DD Control "
                + "(i odwrotnie).<br>"
                + "<b style='color:#F2F4F7'>FFBeast</b>: USB HID 1115:22999, interfejs vendor.<br>"
                + "Ustawienia zmieniane są na żywo; <i>Zapisz w bazie</i> utrwala je w pamięci flash. "
                + "Pedały i kierownica są odczytywane jako standardowe kontrolery gier Windows.<br>"
                + "Profile i konfiguracja: %APPDATA%\\DDControl."
        }
    }

    Item { Layout.preferredHeight: 20 }
}
