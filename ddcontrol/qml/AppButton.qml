import QtQuick
import QtQuick.Controls.Basic

// Przycisk w stylu aplikacji. variant: primary | secondary | danger | ghost
Button {
    id: root
    property string glyph: ""
    property string variant: "secondary"

    readonly property color fg: !enabled ? Theme.textDim
                              : variant === "primary" ? "#FFFFFF"
                              : variant === "danger" ? Theme.danger : Theme.text

    implicitHeight: 38
    leftPadding: 16
    rightPadding: 16
    hoverEnabled: true
    opacity: enabled ? 1 : 0.6

    contentItem: Row {
        spacing: 8
        Text {
            visible: root.glyph !== ""
            text: root.glyph
            font.family: Theme.fontIcons
            font.pixelSize: 14
            color: root.fg
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: root.text
            font.pixelSize: 13
            font.weight: Font.DemiBold
            color: root.fg
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    background: Rectangle {
        radius: 10
        color: {
            if (!root.enabled)
                return root.variant === "ghost" ? "transparent" : Theme.surface2
            if (root.variant === "primary")
                return root.down ? Qt.darker(Theme.accent, 1.25) : root.hovered ? Qt.lighter(Theme.accent, 1.1) : Theme.accent
            if (root.variant === "ghost")
                return root.hovered ? Theme.surface2 : "transparent"
            if (root.variant === "danger")
                return root.hovered ? Qt.rgba(1, 0.28, 0.34, 0.16) : Qt.rgba(1, 0.28, 0.34, 0.08)
            return root.down ? Theme.surface3 : root.hovered ? Theme.surface3 : Theme.surface2
        }
        border.color: root.variant === "secondary" ? Theme.border
                    : root.variant === "danger" ? Qt.rgba(1, 0.28, 0.34, 0.35) : "transparent"
        Behavior on color { ColorAnimation { duration: 120 } }
    }

    HoverHandler { cursorShape: Qt.PointingHandCursor }
}
