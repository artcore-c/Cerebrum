// Copyright (C) 2021 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only

#include <QGuiApplication>
#include <QQmlApplicationEngine>

#include "app_environment.h"
#include "import_qml_components_plugins.h"
#include "import_qml_plugins.h"

#include "CerebrumClient.h"
#include <QtQml/qqml.h>
#include <QQmlContext>

int main(int argc, char *argv[])
{
    set_qt_environment();
    QGuiApplication app(argc, argv);
    
     // Expose enums/constants to QML (but disallow instantiation)
    qmlRegisterUncreatableType<CerebrumClient>(
        "Cerebrum", 1, 0, "CerebrumClient",
        "Use the context property 'cerebrum'"
    );
    
    QQmlApplicationEngine engine;
    
     CerebrumClient cerebrum;                       // single instance
    engine.rootContext()->setContextProperty("cerebrum", &cerebrum);

    const QUrl url(u"qrc:Main/main.qml"_qs);
    QObject::connect(
                &engine, &QQmlApplicationEngine::objectCreated, &app,
                [url](QObject *obj, const QUrl &objUrl) {
        if (!obj && url == objUrl)
            QCoreApplication::exit(-1);
    },
    Qt::QueuedConnection);

    engine.addImportPath(QCoreApplication::applicationDirPath() + "/qml");
    engine.addImportPath(":/");
    engine.load(url);

    if (engine.rootObjects().isEmpty()) {
        return -1;
    }

    return app.exec();
}
