"""
catalog/core/lineage.py
Build end-to-end data lineage in OpenMetadata for all EOP domains.

Lineage graph:
  Source Tool
    → OTel Collector (normalization)
      → Kafka Topic (streaming pipeline)
        → Databricks Delta Lake (analytical lakehouse)
          → Databricks Dashboard / ML Model
"""

import logging
from typing import List

from metadata.generated.schema.api.lineage.addLineage import AddLineageRequest
from metadata.generated.schema.type.entityLineage import EntitiesEdge, LineageDetails
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.ingestion.ometa.ometa_api import OpenMetadata

log = logging.getLogger("eop.catalog.lineage")


# ── Lineage node definitions ──────────────────────────────────────────────────

LINEAGE_GRAPH = [
    # ── Infrastructure ────────────────────────────────────────────────────────
    {
        "pipeline_name": "infra-metrics-pipeline",
        "description":   "Infrastructure metrics: Telegraf → OTel → Kafka → Databricks",
        "edges": [
            # Telegraf agent → OTel Collector
            ("pipeline", "telegraf-infra-agent",        "pipeline", "otel-collector-infra"),
            # OTel Collector → Kafka topic
            ("pipeline", "otel-collector-infra",         "topic",    "infra.metrics"),
            ("pipeline", "otel-collector-infra",         "topic",    "infra.logs"),
            # Kafka → Databricks Delta tables
            ("topic",    "infra.metrics",                "table",    "eop-infrastructure.eop_infrastructure.infra_metrics.otel_metrics_cpu"),
            ("topic",    "infra.metrics",                "table",    "eop-infrastructure.eop_infrastructure.infra_metrics.otel_metrics_memory"),
            ("topic",    "infra.metrics",                "table",    "eop-infrastructure.eop_infrastructure.infra_metrics.otel_metrics_disk"),
            ("topic",    "infra.metrics",                "table",    "eop-infrastructure.eop_infrastructure.infra_metrics.otel_metrics_network"),
            ("topic",    "infra.logs",                   "table",    "eop-infrastructure.eop_infrastructure.infra_logs.otel_logs_infra"),
            # Delta → Databricks dashboard
            ("table",    "eop-infrastructure.eop_infrastructure.infra_metrics.otel_metrics_cpu",
             "dashboard","databricks.infra-health-dashboard"),
        ],
    },

    # ── Applications ──────────────────────────────────────────────────────────
    {
        "pipeline_name": "app-traces-pipeline",
        "description":   "Application traces: APM agents → OTel → Kafka → Databricks",
        "edges": [
            ("pipeline", "appdynamics-agent",            "pipeline", "otel-collector-apps"),
            ("pipeline", "dynatrace-oneagent",           "pipeline", "otel-collector-apps"),
            ("pipeline", "newrelic-agent",               "pipeline", "otel-collector-apps"),
            ("pipeline", "otel-collector-apps",          "topic",    "app.traces"),
            ("pipeline", "otel-collector-apps",          "topic",    "app.metrics"),
            ("pipeline", "otel-collector-apps",          "topic",    "app.logs"),
            ("topic",    "app.traces",                   "table",    "eop-applications.eop_applications.app_traces.otel_spans"),
            ("topic",    "app.metrics",                  "table",    "eop-applications.eop_applications.app_metrics.otel_metrics_http_server"),
            ("topic",    "app.logs",                     "table",    "eop-applications.eop_applications.app_logs.otel_logs_app"),
            ("table",    "eop-applications.eop_applications.app_traces.otel_spans",
             "dashboard","databricks.app-slo-dashboard"),
        ],
    },

    # ── Network ───────────────────────────────────────────────────────────────
    {
        "pipeline_name": "network-metrics-pipeline",
        "description":   "Network metrics: ThousandEyes/SNMP → OTel → Kafka → Databricks",
        "edges": [
            ("pipeline", "thousandeyes-exporter",        "pipeline", "otel-collector-network"),
            ("pipeline", "logicmonitor-exporter",        "pipeline", "otel-collector-network"),
            ("pipeline", "snmp-exporter",                "pipeline", "otel-collector-network"),
            ("pipeline", "otel-collector-network",       "topic",    "net.metrics"),
            ("pipeline", "otel-collector-network",       "topic",    "net.flows"),
            ("topic",    "net.metrics",                  "table",    "eop-network.eop_network.network_metrics.otel_metrics_connectivity"),
            ("topic",    "net.metrics",                  "table",    "eop-network.eop_network.network_metrics.otel_metrics_network_interface"),
            ("topic",    "net.flows",                    "table",    "eop-network.eop_network.network_flows.otel_flows_network"),
        ],
    },

    # ── Events ────────────────────────────────────────────────────────────────
    {
        "pipeline_name": "events-pipeline",
        "description":   "Events: Moogsoft/ITSI → Vector → Kafka → Enrichment → Databricks",
        "edges": [
            ("pipeline", "moogsoft-webhook",             "pipeline", "vector-events"),
            ("pipeline", "splunk-itsi-hec",              "pipeline", "vector-events"),
            ("pipeline", "vector-events",                "topic",    "events.raw"),
            ("topic",    "events.raw",                   "pipeline", "flink-event-enrichment"),
            ("pipeline", "flink-event-enrichment",       "topic",    "events.correlated"),
            ("topic",    "events.correlated",            "topic",    "events.enriched"),
            ("topic",    "events.enriched",              "table",    "eop-events.eop_events.events_enriched.otel_events_enriched"),
            ("table",    "eop-events.eop_events.events_enriched.otel_events_enriched",
             "table",    "eop-alerting.eop_alerting.alerts_processed.otel_incidents"),
        ],
    },

    # ── Alerting ──────────────────────────────────────────────────────────────
    {
        "pipeline_name": "alerts-pipeline",
        "description":   "Alerts: Grafana AM / ServiceNow → Logstash → Kafka → Databricks",
        "edges": [
            ("pipeline", "grafana-alertmanager",         "pipeline", "logstash-alerts"),
            ("pipeline", "servicenow-events",            "pipeline", "logstash-alerts"),
            ("pipeline", "logstash-alerts",              "topic",    "alerts.raw"),
            ("topic",    "alerts.raw",                   "table",    "eop-alerting.eop_alerting.alerts_raw.otel_alerts_raw"),
            ("topic",    "alerts.raw",                   "pipeline", "vector-dedup"),
            ("pipeline", "vector-dedup",                 "topic",    "alerts.deduped"),
            ("topic",    "alerts.deduped",               "table",    "eop-alerting.eop_alerting.alerts_processed.otel_alerts_deduped"),
            ("table",    "eop-alerting.eop_alerting.alerts_processed.otel_alerts_deduped",
             "dashboard","databricks.alert-intelligence-dashboard"),
        ],
    },

    # ── Cross-domain correlation ──────────────────────────────────────────────
    {
        "pipeline_name": "cross-domain-correlation",
        "description":   "Cross-domain join: infra + app + network + events → Databricks analytics",
        "edges": [
            ("table",    "eop-infrastructure.eop_infrastructure.infra_metrics.otel_metrics_cpu",
             "table",    "databricks.eop_analytics.cross_domain_correlation"),
            ("table",    "eop-applications.eop_applications.app_traces.otel_spans",
             "table",    "databricks.eop_analytics.cross_domain_correlation"),
            ("table",    "eop-network.eop_network.network_metrics.otel_metrics_connectivity",
             "table",    "databricks.eop_analytics.cross_domain_correlation"),
            ("table",    "eop-events.eop_events.events_enriched.otel_events_enriched",
             "table",    "databricks.eop_analytics.cross_domain_correlation"),
            ("table",    "databricks.eop_analytics.cross_domain_correlation",
             "dashboard","databricks.executive-reliability-dashboard"),
        ],
    },
]


