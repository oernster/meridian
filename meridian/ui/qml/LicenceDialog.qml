import QtQuick

// A licence: plain text in a fixed-width face, which reads itself because a
// licence always overflows. The chrome, the page and the focus rules are
// ReadingDialog's.
ReadingDialog {
    width: 510
    height: 560
    namePrefix: "licence"

    property string licenceTitle: ""
    property string licenceBody: ""

    heading: licenceTitle
    body: licenceBody
    bodyFontFamily: "Courier New"
    bodyFontSize: 11
}
