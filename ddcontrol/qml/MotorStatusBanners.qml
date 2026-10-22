import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Co trzeba zrobić, żeby silnik ruszył: włączyć sterownik XDrive, potem skalibrować.
ColumnLayout {
    Layout.fillWidth: true
    spacing: Theme.gap
    visible: backend.baseConnected && (backend.needsXdrive || backend.needsCalibration)

    Banner {
        visible: backend.needsXdrive
        kind: "danger"
        title: "Sterownik silnika nie jest aktywny"
        text: "Płytka MKS XDrive ma w ustawieniach inny sterownik (axis.drvtype = "
            + (backend.settings["axis.0.drvtype"] !== undefined ? backend.settings["axis.0.drvtype"] : "?")
            + "), więc silnik i jego kalibracja są niedostępne. Kliknij, aby włączyć MotorXDrive i zapisać to w płytce."
        AppButton {
            text: "Włącz sterownik XDrive"
            glyph: Theme.icBase
            variant: "primary"
            onClicked: backend.runAction("selectxdrive")
        }
    }

    Banner {
        visible: !backend.needsXdrive && backend.needsCalibration
        kind: "warning"
        title: "Silnik nie jest skalibrowany"
        text: "Bez kalibracji baza nie daje siły. Kalibracja trwa ok. 12 s, kierownica obróci się o kilka "
            + "dziesiątek stopni – puść ją i odsuń ręce. Wymaga podłączonego zasilacza."
        AppButton {
            text: "Kalibruj silnik"
            glyph: Theme.icDiag
            variant: "primary"
            onClicked: ApplicationWindow.window.confirm(
                "Uruchomić kalibrację?",
                "Silnik ustawi wirnik, zmierzy rezystancję i indukcyjność, sprawdzi kierunek enkodera "
                + "i obróci kierownicę o ok. 50°. Puść kierownicę i odsuń ręce.",
                "Kalibruj", false, () => backend.runAction("calibrate"))
        }
    }
}
