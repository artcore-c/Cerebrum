#include "CerebrumClient.h"

#include <QNetworkRequest>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QUrl>
#include <QDateTime>
#include <functional>

// Helper for API_BASE
QString CerebrumClient::apiBase() const
{
    const QByteArray host = qgetenv("CEREBRUM_HOST");
    const QByteArray port = qgetenv("CEREBRUM_PORT");

    if (!host.isEmpty()) {
        const QString p = port.isEmpty()
            ? QStringLiteral("7000")
            : QString::fromUtf8(port);

        return QStringLiteral("http://%1:%2")
            .arg(QString::fromUtf8(host), p);
    }

    return API_BASE;
}

// Helper for model name display formatting
static QString prettyModelName(const QString &id)
{
    if (id == "qwen_7b")       return "Qwen 7B";
    if (id == "codellama_7b")  return "CodeLlama 7B";
    if (id == "deepseek_6b")   return "DeepSeek 6B";

    // Fallback: show raw ID
    return id;
}

static QByteArray mkJsonBody(const QJsonObject &obj) {
    return QJsonDocument(obj).toJson(QJsonDocument::Compact);
}

CerebrumClient::CerebrumClient(QObject *parent)
    : QObject(parent)
{
    m_availableModels = DEFAULT_MODELS;

    // Start in a known UI state (Not Selected until proven)
    m_modelLoaded = false;

    // Poll health occasionally (optional; keeps dots fresh)
    m_healthTimer.setInterval(2000);
    m_healthTimer.setSingleShot(false);
    connect(&m_healthTimer, &QTimer::timeout, this, &CerebrumClient::checkHealth);

    // Initial refresh
    refresh();
}

void CerebrumClient::refresh()
{
    // Stop any in-flight stream
    if (m_streamReply) {
        m_streamReply->disconnect(this);
        m_streamReply->abort();
        m_streamReply->deleteLater();
        m_streamReply = nullptr;
    }
    m_sseBuffer.clear();
    setGenerating(false);

    // Reset visible state, then re-detect
    setOrchestratorRunning(false);
    setVpsConnected(false);
    setModelLoaded(false);

    resetMetrics();

    // Kick checks
    fetchModels();
    checkHealth();

    // Start polling after first refresh (safe even if unreachable)
    if (!m_healthTimer.isActive())
        m_healthTimer.start();

    emit resetComplete();
}

void CerebrumClient::resetMetrics()
{
    m_activeCount = 0;
    m_queueCount = 0;
    m_uptimeText = "Uptime: 0h 0m";
    m_cpuPercent = 0.0;  
    emit metricsChanged();
}

