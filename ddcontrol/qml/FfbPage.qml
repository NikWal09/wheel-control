import QtQuick
import QtQuick.Layouts

PageBase {
    id: page

    NoBaseBanner {}

    SchemaCards {
        page: "ffb"
        wide: page.wide
    }

    Item { Layout.preferredHeight: 20 }
}
