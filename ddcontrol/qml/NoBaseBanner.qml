import QtQuick

// Pokazywany na stronach wymagających bazy, gdy jej nie ma.
Banner {
    visible: !backend.baseConnected
    kind: "warning"
    title: "Baza niepodłączona"
    text: "Podłącz bazę przez USB-C i włącz zasilacz – aplikacja sama wykryje firmware OpenFFBoard "
        + "(port COM) albo FFBeast (USB HID). Możesz też obejrzeć aplikację w trybie demo."

    AppButton {
        visible: !backend.simulation
        text: "Tryb demo"
        glyph: Theme.icDiag
        onClicked: backend.setSimulation(true)
    }
}