void CerebrumClient::checkHealth()
{
    QNetworkRequest req(QUrl(apiBase() + HEALTH_EP));
    req.setHeader(QNetworkRequest::UserAgentHeader, "CerebrumGUI/1.0");

    QNetworkReply *r = m_net.get(req);
    connect(r, &QNetworkReply::finished, this, [this, r]() {
        const int code = r->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray body = r->readAll();
        const bool ok = (r->error() == QNetworkReply::NoError && code >= 200 && code < 300);
        r->deleteLater();

        // ---------------------------
        // ORCHESTRATOR OK?
        // ---------------------------
        if (!ok) {
            setOrchestratorRunning(false);
            setVpsConnected(false);

            // misses
            m_orchestratorMisses++;
            m_vpsMisses++;

            // derive states
            HealthState newOrchState =
                (m_orchestratorMisses >= 3) ? HealthDown :
                (m_orchestratorMisses >= 1) ? HealthWarning :
                                                HealthGood;

            HealthState newVpsState =
                (m_vpsMisses >= 3) ? HealthDown :
                (m_vpsMisses >= 1) ? HealthWarning :
                                        HealthGood;

            if (newOrchState != m_orchestratorState || newVpsState != m_vpsState) {
                m_orchestratorState = newOrchState;
                m_vpsState = newVpsState;
                emit healthStateChanged();
            }

            return;
        }

        // If we’re here, orchestrator is reachable.
        setOrchestratorRunning(true);

        // success resets orchestrator misses
        m_orchestratorMisses = 0;

        // ---------------------------
        // Parse JSON once
        // ---------------------------
        bool vpsOk = true; // default optimistic
        QJsonParseError pe{};
        const QJsonDocument doc = QJsonDocument::fromJson(body, &pe);

        if (pe.error == QJsonParseError::NoError && doc.isObject()) {
            const QJsonObject o = doc.object();

            // metrics (active/queue/uptime_text)
            updateMetricsFromHealthJson(body);

            // cpu_percent (for your graph)
            if (o.contains("cpu_percent") && o["cpu_percent"].isDouble()) {
                const double newCpu = o["cpu_percent"].toDouble();
                if (m_cpuPercent != newCpu) {
                    m_cpuPercent = newCpu;
                    emit metricsChanged();
                }
            }

            // vps connectivity
            if (o.contains("vps_connected") && o["vps_connected"].isBool()) {
                vpsOk = o["vps_connected"].toBool();
            } else if (o.contains("vps") && o["vps"].isObject()) {
                const QJsonObject v = o["vps"].toObject();
                if (v.contains("connected") && v["connected"].isBool())
                    vpsOk = v["connected"].toBool();
            }

            // ---------------------------
            // Active model 
            // ---------------------------
            // Backend is authoritative for model state (GUI is observational only)
            if (o.contains("active_model") && o["active_model"].isString()) {
                const QString model = o["active_model"].toString();
                setCurrentModel(model);
                setModelLoaded(!model.isEmpty());
            } else {
                setCurrentModel("idle");
                setModelLoaded(false);
            }
        
            // optional model sync fields
            // if (o.contains("model_loaded") && o["model_loaded"].isBool())
            //     setModelLoaded(o["model_loaded"].toBool());
            // if (o.contains("model") && o["model"].isString())
            //     setCurrentModel(o["model"].toString());
        } else {
            // If JSON is missing/invalid but /health returned 200, still show as up.
            // Leave vpsOk=true (or set false if you prefer strict JSON).
            updateMetricsFromHealthJson(body);
        }

        // ---------------------------
        // VPS hysteresis
        // ---------------------------
        if (vpsOk) m_vpsMisses = 0;
        else       m_vpsMisses++;

        HealthState newOrchState = HealthGood; // successful /health
        HealthState newVpsState =
            (m_vpsMisses >= 3) ? HealthDown :
            (m_vpsMisses >= 1) ? HealthWarning :
                                    HealthGood;

        if (newOrchState != m_orchestratorState || newVpsState != m_vpsState) {
            m_orchestratorState = newOrchState;
            m_vpsState = newVpsState;
            emit healthStateChanged();
        }

        // binary truth
        setVpsConnected(vpsOk);
    });
}

void CerebrumClient::updateMetricsFromHealthJson(const QByteArray &json)
{
    QJsonParseError pe{};
    const auto doc = QJsonDocument::fromJson(json, &pe);
    if (pe.error != QJsonParseError::NoError || !doc.isObject())
        return;

    const auto o = doc.object();

    // Active
    if (o.contains("active") && o["active"].isDouble()) {
        m_activeCount = o["active"].toInt();
        emit metricsChanged();
    } else if (o.contains("active_count") && o["active_count"].isDouble()) {
        m_activeCount = o["active_count"].toInt();
        emit metricsChanged();
    }

    // Queue (optional; you said can remain 0)
    if (o.contains("queue") && o["queue"].isDouble()) {
        m_queueCount = o["queue"].toInt();
        emit metricsChanged();
    } else if (o.contains("queue_count") && o["queue_count"].isDouble()) {
        m_queueCount = o["queue_count"].toInt();
        emit metricsChanged();
    }

    // Uptime (optional)
    if (o.contains("uptime") && o["uptime"].isString()) {
        m_uptimeText = "Uptime: " + o["uptime"].toString();
        emit metricsChanged();
    } else if (o.contains("uptime_text") && o["uptime_text"].isString()) {
        m_uptimeText = "Uptime: " + o["uptime_text"].toString();
        emit metricsChanged();
    }
}

