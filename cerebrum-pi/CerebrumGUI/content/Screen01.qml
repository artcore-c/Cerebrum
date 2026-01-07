import QtQuick 6.5
import QtQuick.Controls 6.5
import CerebrumGUI
import Cerebrum 1.0


Rectangle {
    id: root
    width: Constants.width
    height: Constants.height
    color: "#1a1a1a"

    // ---- CPU graph data ----
    property var cpuData: [0, 0]
    property int cpuMaxSamples: 60   // ~2 minutes at 2s intervals

    // Quiet QML shutdown spam on exit
    property bool appShuttingDown: false
    property bool cerebrumValid: cerebrum && !appShuttingDown
    Component.onDestruction: appShuttingDown = true


    // Safely access cerebrum properties with null checks
    function safeCerebrumProperty(prop, defaultValue) {
        return cerebrumValid && cerebrum ? cerebrum[prop] : defaultValue
    }

    Connections {
            target: cerebrumValid ? cerebrum : null
            enabled: cerebrumValid

            function onTokenReceived(token) {
                if (!appShuttingDown) chatText.text += token
            }

            function onGenerationFinished(totalTokens, inferenceTimeSeconds) {
                if (!appShuttingDown) {
                    chatText.text += "\n[" + totalTokens + " tokens, " +
                                     inferenceTimeSeconds + "s]\n\n"
                }
            }

            function onGenerationError(message) {
                if (!appShuttingDown) {
                    chatText.text += "\n[ERROR] " + message + "\n\n"
                }
            }

            function onResetComplete() {
                if (!appShuttingDown) {
                    chatText.text = ""
                    startupFlip.restart()
                }
            }

            function onMetricsChanged() {
                if (!appShuttingDown) {
                    var newData = cpuData.slice()
                    newData.push(cerebrumValid ? cerebrum.cpuPercent : 0)
                    if (newData.length > cpuMaxSamples)
                        newData.shift()
                    cpuData = newData
                    cpuGraph.requestPaint()
                }
            }
        }


    Shortcut {
        sequence: "Esc"
        onActivated: {
            appShuttingDown = true
            Qt.quit()
        }
    }

    Shortcut {
        sequence: "Ctrl+Q"
        onActivated: {
            appShuttingDown = true
            Qt.quit()
        }
    }


    // Footer - Metrics
    Rectangle {
        id: footer
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        height: 40
        color: "#2a2a2a"
        radius: 10

        Row {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 20
            spacing: 20

            Text {
                text: "Active: " + (cerebrumValid ? cerebrum.activeCount : 0)
                font.letterSpacing: 1
                font.pixelSize: 20
                font.weight: Font.Medium

                font.bold: true
                minimumPointSize: 18
                minimumPixelSize: 18
                color: "#cccccc"
            }

            Text {
                text: "|"
                font.pixelSize: 13
                color: "#444444"
            }

            Text {
                text: "Queue: " + (cerebrumValid ? cerebrum.queueCount : 0)
                font.letterSpacing: 1
                font.pixelSize: 20
                font.weight: Font.Medium
                font.bold: true
                minimumPointSize: 18
                minimumPixelSize: 18
                color: "#cccccc"
            }

            Text {
                text: "|"
                font.pixelSize: 13
                color: "#444444"
            }

            Text {
                text: cerebrumValid ? cerebrum.uptimeText : "Uptime: 0h 0m"

                font.letterSpacing: 1
                font.pixelSize: 20
                font.weight: Font.Medium

                font.bold: true
                minimumPointSize: 18
                minimumPixelSize: 18
                color: "#cccccc"
            }
        }


        Text {
            x: 816
            width: 0
            height: 22
            text: "|"
            font.pixelSize: 13
            transformOrigin: Item.Center
            rotation: 0
            color: "#444444"
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: cpuPanel.right
            anchors.rightMargin: -20
        }

        Rectangle {
            id: cpuPanel
            width: 246
            height: 38
            radius: 1
            border.color: "#3a3a3a"
            border.width: 2
            color: "#1a1a1a"
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: refreshButton.left
            anchors.rightMargin: 45

            Text {
                text: "CPU:"
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.left
                anchors.rightMargin: 5

                font.letterSpacing: 1
                font.pixelSize: 20
                font.weight: Font.Medium
                font.bold: true
                minimumPixelSize: 18
                color: "#cccccc"
            }

            Canvas {
                id: cpuGraph
                width: parent.width -8
                height: parent.height -8
                x: 4
                y: 4
                antialiasing: true

                Component.onCompleted: requestPaint()

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)

                    // MUST have at least 2 points
                    if (cpuData.length < 2)
                        return

                    ctx.strokeStyle = "#55f4f8"   // solid cyan for demo visibility
                    ctx.lineWidth = 1.5
                    ctx.beginPath()

                    var step = width / (cpuData.length - 1)

                    for (var i = 0; i < cpuData.length; i++) {
                        var x = i * step
                        var y = height - Math.max(0, Math.min(100, cpuData[i])) / 100 * height
                        if (i === 0)
                            ctx.moveTo(x, y)
                        else
                            ctx.lineTo(x, y)
                    }

                    ctx.stroke()
                }

            }
        }


        Button {
            id: refreshButton
            x: 1126
            width: 98

            height: 32
            text: "Refresh"
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            font.letterSpacing: 1
            anchors.rightMargin: 15
            font.pixelSize: 20
            highlighted: false
            font.weight: Font.Medium
            font.bold: false
            icon.color: "#ffffff"

            onClicked: cerebrum.refresh()

            background: Rectangle {
                color: "#f26d50"
                radius: 5
            }

            // keyboard shortcut
            Shortcut {
                sequence: "Ctrl+R"
                onActivated: refreshButton.clicked()
            }
        }
    }


    Rectangle {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        height: 87
        color: "#2a2a2a"
        radius: 10

        // PATCH: Replaced Row with Item to allow anchored 3-column layout safely
        Item {
            id: topBarLayout
            anchors.fill: parent
            anchors.bottomMargin: 8

            // Left: System Status
            Column {
                id: leftStatus
                width: 350
                scale: 1.4
                leftPadding: 65
                spacing: 8

                anchors.left: parent.left
                anchors.leftMargin: 0
                anchors.verticalCenter: parent.verticalCenter

                Row {
                    spacing: 8
                    Rectangle {
                        y: 6
                        width: 10
                        height: 10
                        radius: 5
                        color: {
                            if (!cerebrumValid) return "#ff0000"
                            switch (cerebrum.orchestratorState) {
                            case CerebrumClient.HealthGood:
                                return "#00ff00"
                            case CerebrumClient.HealthWarning:
                                return "#ff8800"
                            case CerebrumClient.HealthDown:
                            default:
                                return "#ff0000"
                            }
                        }
                    }

                    Text {
                        y: 1
                        text: {
                            if (!cerebrumValid) return "Orchestrator: Offline"
                            switch (cerebrum.orchestratorState) {
                                case CerebrumClient.HealthGood:
                                    return "Orchestrator: Ready"
                                case CerebrumClient.HealthWarning:
                                    return "Orchestrator: Waiting"
                                case CerebrumClient.HealthDown:
                                default:
                                    return "Orchestrator: Offline"
                            }
                        }

                        font.letterSpacing: 0.5
                        font.pixelSize: 16
                        font.weight: Font.Medium
                        color: "#ffffff"
                    }
                }

                Row {
                    spacing: 8
                    Rectangle {
                        y: 5
                        width: 10
                        height: 11
                        radius: 5
                        color: {
                            if (!cerebrumValid) return "#ff0000"
                            switch (cerebrum.vpsState) {
                            case CerebrumClient.HealthGood:
                                return "#00ff00"
                            case CerebrumClient.HealthWarning:
                                return "#ff8800"
                            case CerebrumClient.HealthDown:
                            default:
                                return "#ff0000"
                            }
                        }
                    }

                    Text {
                        y: 1
                        text: {
                            if (!cerebrumValid) return "VPS: Disconnected"
                            switch (cerebrum.vpsState) {
                                case CerebrumClient.HealthGood:
                                    return "VPS: Connected"
                                case CerebrumClient.HealthWarning:
                                    return "VPS: Connecting"
                                case CerebrumClient.HealthDown:
                                default:
                                    return "VPS: Disconnected"
                            }
                        }

                        font.letterSpacing: 0.5
                        font.pixelSize: 16
                        font.weight: Font.Medium
                        color: "#ffffff"

                    }
                }
            }


            // Center: Title
            Column {
                id: centerTitle
                width: parent.width / 3
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    id: asciiLogo
                    y: 0
                    width: 340

                    font.family: "Menlo"
                    font.pixelSize: 12
                    color: "#55f4f8"
                    text: "  ____              _                    \n / ___|___ _ __ ___| |__  _ __ _   _ _ __ ___™\n| |   / _ \\ '__/ _ \\ '_ \\| '__| | | | '_ ` _ \\\n| |__|  __/ | |  __/ |_) | |  | |_| | | | | | |\n \\____\\___|_|  \\___|_.__/|_|   \\__,_|_| |_| |_|"
                    font.letterSpacing: 0
                    lineHeight: 0.85
                    topPadding: 6
                    bottomPadding: 1
                    scale: 1

                    horizontalAlignment: Text.AlignLeft
                    anchors.horizontalCenter: parent.horizontalCenter

                    // 3D Transform
                    transform: [
                        Rotation {
                            id: flipRotation
                            origin.x: asciiLogo.width / 2
                            origin.y: asciiLogo.height / 2
                            axis { x: 1; y: 0; z: 0 }
                            angle: 0
                        },
                        Scale {
                            id: logoScale
                            origin.x: asciiLogo.width / 2
                            origin.y: asciiLogo.height / 2
                            xScale: 1.0
                            yScale: 1.0
                        }
                    ]

                    // Startup Animation
                    SequentialAnimation {
                        id: startupFlip
                        running: true

                        ParallelAnimation {
                            NumberAnimation {
                                target: flipRotation
                                property: "angle"
                                from: 0
                                to: 360
                                duration: 1500
                                easing.type: Easing.InOutCubic
                            }

                            SequentialAnimation {
                                NumberAnimation {
                                    target: logoScale
                                    properties: "xScale,yScale"
                                    from: 1.0
                                    to: 1.15
                                    duration: 750
                                    easing.type: Easing.InQuad
                                }
                                NumberAnimation {
                                    target: logoScale
                                    properties: "xScale,yScale"
                                    from: 1.15
                                    to: 1.0
                                    duration: 750
                                    easing.type: Easing.OutQuad
                                }
                            }
                        }
                    }
                }


                Text {
                    text: "Distributed Interactive AI Code Assistant"
                    font.letterSpacing: 0.7
                    font.pixelSize: 22
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignTop
                    bottomPadding: 7
                    color: "#888888"
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }

            // Right: Model Info
            Column {
                id: rightModel
                width: 200
                scale: 1.4
                anchors.right: parent.right
                anchors.rightMargin: 60
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4

                Text {
                    text: cerebrumValid ? cerebrum.modelStatusText : "Model: Not Selected"
                    font.pixelSize: 16
                    color: "#888888"
                    anchors.right: parent.right
                    font.letterSpacing: 0.5
                }

                Text {
                    text: cerebrumValid ? cerebrum.currentModel : ""

                    font.pixelSize: 16
                    font.bold: true
                    color: "#55f4f8"
                    anchors.right: parent.right
                    font.letterSpacing: 0.5

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: modelMenu.open()
                    }
                }

                //Menu {
                //    id: modelMenu

                //    Repeater {
                //        model: cerebrumValid ? cerebrum.availableModels : []
                //        delegate: MenuItem {
                //            text: modelData
                //            onTriggered: cerebrum.selectModel(modelData)
                //        }
                //    }
                //}
            }
        }
    }


    // Chat/Text Area
    Rectangle {
        id: chatArea
        anchors.top: topBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top
        anchors.margins: 20
        anchors.bottomMargin: 12
        anchors.topMargin: 10
        color: "#0d0d0d"
        radius: 10
        border.color: "#2a2a2a"
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 10

            // Thinking indicator (only visible when processing)
            Row {
                id: thinkingIndicator
                visible: cerebrumValid && cerebrum.generating

                spacing: 8

                Text {
                    text: "Thinking"
                    font.letterSpacing: 0.5
                    font.pixelSize: 24
                    font.weight: Font.DemiBold
                    font.bold: false
                    color: "#888888"
                    font.italic: true
                }

                // Animated dots
                Row {
                    y: 16
                    spacing: 4
                    Repeater {
                        model: 3
                        Rectangle {
                            width: 6
                            height: 6
                            radius: 3
                            color: "#55f4f8"

                            SequentialAnimation on opacity {
                                running: thinkingIndicator.visible
                                loops: Animation.Infinite

                                PauseAnimation { duration: index * 200 }
                                NumberAnimation { to: 0.3; duration: 400 }
                                NumberAnimation { to: 1.0; duration: 400 }
                            }
                        }
                    }
                }
            }


            // Chat content area
            ScrollView {
                id: chatScroll
                width: parent.width
                height: parent.height - thinkingIndicator.height - cursor.height - 20
                clip: true

                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                TextEdit {
                    id: chatText

                    width: chatScroll.availableWidth
                    height: Math.max(contentHeight, chatScroll.height)

                    color: "#ffffff"
                    font.pixelSize: 23
                    font.family: "Fira Code"

                    wrapMode: TextEdit.Wrap
                    textFormat: TextEdit.PlainText
                    horizontalAlignment: Text.AlignLeft
                    selectByMouse: true
                    readOnly: true

                    onTextChanged: {
                        chatScroll.contentItem.contentY =
                            chatScroll.contentItem.contentHeight - chatScroll.contentItem.height
                    }
                }
            }


            // Cursor line
            Row {
                id: cursor
                spacing: 4

                Rectangle {
                    id: cursorBar
                    y: 0
                    width: 11
                    height: 29
                    color: "#c91dbf"

                    SequentialAnimation on opacity {
                        running: true
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.0; duration: 530 }
                        NumberAnimation { to: 1.0; duration: 530 }
                    }
                }

                TextInput {
                    id: userInput
                    width: 1194
                    font.pixelSize: 23
                    font.family: "Fira Code"
                    color: "#ffffff"
                    focus: true
                    cursorVisible: true
                    wrapMode: TextInput.Wrap

                    Keys.onReturnPressed: {
                        if (text.length > 0) {
                            chatText.text += "\n>>> " + text + "\n"
                            cerebrum.sendPrompt(text)
                            text = ""
                        }
                    }
                }

            }
        }
    }
}
