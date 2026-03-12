# Enterprise Observability Platform (EOP)

> Unified, OTel-standardized observability across Infrastructure, Applications, Network, Events, and Alerting domains — with an enterprise data catalogue powered by OpenMetadata.

---

## Repository Structure

```
enterprise-observability-platform/
├── collectors/                     # Data collection & normalization configs
│   ├── telegraf/                   # Infrastructure metrics (Cloud Insights)
│   ├── otel-collector/             # Central OTel Collector (all domains)
│   ├── fluent-bit/                 # Log forwarding (Loki / ClickHouse)
│   ├── logstash/                   # Splunk / AppDynamics log normalization
│   ├── vector/                     # High-performance log/metric pipeline
│   └── prometheus-exporters/       # Network & infra Prometheus exporters
├── catalog/                        # OpenMetadata enterprise catalogue
│   ├── openmetadata/               # Connector configs per domain
│   ├── schemas/                    # OTel semantic convention schemas
│   └── scripts/                    # Automation: ingest, tag, lineage
├── governance/                     # Data quality & retention rules
│   ├── data-quality/               # Great Expectations suites per domain
│   └── retention-policies/         # Kafka & storage retention configs
└── docs/                           # Architecture & onboarding guides
```

---

## Domains Covered

| Domain | Tools | Collector | OTel Signal |
|---|---|---|---|
| Infrastructure | Grafana, VictoriaMetrics | Telegraf + OTel | Metrics, Logs |
| Applications | AppDynamics, Dynatrace, New Relic | OTel Collector | Traces, Metrics, Logs |
| Network | ThousandEyes, Logic Monitor, Selector | Prometheus Exporter + OTel | Metrics, Flows |
| Events | Moogsoft, Splunk ITSI | Vector + OTel | Logs (Events) |
| Alerting | ServiceNow, Grafana AM | Logstash + OTel | Logs (Alerts) |

---

## Key Standards

- **Protocol**: OTLP/gRPC (primary), OTLP/HTTP (fallback)
- **Semantic Conventions**: [OpenTelemetry Semantic Conventions v1.24](https://opentelemetry.io/docs/specs/semconv/)
- **Schema Registry**: Confluent Schema Registry (Avro/Protobuf)
- **Catalogue**: OpenMetadata with Unity Catalog sync
- **Data Quality**: Great Expectations + Databricks DQ

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-org/enterprise-observability-platform.git
cd enterprise-observability-platform

# 2. Deploy OTel Collector (infra domain example)
kubectl apply -f collectors/otel-collector/infra/otel-collector-infra.yaml

# 3. Deploy Telegraf
kubectl apply -f collectors/telegraf/telegraf-configmap.yaml

# 4. Bootstrap OpenMetadata catalog
cd catalog/scripts
pip install -r requirements.txt
python bootstrap_catalog.py --domain all

# 5. Run Data Quality checks
cd governance/data-quality
pip install great_expectations
great_expectations checkpoint run infra_metrics_checkpoint
```

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full reference architecture.

---

## Contributing

Each domain has an **owner team**. All collector configs must:
1. Follow OTel semantic conventions for attribute naming
2. Include a `service.name`, `host.name`, `deployment.environment` resource attribute
3. Pass the domain DQ checkpoint before merging to `main`

---

## License

Internal — Enterprise Observability Platform Team