void CerebrumClient::fetchModels()
{
    // GUI model selection disabled (unless backend supports it)
    // Backend model state is reported via /health (active_model)

    // Try first endpoint
    QNetworkRequest req1(QUrl(apiBase() + MODELS_EP_1));
    req1.setHeader(QNetworkRequest::UserAgentHeader, "CerebrumGUI/1.0");

    QNetworkReply *r1 = m_net.get(req1);
    connect(r1, &QNetworkReply::finished, this, [this, r1]() {
        const int code = r1->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray body = r1->readAll();
        const bool ok = (r1->error() == QNetworkReply::NoError && code >= 200 && code < 300);
        r1->deleteLater();

        if (ok) {
            QJsonParseError pe{};
            const auto doc = QJsonDocument::fromJson(body, &pe);
            if (pe.error == QJsonParseError::NoError) {
                QStringList models;
                
                if (doc.isArray()) {
                    for (const auto &v : doc.array())
                        if (v.isString()) models << v.toString();
                } else if (doc.isObject()) {
                    const auto o = doc.object();
                    if (o.contains("models") && o["models"].isArray()) {
                        for (const auto &v : o["models"].toArray())
                            if (v.isString()) models << v.toString();
                    }
                }
                
                if (!models.isEmpty()) {
                    m_availableModels = models;
                    emit availableModelsChanged();
                    return; // Success!
                }
            }
        }

        // First failed, try second endpoint
        QNetworkRequest req2(QUrl(apiBase() + MODELS_EP_2));
        req2.setHeader(QNetworkRequest::UserAgentHeader, "CerebrumGUI/1.0");

        QNetworkReply *r2 = m_net.get(req2);
        connect(r2, &QNetworkReply::finished, this, [this, r2]() {
            const int code = r2->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
            const QByteArray body = r2->readAll();
            const bool ok = (r2->error() == QNetworkReply::NoError && code >= 200 && code < 300);
            r2->deleteLater();

            if (ok) {
                QJsonParseError pe{};
                const auto doc = QJsonDocument::fromJson(body, &pe);
                if (pe.error == QJsonParseError::NoError) {
                    QStringList models;
                    
                    if (doc.isArray()) {
                        for (const auto &v : doc.array())
                            if (v.isString()) models << v.toString();
                    } else if (doc.isObject()) {
                        const auto o = doc.object();
                        if (o.contains("models") && o["models"].isArray()) {
                            for (const auto &v : o["models"].toArray())
                                if (v.isString()) models << v.toString();
                        }
                    }
                    
                    if (!models.isEmpty()) {
                        m_availableModels = models;
                        emit availableModelsChanged();
                        return;
                    }
                }
            }

            // Both failed - use defaults
            if (m_availableModels.isEmpty()) {
                m_availableModels = DEFAULT_MODELS;
                emit availableModelsChanged();
            }
        });
    });
}


/*
void CerebrumClient::openModelMenu()
{
    // no-op; QML displays availableModels
}

void CerebrumClient::selectModel(const QString &modelName)
{
    setCurrentModel(modelName);
    setModelLoaded(true); // optimistic selection

    // Try POST /v1/model/select {model:"..."}
    // If endpoint doesn't exist yet, this will fail and we remain Not Selected.
    QNetworkRequest req(QUrl(apiBase() + SELECT_MODEL_EP));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setHeader(QNetworkRequest::UserAgentHeader, "CerebrumGUI/1.0");

    QJsonObject payload;
    payload["model"] = modelName;

    QNetworkReply *r = m_net.post(req, mkJsonBody(payload));
    connect(r, &QNetworkReply::finished, this, [this, r]() {
        const int code = r->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray body = r->readAll();
        r->deleteLater();

        if (r->error() != QNetworkReply::NoError || code < 200 || code >= 300) {
            // setModelLoaded(false); //<-- backend doesn't support model select yet — keep UI selected
            return;
        }

        // If JSON says loaded, use it; else treat success as loaded.
        bool loaded = true;
        QJsonParseError pe{};
        const auto doc = QJsonDocument::fromJson(body, &pe);
        if (pe.error == QJsonParseError::NoError && doc.isObject()) {
            const auto o = doc.object();
            if (o.contains("loaded") && o["loaded"].isBool())
                loaded = o["loaded"].toBool();
            if (o.contains("model") && o["model"].isString())
                setCurrentModel(o["model"].toString());
        }
        setModelLoaded(loaded);
    });
}
*/

