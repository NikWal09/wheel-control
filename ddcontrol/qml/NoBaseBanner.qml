import QtQuick

// Pokazywany na stronach wymagających bazy, gdy jej nie ma.
Banner {
    visible: !backend.baseConnected
    kind: "warning"
    title: "Baza niepodłączona"
    text: "Podłącz bazę Direct Drive przez USB-C i włącz zasilacz – aplikacja połączy się automatycznie. "
        + "Możesz też obejrzeć aplikację w trybie demo."

    AppButton {
        visible: !backend.simulation
        text: "Tryb demo"
        glyph: Theme.icDiag
        onClicked: backend.setSimulation(true)
    }
}
