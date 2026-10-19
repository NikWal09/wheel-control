import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1400
    height: 880
    minimumWidth: 1120
    minimumHeight: 720
    visible: true
    title: "DD Control"
    color: Theme.bg
    font.family: Theme.fontBody

    property int currentPage: 0
    readonly property var pages: [
        { name: "dashboard", label: "Pulpit", icon: Theme.icDashboard, title: "Pulpit",
          subtitle: "Podgląd na żywo bazy, pedałów i kierownicy" },
        { name: "ffb", label: "Force Feedback", icon: Theme.icFfb, title: "Force Feedback",
          subtitle: "Siła i charakter efektów – zmiany działają natychmiast" },
        { name: "base", label: "Baza i silnik", icon: Theme.icBase, title: "Baza i silnik",
          subtitle: "Zasilanie, silnik, enkoder, regulator i informacje o urządzeniu" },
        { name: "pedals", label: "Pedały", icon: Theme.icPedals, title: "Pedały",
          subtitle: "Podgląd gazu i hamulca (load cell)" },
        { name: "wheel", label: "Kierownica", icon: Theme.icWheel, title: "Kierownica",
          subtitle: "Test i przypisanie przycisków kierownicy BLE" },
        { name: "profiles", label: "Profile", icon: Theme.icProfiles, title: "Profile",
          subtitle: "Zestawy ustawień FFB pod konkretne gry" },
        { name: "settings", label: "Ustawienia", icon: Theme.icSettings, title: "Ustawienia aplikacji",
          subtitle: "Wygląd, tryb demo i informacje" }
    ]
    readonly property var pageNames: pages.map(p => p.name)

    Binding { target: Theme; property: "accent"; value: backend.accent }

    function confirm(title, text, actionLabel, danger, callback) {
        confirmDialog.title = title
        confirmDialog.text = text
        confirmDialog.actionLabel = actionLabel
        confirmDialog.danger = danger
        confirmDialog.callback = callback
        confirmDialog.open()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ---------------- pasek boczny ----------------
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 248
            color: Theme.sidebar

            Rectangle {
                anchors.right: parent.right
                width: 1
                height: parent.height
                color: Theme.border
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                anchors.topMargin: 24
                spacing: 4

                // logo
                RowLayout {
                    spacing: 12
                    Layout.leftMargin: 6
                    Layout.bottomMargin: 26
                    Rectangle {
                        width: 40; height: 40; radius: 11
                        gradient: Gradient {
                            GradientStop { position: 0; color: Qt.lighter(Theme.accent, 1.15) }
                            GradientStop { position: 1; color: Qt.darker(Theme.accent, 1.5) }
                        }
                        Text {
                            anchors.centerIn: parent
                            text: "DD"
                            font.family: Theme.fontDisplay
                            font.pixelSize: 17
                            font.weight: Font.Bold
                            color: "#fff"
                        }
                    }
                    ColumnLayout {
                        spacing: 0
                        Text {
                            text: "DD CONTROL"
                            font.family: Theme.fontDisplay
                            font.pixelSize: 18
                            font.weight: Font.Bold
                            font.letterSpacing: 1.5
                            color: Theme.text
                        }
                        Text {
                            text: "Direct Drive Suite"
                            font.pixelSize: 11
                            color: Theme.textFaint
                        }
                    }
                }

                Repeater {
                    model: win.pages
                    delegate: Rectangle {
                        id: navItem
                        required property var modelData
                        required property int index
                        readonly property bool current: win.currentPage === index
                        Layout.fillWidth: true
                        implicitHeight: 44
                        radius: 10
                        color: current ? Theme.surface2 : (navMouse.containsMouse ? Theme.surface : "transparent")
                        Behavior on color { ColorAnimation { duration: 120 } }

                        Rectangle {
                            visible: navItem.current
                            x: 0
                            anchors.verticalCenter: parent.verticalCenter
                            width: 3; height: 20; radius: 2
                            color: Theme.accent
                        }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 12
                            spacing: 14
                            Text {
                                text: navItem.modelData.icon
                                font.family: Theme.fontIcons
                                font.pixelSize: 16
                                color: navItem.current ? Theme.accent : Theme.textDim
                            }
                            Text {
                                text: navItem.modelData.label
                                font.pixelSize: 14
                                font.weight: navItem.current ? Font.DemiBold : Font.Normal
                                color: navItem.current ? Theme.text : Theme.textDim
                                Layout.fillWidth: true
                            }
                            Rectangle {
                                // kropka "niezapisane" przy stronach z ustawieniami bazy
                                visible: backend.dirty && (navItem.index === 1 || navItem.index === 2)
                                width: 6; height: 6; radius: 3
                                color: Theme.warning
                            }
                        }
                        MouseArea {
                            id: navMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: win.currentPage = navItem.index
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // aktywny profil
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: profCol.implicitHeight + 24
                    radius: 12
                    color: Theme.surface
                    border.color: Theme.border
                    ColumnLayout {
                        id: profCol
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 2
                        Text {
                            text: "AKTYWNY PROFIL"
                            font.family: Theme.fontDisplay
                            font.pixelSize: 10
                            font.letterSpacing: 1.2
                            color: Theme.textFaint
                        }
                        Text {
                            text: (backend.activeProfile || "Brak") + (backend.profileModified ? " *" : "")
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                            color: Theme.text
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: win.currentPage = 5
                    }
                }

                // urządzenia
                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: 8
                    implicitHeight: devCol.implicitHeight + 28
                    radius: 12
                    color: Theme.surface
                    border.color: Theme.border
                    ColumnLayout {
                        id: devCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 12
                        StatusRow {
                            Layout.fillWidth: true
                            label: "Baza Direct Drive"
                            ok: backend.baseConnected
                            detail: backend.baseSimulated ? "Symulacja" : (backend.firmware ? "FFBeast " + backend.firmware : "")
                        }
                        StatusRow {
                            Layout.fillWidth: true
                            label: "Kierownica"
                            ok: backend.wheelConnected
                            detail: backend.wheelName
                        }
                        StatusRow {
                            Layout.fillWidth: true
                            label: "Pedały"
                            ok: backend.pedalsConnected
                            detail: backend.pedalsName
                        }
                    }
                }
            }
        }

        // ---------------- treść ----------------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // nagłówek strony
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                Layout.topMargin: 26
                Layout.bottomMargin: 14
                spacing: 12

                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true
                    Text {
                        text: win.pages[win.currentPage].title
                        font.family: Theme.fontDisplay
                        font.pixelSize: 30
                        font.weight: Font.DemiBold
                        color: Theme.text
                    }
                    Text {
                        text: win.pages[win.currentPage].subtitle
                        font.pixelSize: 13
                        color: Theme.textDim
                    }
                }

                Rectangle {
                    visible: backend.baseSimulated
                    implicitWidth: simLabel.implicitWidth + 24
                    implicitHeight: 30
                    radius: 15
                    color: Qt.rgba(0.24, 0.65, 1, 0.12)
                    border.color: Qt.rgba(0.24, 0.65, 1, 0.4)
                    Text {
                        id: simLabel
                        anchors.centerIn: parent
                        text: "TRYB DEMO"
                        font.family: Theme.fontDisplay
                        font.pixelSize: 12
                        font.letterSpacing: 1.2
                        color: Theme.info
                    }
                }

                Rectangle {
                    visible: backend.dirty && backend.baseConnected
                    implicitWidth: dirtyRow.implicitWidth + 24
                    implicitHeight: 30
                    radius: 15
                    color: Qt.rgba(1, 0.69, 0.13, 0.1)
                    border.color: Qt.rgba(1, 0.69, 0.13, 0.4)
                    Row {
                        id: dirtyRow
                        anchors.centerIn: parent
                        spacing: 8
                        Rectangle { width: 6; height: 6; radius: 3; color: Theme.warning; anchors.verticalCenter: parent.verticalCenter }
                        Text {
                            text: "Niezapisane w bazie"
                            font.pixelSize: 12
                            color: Theme.warning
                        }
                    }
                }

                AppButton {
                    visible: backend.dirty && backend.baseConnected
                    text: "Cofnij"
                    glyph: Theme.icUndo
                    variant: "ghost"
                    onClicked: backend.reloadSettings()
                }
                AppButton {
                    text: "Zapisz w bazie"
                    glyph: Theme.icSave
                    variant: "primary"
                    enabled: backend.baseConnected && backend.dirty
                    onClicked: backend.saveToBase()
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: win.currentPage

                DashboardPage {}
                FfbPage {}
                BasePage {}
                PedalsPage {}
                WheelPage {}
                ProfilesPage {}
                SettingsPage {}
            }
        }
    }

    // ---------------- powiadomienia ----------------
    ListModel { id: toasts }

    Connections {
        target: backend
        function onToast(message, kind) {
            toasts.append({ message: message, kind: kind, born: Date.now() })
            if (toasts.count > 4)
                toasts.remove(0)
        }
    }

    Timer {
        interval: 250
        repeat: true
        running: toasts.count > 0
        onTriggered: {
            while (toasts.count > 0 && Date.now() - toasts.get(0).born > 3800)
                toasts.remove(0)
        }
    }

    Column {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24
        spacing: 10
        z: 100

        Repeater {
            model: toasts
            delegate: Rectangle {
                required property string message
                required property string kind
                readonly property color tone: kind === "success" ? Theme.success : kind === "error" ? Theme.danger : Theme.info
                width: Math.min(420, toastText.implicitWidth + 64)
                height: 48
                radius: 12
                color: Theme.surface2
                border.color: Qt.rgba(tone.r, tone.g, tone.b, 0.45)
                Rectangle {
                    x: 0; width: 4; height: parent.height - 20
                    anchors.verticalCenter: parent.verticalCenter
                    radius: 2
                    color: parent.tone
                }
                Text {
                    x: 18
                    anchors.verticalCenter: parent.verticalCenter
                    text: kind === "error" ? Theme.icWarning : kind === "success" ? Theme.icCheck : Theme.icInfo
                    font.family: Theme.fontIcons
                    font.pixelSize: 14
                    color: parent.tone
                }
                Text {
                    id: toastText
                    x: 44
                    width: parent.width - 58
                    anchors.verticalCenter: parent.verticalCenter
                    text: message
                    elide: Text.ElideRight
                    font.pixelSize: 13
                    color: Theme.text
                }
            }
        }
    }

    // ---------------- potwierdzenie ----------------
    Popup {
        id: confirmDialog
        property string title
        property string text
        property string actionLabel
        property bool danger: false
        property var callback

        anchors.centerIn: Overlay.overlay
        width: 440
        modal: true
        padding: 26
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.6) }
        background: Rectangle {
            radius: 16
            color: Theme.surface
            border.color: Theme.border
        }

        contentItem: ColumnLayout {
            spacing: 14
            Text {
                text: confirmDialog.title
                font.family: Theme.fontDisplay
                font.pixelSize: 20
                font.weight: Font.DemiBold
                color: Theme.text
            }
            Text {
                text: confirmDialog.text
                wrapMode: Text.WordWrap
                font.pixelSize: 13
                lineHeight: 1.2
                color: Theme.textDim
                Layout.fillWidth: true
            }
            RowLayout {
                Layout.topMargin: 8
                Layout.alignment: Qt.AlignRight
                spacing: 10
                AppButton {
                    text: "Anuluj"
                    variant: "ghost"
                    onClicked: confirmDialog.close()
                }
                AppButton {
                    text: confirmDialog.actionLabel
                    variant: confirmDialog.danger ? "danger" : "primary"
                    onClicked: {
                        confirmDialog.close()
                        if (confirmDialog.callback)
                            confirmDialog.callback()
                    }
                }
            }
        }
    }
}
