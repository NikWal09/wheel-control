import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Ile siły baza może dać w grze i w blokadzie przy obecnych ustawieniach (OpenFFBoard + MotorXDrive).
Card {
    id: root
    readonly property var budget: backend.forceBudget
    readonly property bool available: budget.available === true

    title: "Siła bazy"
    subtitle: "Maksimum przy obecnych ustawieniach – Moc × Udział efektów × Limit prądu"
    icon: Theme.icFfb
    visible: available

    RowLayout {
        Layout.fillWidth: true
        spacing: 24

        Repeater {
            model: root.available ? [
                { label: "Efekty z gry", amps: root.budget.gameA, nm: root.budget.gameNm,
                  note: Math.round(root.budget.gamePercent) + "% limitu prądu" },
                { label: "Blokada kierownicy", amps: root.budget.endstopA, nm: root.budget.endstopNm,
                  note: "pełny limit prądu, niezależnie od Mocy" }
            ] : []
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                spacing: 2
                Text {
                    text: modelData.label
                    font.pixelSize: 13
                    color: Theme.textDim
                }
                RowLayout {
                    spacing: 6
                    Text {
                        text: modelData.amps.toFixed(1)
                        font.family: Theme.fontDisplay
                        font.pixelSize: 30
                        font.weight: Font.DemiBold
                        color: Theme.text
                    }
                    Text {
                        text: "A"
                        font.family: Theme.fontDisplay
                        font.pixelSize: 15
                        color: Theme.textDim
                        Layout.alignment: Qt.AlignBaseline
                    }
                    Text {
                        text: "≈ " + modelData.nm.toFixed(1) + " Nm"
                        font.family: Theme.fontDisplay
                        font.pixelSize: 20
                        color: Theme.accent
                        Layout.leftMargin: 8
                        Layout.alignment: Qt.AlignBaseline
                    }
                }
                Text {
                    text: modelData.note
                    font.pixelSize: 12
                    color: Theme.textFaint
                }
            }
        }
    }

    // udział siły z gry w limicie prądu
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 6
        radius: 3
        color: Theme.track
        Rectangle {
            width: parent.width * Math.min(1, (root.budget.gamePercent || 0) / 100)
            height: parent.height
            radius: 3
            color: Theme.accent
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        Text {
            text: "Stała momentu silnika"
            font.pixelSize: 14
            font.weight: Font.Medium
            color: Theme.text
            Layout.fillWidth: true
        }
        Rectangle {
            implicitWidth: 90
            implicitHeight: 34
            radius: 10
            color: Theme.bg
            border.color: ktInput.activeFocus ? Theme.accent : Theme.border
            TextInput {
                id: ktInput
                anchors.fill: parent
                anchors.margins: 6
                horizontalAlignment: TextInput.AlignHCenter
                verticalAlignment: TextInput.AlignVCenter
                font.family: Theme.fontDisplay
                font.pixelSize: 16
                color: Theme.text
                selectionColor: Theme.accent
                validator: RegularExpressionValidator { regularExpression: /^\d{0,1}([.,]\d{0,3})?$/ }
                onEditingFinished: {
                    const v = parseFloat(text.replace(",", "."))
                    if (v > 0 && Math.abs(v - backend.motorKt) > 0.0005)
                        backend.setMotorKt(v)
                    text = backend.motorKt.toFixed(2)
                    focus = false
                }
                Binding on text {
                    value: backend.motorKt.toFixed(2)
                    when: !ktInput.activeFocus
                    restoreMode: Binding.RestoreNone
                }
            }
        }
        Text {
            text: "Nm/A"
            font.pixelSize: 13
            color: Theme.textDim
        }
    }

    Text {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        font.pixelSize: 12
        lineHeight: 1.15
        color: Theme.textDim
        text: "Nm to szacunek: prąd × stała momentu. Zmierz ją wagą bagażową: przeciągnij kierownicę za blokadę, "
            + "odczytaj siłę na obręczy i policz kg × 9,81 × promień [m] / Limit prądu [A]. Siłę w grze zwiększysz "
            + "Mocą i Udziałem efektów; wyższy Limit prądu wzmacnia też blokadę."
    }
}
