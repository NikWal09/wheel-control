import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Wybór kontrolera gier dla roli ("pedals" / "wheel").
RowLayout {
    id: root
    property string role
    property string currentKey
    property bool connected: false
    readonly property var items: {
        let list = [{ key: "", name: "Wykryj automatycznie" }].concat(backend.joysticks.map(j => ({
            key: j.key, name: j.name + "  ·  " + j.key + "  ·  " + j.axes + " osi, " + j.buttons + " przycisków" })))
        if (currentKey !== "" && !list.some(i => i.key === currentKey))
            list.push({ key: currentKey, name: currentKey + " (odłączone)" })
        return list
    }

    spacing: 14

    Text {
        text: "Urządzenie"
        font.pixelSize: 14
        font.weight: Font.Medium
        color: Theme.text
    }

    ComboBox {
        id: combo
        Layout.fillWidth: true
        implicitHeight: 40
        model: root.items
        textRole: "name"
        valueRole: "key"
        currentIndex: Math.max(0, root.items.findIndex(i => i.key === root.currentKey))
        onActivated: backend.assignDevice(root.role, currentValue)

        contentItem: Text {
            leftPadding: 14
            verticalAlignment: Text.AlignVCenter
            text: combo.displayText
            font.pixelSize: 13
            color: Theme.text
            elide: Text.ElideRight
        }
        indicator: Text {
            x: combo.width - width - 14
            anchors.verticalCenter: parent.verticalCenter
            text: ""
            font.family: Theme.fontIcons
            font.pixelSize: 11
            color: Theme.textDim
        }
        background: Rectangle {
            radius: 10
            color: Theme.bg
            border.color: combo.activeFocus || combo.popup.visible ? Theme.accent : Theme.border
        }
        delegate: ItemDelegate {
            required property var modelData
            required property int index
            width: combo.width
            highlighted: combo.highlightedIndex === index
            contentItem: Text {
                text: modelData.name
                font.pixelSize: 13
                color: Theme.text
                elide: Text.ElideRight
            }
            background: Rectangle { color: highlighted ? Theme.surface3 : "transparent"; radius: 6 }
        }
        popup: Popup {
            y: combo.height + 4
            width: combo.width
            padding: 4
            implicitHeight: contentItem.implicitHeight + 8
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: combo.popup.visible ? combo.delegateModel : null
            }
            background: Rectangle { radius: 10; color: Theme.surface2; border.color: Theme.border }
        }
    }

    Rectangle {
        implicitWidth: statusText.implicitWidth + 22
        implicitHeight: 28
        radius: 14
        color: root.connected ? Qt.rgba(0.18, 0.83, 0.48, 0.1) : Theme.surface2
        border.color: root.connected ? Qt.rgba(0.18, 0.83, 0.48, 0.4) : Theme.border
        Text {
            id: statusText
            anchors.centerIn: parent
            text: root.connected ? "Połączono" : "Brak sygnału"
            font.pixelSize: 12
            color: root.connected ? Theme.success : Theme.textDim
        }
    }
}
