#pragma once

#include <QObject>
#include <QStringList>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QTimer>

class CerebrumClient : public QObject {
    Q_OBJECT

    // Status
    Q_PROPERTY(bool vpsConnected READ vpsConnected NOTIFY vpsConnectedChanged)
    Q_PROPERTY(bool orchestratorRunning READ orchestratorRunning NOTIFY orchestratorRunningChanged)
    // Derived health state (with hysteresis)
    Q_PROPERTY(HealthState orchestratorState READ orchestratorState NOTIFY healthStateChanged)
    Q_PROPERTY(HealthState vpsState READ vpsState NOTIFY healthStateChanged)

    // Model
    Q_PROPERTY(bool modelLoaded READ modelLoaded NOTIFY modelLoadedChanged)
    Q_PROPERTY(QString currentModel READ currentModel NOTIFY currentModelChanged)
    Q_PROPERTY(QString modelStatusText READ modelStatusText NOTIFY modelLoadedChanged)
    // Q_PROPERTY(QStringList availableModels READ availableModels NOTIFY availableModelsChanged)

    // Generation
    Q_PROPERTY(bool generating READ generating NOTIFY generatingChanged)

    // Footer metrics (basic)
    Q_PROPERTY(int activeCount READ activeCount NOTIFY metricsChanged)
    Q_PROPERTY(int queueCount READ queueCount NOTIFY metricsChanged)
    Q_PROPERTY(QString uptimeText READ uptimeText NOTIFY metricsChanged)

    // CM4 CPU
    Q_PROPERTY(double cpuPercent READ cpuPercent NOTIFY metricsChanged)

public:
    enum HealthState {
        HealthGood = 0,
        HealthWarning = 1,
        HealthDown = 2
    };
    Q_ENUM(HealthState)

    explicit CerebrumClient(QObject *parent = nullptr);

    // UI actions
    Q_INVOKABLE void refresh();
    Q_INVOKABLE void sendPrompt(const QString &prompt);
    // Q_INVOKABLE void openModelMenu();   // no-op; QML uses availableModels
    // Q_INVOKABLE void selectModel(const QString &modelName);

    // Property accessors
    bool vpsConnected() const { return m_vpsConnected; }
    bool orchestratorRunning() const { return m_orchestratorRunning; }
    
    HealthState orchestratorState() const { return m_orchestratorState; }
    HealthState vpsState() const { return m_vpsState; }

    bool modelLoaded() const { return m_modelLoaded; }
    QString currentModel() const { return m_currentModel; }
    QString modelStatusText() const { return m_modelLoaded ? "Model: Selected" : "Model: Not Selected"; }
    //QStringList availableModels() const { return m_availableModels; }

    bool generating() const { return m_generating; }

    int activeCount() const { return m_activeCount; }
    int queueCount() const { return m_queueCount; }
    QString uptimeText() const { return m_uptimeText; }

    double cpuPercent() const { return m_cpuPercent; }

signals:
    // Status
    void vpsConnectedChanged();
    void orchestratorRunningChanged();
    void healthStateChanged();

    // Model
    void modelLoadedChanged();
    void currentModelChanged();
    void availableModelsChanged();

    // Generation
    void generatingChanged();
    void tokenReceived(const QString &token);
    void generationFinished(int totalTokens, double inferenceTimeSeconds);
    void generationError(const QString &message);

    // Metrics/UI
    void metricsChanged();
    void resetComplete(); // use to restart ASCII animation + confirm refresh

private:
    // Helper for dynamic API_BASE
    QString apiBase() const;
    // ---- Configuration (adjust here only if endpoints change) ----
    const QString API_BASE = "http://localhost:7000";
    const QString HEALTH_EP = "/health";
    const QString STREAM_EP = "/v1/complete/stream";

    // Optional endpoints (if your orchestrator implements them later)
    const QString MODELS_EP_1 = "/v1/models";          // GET
    const QString MODELS_EP_2 = "/models";             // GET fallback
    const QString SELECT_MODEL_EP = "/v1/model/select"; // POST {model:"..."}

    // Defaults used if models endpoint isn't present yet
    QStringList DEFAULT_MODELS = {"Llama 3.2 3B", "Qwen 7B", "Phi-3 Mini"};

    // ---- Internal helpers ----
    void checkHealth();
    void fetchModels();
    void setOrchestratorRunning(bool v);
    void setVpsConnected(bool v);
    void setModelLoaded(bool v);
    void setCurrentModel(const QString &m);
    void setGenerating(bool v);

    void resetMetrics();
    void updateMetricsFromHealthJson(const QByteArray &json);

    // Streaming SSE parsing
    void startStreamRequest(const QByteArray &jsonBody);
    void processSseBuffer(bool flushRemainder = false);
    void handleSseReadyRead();
    void finalizeStream();

    void parseSingleEvent(const QByteArray &event);

private:
    QNetworkAccessManager m_net;
    QNetworkReply *m_streamReply = nullptr;
    QByteArray m_sseBuffer;

    // Health hysteresis
    int m_orchestratorMisses = 0;
    int m_vpsMisses = 0;
    
    HealthState m_orchestratorState = HealthDown;
    HealthState m_vpsState = HealthDown;

    // State
    bool m_vpsConnected = false;
    bool m_orchestratorRunning = false;

    bool m_modelLoaded = false;
    QString m_currentModel = "idle";
    QStringList m_availableModels;

    bool m_generating = false;

    int m_activeCount = 0;
    int m_queueCount = 0; // left unwired; keep 0 for now unless health provides it
    QString m_uptimeText = "Uptime: 0h 0m";

    double m_cpuPercent = 0.0;
    // Periodic health polling (optional)
    QTimer m_healthTimer;
};
