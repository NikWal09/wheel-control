import QtQuick
import QtQuick.Layouts

PageBase {
    id: page

    NoBaseBanner {}

    GridLayout {
        Layout.fillWidth: true
        columns: page.wide ? 2 : 1
        columnSpacing: Theme.gap
        rowSpacing: Theme.gap

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Ogólne"
            subtitle: "Najważniejsze parametry"
            icon: Theme.icFfb

            SettingSlider {
                Layout.fillWidth: true
                key: "motionRange"
                label: "Kąt obrotu"
                unit: "°"
                from: 180
                to: 2520
                stepSize: 10
                presets: [360, 540, 720, 900, 1080, 1440]
                description: "Pełny kąt obrotu od blokady do blokady. Gry ustawiające kąt same (iRacing, ACC, AC) "
                    + "najlepiej działają z 900–1080°."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "totalStrength"
                label: "Siła całkowita"
                description: "Globalny mnożnik wszystkich efektów. Zaczynaj od niskich wartości – silnik "
                    + "z hoverboardu potrafi oddać ok. 15 Nm."
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Efekty z gry"
            subtitle: "Siły wysyłane przez symulator (DirectInput)"
            icon: Theme.icWheel

            SettingSlider {
                Layout.fillWidth: true
                key: "dxConstantStrength"
                label: "Siła stała"
                description: "Główny kanał FFB – siły na kołach, przyczepność, podsterowność."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "dxPeriodicStrength"
                label: "Efekty okresowe"
                description: "Wibracje: tarki, nierówności nawierzchni, praca silnika."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "dxSpringStrength"
                label: "Sprężyna"
                description: "Sprężyna centrująca wysyłana przez grę (np. w menu albo starszych tytułach)."
            }
            Segmented {
                Layout.fillWidth: true
                label: "Kierunek sił z gry"
                enabled: backend.baseConnected
                options: [{ label: "Normalny", value: 1 }, { label: "Odwrócony", value: -1 }]
                value: backend.settings.dxConstantDirection
                onPicked: v => backend.setSetting("dxConstantDirection", v)
                description: "Odwróć, jeśli w grze kierownica „ucieka” w zakręt zamiast stawiać opór."
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Efekty bazy"
            subtitle: "Generowane przez sterownik, niezależnie od gry"
            icon: Theme.icBase

            SettingSlider {
                Layout.fillWidth: true
                key: "integratedSpring"
                label: "Sprężyna centrująca"
                description: "Stała siła wracająca do środka. Przydatna w grach bez FFB; w symulatorach zwykle 0%."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "staticDampening"
                label: "Tłumienie statyczne"
                description: "Stały opór obrotu – dodaje „ciężaru” i wycisza drobne oscylacje."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "dynamicDampening"
                label: "Tłumienie dynamiczne"
                description: "Opór rosnący z prędkością obrotu – stabilizuje kierownicę przy szybkich kontrach."
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            title: "Wirtualna blokada"
            subtitle: "Soft stop na końcu zakresu obrotu"
            icon: Theme.icWarning

            SettingSlider {
                Layout.fillWidth: true
                key: "softStopStrength"
                label: "Siła blokady"
                description: "Jak mocno baza zatrzymuje kierownicę po przekroczeniu kąta obrotu."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "softStopRange"
                label: "Zakres narastania"
                unit: "°"
                to: 90
                description: "Kąt (ponad zakres obrotu), na którym siła blokady rośnie do maksimum."
            }
            SettingSlider {
                Layout.fillWidth: true
                key: "softStopDampening"
                label: "Tłumienie blokady"
                description: "Zapobiega odbijaniu się kierownicy od blokady."
            }
        }
    }

    Item { Layout.preferredHeight: 20 }
}
