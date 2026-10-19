import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts

PageBase {
    id: page
    property string selected: backend.activeProfile || (backend.profiles.length ? backend.profiles[0].name : "")
    readonly property var profile: backend.profiles.find(p => p.name === selected) || null

    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        Text {
            text: backend.profiles.length + " profili dla firmware'u " + backend.firmwareName
            font.pixelSize: 13
            color: Theme.textDim
            Layout.fillWidth: true
        }
        AppButton {
            text: "Importuj z pliku"
            glyph: Theme.icImport
            onClicked: importDialog.open()
        }
        AppButton {
            text: "Zapisz bieżące jako profil"
            glyph: Theme.icAdd
            variant: "primary"
            enabled: backend.baseConnected
            onClicked: {
                nameField.text = backend.activeProfile && !page.profile?.builtin ? backend.activeProfile : ""
                gameField.text = ""
                savePopup.open()
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.gap

        // ----- lista -----
        ColumnLayout {
            // stała szerokość listy - bez tego wypełniające dzieci rozpychają ją na całą stronę
            Layout.fillWidth: false
            Layout.preferredWidth: page.wide ? 360 : 300
            Layout.maximumWidth: Layout.preferredWidth
            Layout.alignment: Qt.AlignTop
            spacing: 10

            Repeater {
                model: backend.profiles
                delegate: Rectangle {
                    id: item
                    required property var modelData
                    readonly property bool isSelected: modelData.name === page.selected
                    readonly property bool isActive: modelData.name === backend.activeProfile
                    Layout.fillWidth: true
                    implicitHeight: 66
                    radius: 12
                    color: isSelected ? Theme.surface2 : (ma.containsMouse ? Theme.surface : Theme.surface)
                    border.color: isSelected ? Theme.accent : Theme.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 14
                        spacing: 12
                        Rectangle {
                            width: 36; height: 36; radius: 10
                            color: item.isActive ? Theme.accent : Theme.surface3
                            Text {
                                anchors.centerIn: parent
                                text: item.modelData.name.substring(0, 2).toUpperCase()
                                font.family: Theme.fontDisplay
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                color: item.isActive ? "#fff" : Theme.textDim
                            }
                        }
                        ColumnLayout {
                            spacing: 1
                            Layout.fillWidth: true
                            Text {
                                text: item.modelData.name
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                color: Theme.text
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: item.modelData.game + (item.modelData.builtin ? " · wbudowany" : " · własny")
                                font.pixelSize: 12
                                color: Theme.textDim
                            }
                        }
                        Rectangle {
                            visible: item.isActive
                            implicitWidth: activeLabel.implicitWidth + 16
                            implicitHeight: 22
                            radius: 11
                            color: Theme.accentSoft
                            Text {
                                id: activeLabel
                                anchors.centerIn: parent
                                text: backend.profileModified ? "AKTYWNY *" : "AKTYWNY"
                                font.family: Theme.fontDisplay
                                font.pixelSize: 10
                                font.letterSpacing: 1
                                color: Theme.accent
                            }
                        }
                    }
                    MouseArea {
                        id: ma
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: page.selected = item.modelData.name
                        onDoubleClicked: backend.applyProfile(item.modelData.name)
                    }
                }
            }
        }

        // ----- szczegóły -----
        Card {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            visible: page.profile !== null
            title: page.profile ? page.profile.name : ""
            subtitle: page.profile ? (page.profile.game + (page.profile.builtin
                       ? " · profil wbudowany – punkt startowy do własnego strojenia" : " · profil własny")) : ""
            icon: Theme.icProfiles

            Text {
                visible: backend.baseConnected
                text: "Wartości różniące się od bieżących ustawień bazy są podświetlone."
                font.pixelSize: 12
                color: Theme.textDim
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 28
                rowSpacing: 0

                Repeater {
                    model: backend.profileKeys
                    delegate: Rectangle {
                        required property string modelData
                        readonly property var field: backend.fieldMap[modelData]
                        readonly property var value: page.profile ? page.profile.settings[modelData] : undefined
                        readonly property var current: backend.settings[modelData]
                        readonly property bool differs: backend.baseConnected && value !== undefined && current !== value
                        Layout.fillWidth: true
                        implicitHeight: 42
                        color: "transparent"
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
                        RowLayout {
                            anchors.fill: parent
                            spacing: 8
                            Text {
                                text: parent.parent.field ? parent.parent.field.label : modelData
                                font.pixelSize: 13
                                color: Theme.textDim
                                Layout.fillWidth: true
                            }
                            Text {
                                visible: parent.parent.differs
                                text: Theme.formatField(parent.parent.field, parent.parent.current) + "  →"
                                font.pixelSize: 12
                                color: Theme.textFaint
                            }
                            Text {
                                text: Theme.formatField(parent.parent.field, parent.parent.value)
                                font.family: Theme.fontDisplay
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                                color: parent.parent.differs ? Theme.accent : Theme.text
                            }
                        }
                    }
                }
            }

            RowLayout {
                spacing: 10
                AppButton {
                    text: "Zastosuj"
                    glyph: Theme.icCheck
                    variant: "primary"
                    enabled: backend.baseConnected
                    onClicked: backend.applyProfile(page.selected)
                }
                AppButton {
                    text: "Eksportuj"
                    glyph: Theme.icExport
                    onClicked: {
                        exportDialog.selectedFile = "file:///" + page.selected.replace(/[\\/:*?"<>|]/g, "_") + ".ddprofile.json"
                        exportDialog.open()
                    }
                }
                AppButton {
                    visible: page.profile && !page.profile.builtin
                    text: "Usuń"
                    glyph: Theme.icDelete
                    variant: "danger"
                    onClicked: ApplicationWindow.window.confirm(
                        "Usunąć profil?", "Profil „" + page.selected + "” zostanie trwale usunięty.",
                        "Usuń", true, () => { backend.deleteProfile(page.selected); page.selected = "" })
                }
            }
            Text {
                visible: !backend.baseConnected
                text: "Podłącz bazę, aby zastosować profil."
                font.pixelSize: 12
                color: Theme.textDim
            }
        }
    }

    Item { Layout.preferredHeight: 20 }

    FileDialog {
        id: exportDialog
        title: "Eksportuj profil"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Profil DD Control (*.json)"]
        onAccepted: backend.exportProfile(page.selected, selectedFile)
    }
    FileDialog {
        id: importDialog
        title: "Importuj profil"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Profil DD Control (*.json)"]
        onAccepted: backend.importProfile(selectedFile)
    }

    Popup {
        id: savePopup
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: 420
        modal: true
        padding: 26
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.6) }
        background: Rectangle { radius: 16; color: Theme.surface; border.color: Theme.border }
        onOpened: nameField.forceActiveFocus()

        contentItem: ColumnLayout {
            spacing: 12
            Text {
                text: "Zapisz profil"
                font.family: Theme.fontDisplay
                font.pixelSize: 20
                font.weight: Font.DemiBold
                color: Theme.text
            }
            Text {
                text: "Zapisuje bieżące ustawienia Force Feedback (bez parametrów silnika)."
                wrapMode: Text.WordWrap
                font.pixelSize: 12
                color: Theme.textDim
                Layout.fillWidth: true
            }
            InputField { id: nameField; placeholder: "Nazwa profilu, np. ACC – GT3"; Layout.fillWidth: true }
            InputField { id: gameField; placeholder: "Gra (opcjonalnie)"; Layout.fillWidth: true }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Layout.topMargin: 6
                spacing: 10
                AppButton { text: "Anuluj"; variant: "ghost"; onClicked: savePopup.close() }
                AppButton {
                    text: "Zapisz"
                    variant: "primary"
                    enabled: nameField.text.trim() !== ""
                    onClicked: {
                        backend.saveProfile(nameField.text, gameField.text)
                        page.selected = nameField.text.trim()
                        savePopup.close()
                    }
                }
            }
        }
    }

    component InputField: TextField {
        property string placeholder
        placeholderText: placeholder
        placeholderTextColor: Theme.textFaint
        color: Theme.text
        font.pixelSize: 14
        leftPadding: 14
        implicitHeight: 42
        selectionColor: Theme.accent
        background: Rectangle {
            radius: 10
            color: Theme.bg
            border.color: parent.activeFocus ? Theme.accent : Theme.border
        }
    }
}
