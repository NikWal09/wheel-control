import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Przewijana strona z marginesami; dzieci układane w kolumnie.
ScrollView {
    id: root
    default property alias content: column.data
    readonly property real pageWidth: availableWidth - 2 * 32
    readonly property bool wide: pageWidth > 1000

    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical: ScrollBar {
        parent: root
        x: root.width - width - 4
        y: 4
        height: root.height - 8
        active: root.ScrollBar.vertical.active
        contentItem: Rectangle {
            implicitWidth: 6
            radius: 3
            color: Theme.surface3
        }
    }

    ColumnLayout {
        id: column
        x: 32
        width: root.pageWidth
        spacing: Theme.gap
        Item { Layout.preferredHeight: 6 }
    }
}
