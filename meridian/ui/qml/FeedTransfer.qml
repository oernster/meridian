import QtQuick
import QtQuick.Dialogs

// The feed list leaving and re-entering the application: the two file pickers
// and the report every import ends in.
//
// Extracted from main.qml, which held the two pickers inline; the import
// report made a third piece of the same concern. An import says what it did
// every time, through a dialog that stays until dismissed: the controller used
// to log a feed it could not add and say nothing, so a partial import read as
// a whole one. A transient toast would repeat that failure for a long list.
//
// A plain Item with no size: it takes no focus and paints nothing. The dialogs
// centre themselves on the window's overlay, so where this sits is immaterial.
Item {
    id: transfer

    required property var theme

    function chooseImport() { importDialog.open() }
    function chooseExport() { exportDialog.open() }

    Connections {
        target: controller
        function onImportReported(message, complete) {
            importReportDialog.title = complete ? "Import Feeds" : "Import Incomplete"
            importReportDialog.message = message
            importReportDialog.open()
        }
    }

    FileDialog {
        id: exportDialog
        fileMode: FileDialog.SaveFile
        nameFilters: ["Meridian feeds (*.json)"]
        defaultSuffix: "json"
        onAccepted: controller.exportFeeds(selectedFile)
    }

    FileDialog {
        id: importDialog
        fileMode: FileDialog.OpenFile
        nameFilters: ["Meridian feeds (*.json)", "All files (*)"]
        onAccepted: controller.importFeeds(selectedFile)
    }

    ConfirmDialog {
        id: importReportDialog
        objectName: "importReportDialog"
        theme: transfer.theme
        okOnly: true
        bodyLineHeight: 1.0
    }
}
