import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

PageBase {
    id: page

    NoBaseBanner {}

    Banner {
        visible: backend.baseConnected
        kind: "warning"
        title: "Ustawienia zaawansowane"
        text: "Błędne pary biegunów, kierunek enkodera lub wzmocnienia regulatora mogą spowodować gwałtowny ruch "
            + "kierownicy. Zmieniaj pojedynczo, trzymając ręce z dala od kierownicy, i zapisuj dopiero po sprawdzeniu."
    }

    GridLayout {
        Layout.fillWidth: true
        columns: page.wide ? 2 : 1
        columnSpacing: Theme.gap
        rowSpacing: Theme.gap

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Zasilanie"
            subtitle: "Moc silnika i ochrona zasilacza"
            icon: Theme.icPower

            ToggleRow {
                Layout.fillWidth: true
                label: "Siły włączone"
                description: "Wyłączenie odcina moment silnika – kierownica obraca się swobodnie."
                checked: backend.settings.forceEnabled === 1
                enabled: backend.baseConnected
                onToggled: c => backend.setSetting("forceEnabled", c ? 1 : 0)
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "powerLimit"
                label: "Limit mocy"
                description: "Maksymalny moment jako % możliwości sterownika. Przy pierwszych testach trzymaj nisko."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "brakingLimit"
                label: "Limit hamowania"
                description: "Ogranicza energię oddawaną przez silnik przy hamowaniu – chroni zasilacz przed przepięciem."
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Silnik i enkoder"
            subtitle: "Silnik BLDC z hoverboardu + MT6701"
            icon: Theme.icBase

            NumberStepper {
                Layout.fillWidth: true
                key: "polePairs"
                label: "Pary biegunów"
                description: "Silnik z hoverboardu ma zwykle 15 par (30 magnesów)."
            }
            NumberStepper {
                Layout.fillWidth: true
                key: "encoderCpr"
                label: "CPR enkodera"
                step: 64
                description: "Impulsy na obrót. MT6701 w trybie ABZ 1024 PPR × 4 = 4096."
            }
            Segmented {
                Layout.fillWidth: true
                label: "Kierunek enkodera"
                enabled: backend.baseConnected
                options: [{ label: "Normalny", value: 1 }, { label: "Odwrócony", value: -1 }]
                value: backend.settings.encoderDirection
                onPicked: v => backend.setSetting("encoderDirection", v)
            }
            Segmented {
                Layout.fillWidth: true
                label: "Kierunek siły"
                enabled: backend.baseConnected
                options: [{ label: "Normalny", value: 1 }, { label: "Odwrócony", value: -1 }]
                value: backend.settings.forceDirection
                onPicked: v => backend.setSetting("forceDirection", v)
            }
            Segmented {
                Layout.fillWidth: true
                label: "Wzmocnienie pomiaru prądu"
                enabled: backend.baseConnected
                options: [{ label: "80 V/V", value: 0 }, { label: "40 V/V", value: 1 },
                          { label: "20 V/V", value: 2 }, { label: "10 V/V", value: 3 }]
                value: backend.settings.amplifierGain
                onPicked: v => backend.setSetting("amplifierGain", v)
                description: "Wzmocnienie wzmacniaczy prądu w sterowniku (DRV8301). Wyższe = lepsza rozdzielczość, mniejszy zakres prądu."
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Regulator"
            subtitle: "Pętla prądu i filtracja pozycji"
            icon: Theme.icPedals

            NumberStepper {
                Layout.fillWidth: true
                key: "pGain"
                label: "Wzmocnienie P"
            }
            NumberStepper {
                Layout.fillWidth: true
                key: "iGain"
                label: "Wzmocnienie I"
                step: 10
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "positionSmoothing"
                label: "Wygładzanie pozycji"
                description: "Filtr odczytu enkodera. Więcej = gładziej, ale z większym opóźnieniem."
            }
            NumberStepper {
                Layout.fillWidth: true
                key: "speedBufferSize"
                label: "Bufor prędkości"
                description: "Liczba próbek do wyliczania prędkości (wpływa na tłumienie dynamiczne)."
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Kalibracja"
            subtitle: "Ustawianie kąta elektrycznego przy starcie"
            icon: Theme.icDiag

            SettingSlider {
                Layout.fillWidth: true
                key: "calibrationMagnitude"
                label: "Siła kalibracji"
                description: "Moment używany przy wyszukiwaniu położenia wirnika."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "calibrationSpeed"
                label: "Prędkość kalibracji"
            }
            ToggleRow {
                Layout.fillWidth: true
                label: "Tryb debugowania momentu"
                description: "Diagnostyka sterownika – na co dzień wyłączony."
                checked: backend.settings.debugTorque === 1
                enabled: backend.baseConnected
                onToggled: c => backend.setSetting("debugTorque", c ? 1 : 0)
            }
        }
    }

    Card {
        Layout.fillWidth: true
        title: "Urządzenie"
        subtitle: "Kontroler MKS XDrive Mini z firmware FFBeast"
        icon: Theme.icInfo

        GridLayout {
            Layout.fillWidth: true
            columns: page.wide ? 4 : 2
            columnSpacing: 32
            rowSpacing: 4

            Repeater {
                model: [
                    { k: "Urządzenie", v: backend.baseConnected ? backend.baseName : "—" },
                    { k: "Firmware", v: backend.firmware || "—" },
                    { k: "Licencja", v: !backend.baseConnected ? "—" : backend.licensed ? "Premium" : "Light" },
                    { k: "Połączenie", v: !backend.baseConnected ? "—" : backend.baseSimulated ? "Symulacja" : "USB HID" }
                ]
                delegate: ColumnLayout {
                    required property var modelData
                    spacing: 2
                    Layout.fillWidth: true
                    Text { text: modelData.k.toUpperCase(); font.family: Theme.fontDisplay; font.pixelSize: 11; font.letterSpacing: 1.2; color: Theme.textFaint }
                    Text { text: modelData.v; font.pixelSize: 15; font.weight: Font.DemiBold; color: Theme.text }
                }
            }
        }

        Text {
            visible: backend.deviceId !== ""
            text: "ID urządzenia: " + backend.deviceId
            font.family: "Consolas"
            font.pixelSize: 12
            color: Theme.textDim
        }

        RowLayout {
            spacing: 10
            AppButton {
                text: "Zapisz w bazie"
                glyph: Theme.icSave
                variant: "primary"
                enabled: backend.baseConnected
                onClicked: backend.saveToBase()
            }
            AppButton {
                text: "Odczytaj z bazy"
                glyph: Theme.icRefresh
                enabled: backend.baseConnected
                onClicked: backend.reloadSettings()
            }
            AppButton {
                text: "Restart"
                glyph: Theme.icPower
                enabled: backend.baseConnected
                onClicked: ApplicationWindow.window.confirm(
                    "Zrestartować bazę?",
                    "Niezapisane zmiany zostaną utracone. Po restarcie baza przeprowadzi kalibrację – nie trzymaj kierownicy.",
                    "Restartuj", false, () => backend.rebootBase())
            }
            AppButton {
                text: "Tryb DFU"
                glyph: Theme.icImport
                variant: "danger"
                enabled: backend.baseConnected
                onClicked: ApplicationWindow.window.confirm(
                    "Przejść w tryb DFU?",
                    "Baza zniknie jako kierownica i będzie czekać na nowy firmware (STM32CubeProgrammer / FFBeast). "
                    + "Aby wrócić, odłącz i podłącz zasilanie.",
                    "Przejdź w DFU", true, () => backend.enterDfu())
            }
        }
    }

    Item { Layout.preferredHeight: 20 }
}