def build_lineage_graph(
    client: OpenMetadata,
    domain,
    dry_run: bool = False,
) -> None:
    """
    Build lineage edges for a single domain in OpenMetadata.
    Only processes lineage graphs where the pipeline_name starts with the domain name.
    """
    domain_prefix = domain.domain_name

    relevant_graphs = [
        g for g in LINEAGE_GRAPH
        if domain_prefix in g["pipeline_name"] or "cross-domain" in g["pipeline_name"]
    ]

    for graph in relevant_graphs:
        log.info(f"  Building lineage: {graph['pipeline_name']}")
        for source_type, source_fqn, dest_type, dest_fqn in graph["edges"]:
            if dry_run:
                log.info(f"    [DRY RUN] {source_type}:{source_fqn} → {dest_type}:{dest_fqn}")
                continue
            try:
                _add_lineage_edge(client, source_type, source_fqn, dest_type, dest_fqn)
                log.debug(f"    ✓ {source_fqn} → {dest_fqn}")
            except Exception as e:
                log.warning(f"    ⚠ Could not add lineage edge {source_fqn} → {dest_fqn}: {e}")


def _add_lineage_edge(
    client: OpenMetadata,
    source_type: str,
    source_fqn: str,
    dest_type: str,
    dest_fqn: str,
) -> None:
    """Add a single directed lineage edge in OpenMetadata."""
    entity_type_map = {
        "table":     "table",
        "pipeline":  "pipeline",
        "topic":     "topic",
        "dashboard": "dashboard",
    }

    source_ref = EntityReference(
        type=entity_type_map[source_type],
        fullyQualifiedName=source_fqn,
    )
    dest_ref = EntityReference(
        type=entity_type_map[dest_type],
        fullyQualifiedName=dest_fqn,
    )

    lineage_request = AddLineageRequest(
        edge=EntitiesEdge(
            fromEntity=source_ref,
            toEntity=dest_ref,
            lineageDetails=LineageDetails(
                description="EOP automated lineage"
            ),
        )
    )
    client.add_lineage(lineage_request)