void CerebrumClient::sendPrompt(const QString &prompt)
{
    if (prompt.trimmed().isEmpty())
        return;

    if (m_generating) {
        emit generationError("Generation already in progress.");
        return;
    }

    // Must have orchestrator reachable; otherwise error immediately
    if (!m_orchestratorRunning) {
        emit generationError("Orchestrator is not running (localhost:7000 unreachable).");
        return;
    }

    // Abort any previous stream
    if (m_streamReply) {
        m_streamReply->disconnect(this);
        m_streamReply->abort();
        m_streamReply->deleteLater();
        m_streamReply = nullptr;
    }
    m_sseBuffer.clear();

    QJsonObject payload;
    payload["prompt"] = prompt;
    payload["language"] = "python";
    payload["max_tokens"] = 512;
    payload["temperature"] = 0.2;

    // If your backend supports it later
    payload["model"] = m_currentModel;

    startStreamRequest(mkJsonBody(payload));
}

void CerebrumClient::startStreamRequest(const QByteArray &jsonBody)
{
    // Pause health polling during active stream
    if (m_healthTimer.isActive())
        m_healthTimer.stop();

    QNetworkRequest req(QUrl(apiBase() + STREAM_EP));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setHeader(QNetworkRequest::UserAgentHeader, "CerebrumGUI/1.0");
    req.setRawHeader("Accept", "text/event-stream");

    // Discourage HTTP2 for more SSE-friendly behavior
    req.setAttribute(QNetworkRequest::Http2AllowedAttribute, false);
    req.setRawHeader("Cache-Control", "no-cache");
    req.setRawHeader("Connection", "keep-alive");

    m_streamReply = m_net.post(req, jsonBody);

    setGenerating(true);

    connect(m_streamReply, &QNetworkReply::readyRead, this, &CerebrumClient::handleSseReadyRead);

    connect(m_streamReply, &QNetworkReply::finished, this, [this]() {
        // Pull any final bytes and flush remainder before closing
        if (m_streamReply) {
            m_sseBuffer += m_streamReply->readAll();
        }
        processSseBuffer(true); // flush remainder!

        // if processSseBuffer() hit done/error it already finalized+returned,
        // but calling finalizeStream()again is harmless due to guards
        finalizeStream();
    });

    connect(m_streamReply, &QNetworkReply::errorOccurred, this, [this](QNetworkReply::NetworkError) {
        if (m_streamReply) {
            emit generationError(m_streamReply->errorString());
        } else {
            emit generationError("Network error.");
        }
        finalizeStream();
    });
}

void CerebrumClient::processSseBuffer(bool flushRemainder)
{
    // Debug: log what we're receiving
    static int callCount = 0;
    callCount++;
    
    // #ifdef QT_DEBUG
    qDebug() << "=== processSseBuffer call" << callCount << "===";
    qDebug() << "Buffer size:" << m_sseBuffer.size();
    if (!m_sseBuffer.isEmpty()) {
        qDebug() << "Buffer start:" << QString(m_sseBuffer.left(200)).toHtmlEscaped();
        qDebug() << "Buffer hex:" << m_sseBuffer.left(50).toHex();
    }
    
    // Process all complete events in buffer
    while (!m_sseBuffer.isEmpty()) {
        // Find next event boundary
        int eventEnd = -1;
        int boundaryLength = 0;
        
        // Check for \n\n
        eventEnd = m_sseBuffer.indexOf("\n\n");
        if (eventEnd != -1) {
            boundaryLength = 2;
        } else {
            // Check for \r\n\r\n
            eventEnd = m_sseBuffer.indexOf("\r\n\r\n");
            if (eventEnd != -1) {
                boundaryLength = 4;
            }
        }
        
        if (eventEnd == -1) {
            // No complete event found
            qDebug() << "No complete event found, waiting for more data";
            if (flushRemainder) {
                qDebug() << "Flushing remainder of size:" << m_sseBuffer.size();
                // Handle remaining data
                if (!m_sseBuffer.isEmpty()) {
                    parseSingleEvent(m_sseBuffer + "\n\n");
                }
                m_sseBuffer.clear();
            }
            break;
        }
        
        qDebug() << "Found event boundary at index" << eventEnd << "length" << boundaryLength;
        
        // Extract and parse the complete event
        QByteArray event = m_sseBuffer.left(eventEnd + boundaryLength);
        m_sseBuffer.remove(0, eventEnd + boundaryLength);
        
        qDebug() << "Processing event of size:" << event.size();
        qDebug() << "Event content:" << QString(event).toHtmlEscaped();
        // #endif

        // Clean up line endings for parsing
        event.replace("\r\n", "\n");
        
        // Remove the trailing blank line(s)
        if (event.endsWith("\n\n")) {
            event.chop(2);
        }
        
        parseSingleEvent(event);
    }
}

