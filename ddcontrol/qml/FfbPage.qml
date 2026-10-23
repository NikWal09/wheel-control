import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

PageBase {
    id: page

    NoBaseBanner {}

    ForceBudgetCard {
        Layout.fillWidth: true
    }

    SchemaCards {
        page: "ffb"
        wide: page.wide
    }

    RowLayout {
        id: ffbActions
        readonly property var defaultsAction: backend.actions.find(a => a.id === "defaults")
        visible: defaultsAction !== undefined
        spacing: 10
        AppButton {
            text: "Zapisz w bazie"
            glyph: Theme.icSave
            variant: "primary"
            enabled: backend.baseConnected
            onClicked: backend.saveToBase()
        }
        AppButton {
            text: ffbActions.defaultsAction ? ffbActions.defaultsAction.label : ""
            glyph: Theme.icon("sync")
            enabled: backend.baseConnected
            onClicked: {
                const a = ffbActions.defaultsAction
                ApplicationWindow.window.confirm(a.confirmTitle, a.confirmText, a.confirmLabel, false,
                                                 () => backend.runAction(a.id))
            }
        }
    }

    Item { Layout.preferredHeight: 20 }
}
