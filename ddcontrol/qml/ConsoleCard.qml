import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Konsola komend OpenFFBoard - diagnostyka bez OpenFFBoard Configuratora.
Card {
    id: root
    title: "Konsola OpenFFBoard"
    subtitle: backend.canConsole ? "Komendy jak w Configuratorze, np. xdrive.0.state? lub axis.0.drvtype!"
                                 : "Dostępna po połączeniu z płytką OpenFFBoard"
    icon: Theme.icDiag

    actions: [
        AppButton {
            text: "Wyczyść"
            variant: "ghost"
            onClicked: backend.clearConsole()
        }
    ]

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 220
        radius: 10
        color: Theme.bg
        border.color: Theme.border
        ListView {
            id: log
            anchors.fill: parent
            anchors.margins: 10
            clip: true
            model: backend.consoleLog
            onCountChanged: positionViewAtEnd()
            delegate: Text {
                required property string modelData
                width: log.width
                text: modelData
                wrapMode: Text.WrapAnywhere
                font.family: "Consolas"
                font.pixelSize: 12
                color: modelData.startsWith(">") ? Theme.accent : Theme.textDim
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        TextField {
            id: input
            Layout.fillWidth: true
            enabled: backend.canConsole
            placeholderText: "np. sys.0.lsactive?   (kilka komend rozdziel ;)"
            placeholderTextColor: Theme.textFaint
            color: Theme.text
            font.family: "Consolas"
            font.pixelSize: 13
            leftPadding: 12
            implicitHeight: 38
            selectionColor: Theme.accent
            background: Rectangle {
                radius: 10
                color: Theme.bg
                border.color: input.activeFocus ? Theme.accent : Theme.border
            }
            onAccepted: send.clicked()
        }
        AppButton {
            id: send
            text: "Wyślij"
            variant: "primary"
            enabled: backend.canConsole && input.text.trim() !== ""
            onClicked: {
                backend.sendConsole(input.text)
                input.text = ""
            }
        }
    }
}
