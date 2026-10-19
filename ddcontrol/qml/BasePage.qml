import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

PageBase {
    id: page

    NoBaseBanner {}

    Banner {
        visible: backend.baseConnected
        kind: "warning"
        title: "Ustawienia zaawansowane"
        text: "Błędne pary biegunów, kierunek enkodera albo uruchomienie kalibracji / testu mogą spowodować "
            + "gwałtowny ruch kierownicy. Zmieniaj pojedynczo, trzymając ręce z dala od kierownicy, "
            + "i zapisuj dopiero po sprawdzeniu."
    }

    SchemaCards {
        page: "base"
        wide: page.wide
    }

    Card {
        Layout.fillWidth: true
        title: "Urządzenie"
        subtitle: backend.controllerName
        icon: Theme.icInfo

        GridLayout {
            Layout.fillWidth: true
            columns: page.wide ? 5 : 2
            columnSpacing: 32
            rowSpacing: 14

            Repeater {
                model: backend.deviceDetails
                delegate: ColumnLayout {
                    required property var modelData
                    spacing: 2
                    Layout.fillWidth: true
                    Text {
                        text: modelData.k.toUpperCase()
                        font.family: Theme.fontDisplay
                        font.pixelSize: 11
                        font.letterSpacing: 1.2
                        color: Theme.textFaint
                    }
                    Text {
                        text: modelData.v
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        color: Theme.text
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: 10
            AppButton {
                text: "Zapisz w bazie"
                glyph: Theme.icSave
                variant: "primary"
                enabled: backend.baseConnected
                onClicked: backend.saveToBase()
            }
            AppButton {
                text: "Odczytaj z bazy"
                glyph: Theme.icRefresh
                enabled: backend.baseConnected
                onClicked: backend.reloadSettings()
            }
            Repeater {
                model: backend.actions
                delegate: AppButton {
                    required property var modelData
                    text: modelData.label
                    glyph: Theme.icon(modelData.icon)
                    variant: modelData.variant
                    enabled: backend.baseConnected
                    onClicked: {
                        const id = modelData.id
                        if (modelData.confirmTitle)
                            ApplicationWindow.window.confirm(modelData.confirmTitle, modelData.confirmText,
                                                             modelData.confirmLabel, modelData.danger,
                                                             () => backend.runAction(id))
                        else
                            backend.runAction(id)
                    }
                }
            }
        }
    }

    Item { Layout.preferredHeight: 20 }
}
