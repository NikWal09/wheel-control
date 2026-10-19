import QtQuick
import QtQuick.Layouts

// Kafelki ustawień dla jednej strony ("ffb" / "base"), zbudowane z opisu firmware'u.
GridLayout {
    id: root
    property string page
    property bool wide: true
    readonly property var sections: backend.schema.filter(s => s.page === root.page)

    Layout.fillWidth: true
    columns: wide ? 2 : 1
    columnSpacing: Theme.gap
    rowSpacing: Theme.gap

    Repeater {
        model: root.sections
        delegate: Card {
            id: card
            required property var modelData
            // sekcja bez żadnego obsługiwanego pola (np. brak klasy xdrive) znika
            visible: !backend.baseConnected
                     || modelData.fields.some(f => backend.settings[f.key] !== undefined)
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: modelData.title
            subtitle: modelData.subtitle
            icon: Theme.icon(modelData.icon)

            Repeater {
                model: card.modelData.fields
                delegate: SettingField {
                    required property var modelData
                    field: modelData
                }
            }
        }
    }
}
