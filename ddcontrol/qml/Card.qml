import QtQuick
import QtQuick.Layouts

// Kafelek z nagłówkiem (ikona, tytuł, podtytuł, miejsce na akcje po prawej).
Rectangle {
    id: root
    property string title: ""
    property string subtitle: ""
    property string icon: ""
    property int padding: 22
    property bool fillBody: false   // true: treść rozciąga się na całą wysokość kafelka
    default property alias content: body.data
    property alias actions: actionsRow.data

    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.border
    border.width: 1
    implicitHeight: layout.implicitHeight + 2 * padding
    implicitWidth: layout.implicitWidth + 2 * padding
    // równe kolumny w GridLayout niezależnie od szerokości treści
    Layout.preferredWidth: 1

    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.margins: root.padding
        spacing: 18

        RowLayout {
            visible: root.title !== ""
            Layout.fillWidth: true
            spacing: 12

            Rectangle {
                visible: root.icon !== ""
                width: 34; height: 34; radius: 10
                color: Theme.accentSoft
                Text {
                    anchors.centerIn: parent
                    text: root.icon
                    font.family: Theme.fontIcons
                    font.pixelSize: 16
                    color: Theme.accent
                }
            }
            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true
                Text {
                    text: root.title.toUpperCase()
                    font.family: Theme.fontDisplay
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.2
                    color: Theme.text
                }
                Text {
                    visible: root.subtitle !== ""
                    text: root.subtitle
                    font.pixelSize: 12
                    color: Theme.textDim
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
            Row {
                id: actionsRow
                spacing: 8
            }
        }

        ColumnLayout {
            id: body
            Layout.fillWidth: true
            Layout.fillHeight: root.fillBody
            spacing: 22
        }
        Item {
            visible: !root.fillBody
            Layout.fillHeight: true
        }
    }
}
