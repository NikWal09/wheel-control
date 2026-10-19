import QtQuick
import QtQuick.Layouts

// Pasek informacyjny. kind: info | warning | danger
Rectangle {
    id: root
    property string kind: "info"
    property string title
    property string text: ""
    property string icon: kind === "info" ? Theme.icInfo : Theme.icWarning
    default property alias actions: actionsRow.data
    readonly property color tone: kind === "warning" ? Theme.warning : kind === "danger" ? Theme.danger : Theme.info

    Layout.fillWidth: true
    implicitHeight: row.implicitHeight + 28
    radius: 12
    color: Qt.rgba(tone.r, tone.g, tone.b, 0.08)
    border.color: Qt.rgba(tone.r, tone.g, tone.b, 0.35)

    RowLayout {
        id: row
        anchors.fill: parent
        anchors.margins: 14
        anchors.leftMargin: 18
        spacing: 14
        Text {
            text: root.icon
            font.family: Theme.fontIcons
            font.pixelSize: 18
            color: root.tone
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: 2
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Text {
                text: root.title
                font.pixelSize: 14
                font.weight: Font.DemiBold
                color: Theme.text
            }
            Text {
                visible: root.text !== ""
                text: root.text
                wrapMode: Text.WordWrap
                font.pixelSize: 12
                color: Theme.textDim
                Layout.fillWidth: true
            }
        }
        Row {
            id: actionsRow
            spacing: 8
            Layout.alignment: Qt.AlignVCenter
        }
    }
}