void CerebrumClient::parseSingleEvent(const QByteArray &event)
{
    qDebug() << "parseSingleEvent called with:" << event;
    
    // Split into lines
    const QList<QByteArray> lines = event.split('\n');
    for (const QByteArray &line : lines) {
        if (!line.startsWith("data:"))
            continue;

        // Extract JSON data after "data:"
        QByteArray jsonData = line.mid(5).trimmed();
        if (jsonData.isEmpty())
            continue;
            
        qDebug() << "Found JSON data:" << jsonData;
        
        // Parse JSON
        QJsonParseError parseError{};
        QJsonDocument doc = QJsonDocument::fromJson(jsonData, &parseError);
        
        if (parseError.error != QJsonParseError::NoError) {
            qWarning() << "JSON parse error:" << parseError.errorString();
            continue;
        }
        
        if (!doc.isObject()) {
            qWarning() << "JSON is not an object";
            continue;
        }
        
        QJsonObject obj = doc.object();
        
        // Check for done flag
        if (obj.contains("done") && obj["done"].toBool()) {
            qDebug() << "Generation complete";
            emit generationFinished(
                obj.value("total_tokens").toInt(),
                obj.value("inference_time").toDouble()
            );
            finalizeStream();
            return;
        }
        
        // Check for error
        if (obj.contains("error") && obj["error"].toBool()) {
            QString errorMsg = obj.value("message").toString("Unknown error");
            qWarning() << "Generation error:" << errorMsg;
            emit generationError(errorMsg);
            finalizeStream();
            return;
        }
        
        // Check for token
        if (obj.contains("token") && obj["token"].isString()) {
            QString token = obj["token"].toString();
            if (!token.isEmpty()) {
                qDebug() << "Emitting token:" << token;
                emit tokenReceived(token);
            }
        } else {
            qDebug() << "No token in object, keys:" << obj.keys();
        }
    }
}

void CerebrumClient::handleSseReadyRead()
{
    if (!m_streamReply)
        return;
    
    // Read all available data
    QByteArray newData = m_streamReply->readAll();
    if (!newData.isEmpty()) {
        qDebug() << "Received" << newData.size() << "bytes";
        m_sseBuffer.append(newData);
        processSseBuffer(false);
    }
}

void CerebrumClient::finalizeStream()
{
    if (m_streamReply) {
        m_streamReply->disconnect(this);
        m_streamReply->deleteLater();
        m_streamReply = nullptr;
    }
    m_sseBuffer.clear();
    setGenerating(false);

    // Resume health polling
    if (!m_healthTimer.isActive())
    m_healthTimer.start();
}

void CerebrumClient::setOrchestratorRunning(bool v)
{
    if (m_orchestratorRunning == v) return;
    m_orchestratorRunning = v;
    emit orchestratorRunningChanged();
}

void CerebrumClient::setVpsConnected(bool v)
{
    if (m_vpsConnected == v) return;
    m_vpsConnected = v;
    emit vpsConnectedChanged();
}

void CerebrumClient::setModelLoaded(bool v)
{
    if (m_modelLoaded == v) return;
    m_modelLoaded = v;
    emit modelLoadedChanged();
}

void CerebrumClient::setCurrentModel(const QString &m)
{
    const QString pretty = prettyModelName(m);
    if (m_currentModel == pretty) 
        return;
    m_currentModel = pretty;
    emit currentModelChanged();
}

void CerebrumClient::setGenerating(bool v)
{
    if (m_generating == v) return;
    m_generating = v;
    emit generatingChanged();
}
