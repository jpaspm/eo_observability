"""
catalog/domains/applications.py
catalog/domains/network.py
catalog/domains/events.py
catalog/domains/alerting.py

OpenMetadata catalog registrations for all remaining EOP domains.
All four domains are defined in this module for brevity.
"""

from typing import List
from metadata.generated.schema.entity.data.table import Column, DataType, TableType
from catalog.core.base_domain import BaseDomain, TableDefinition, EOP_TAGS


# =============================================================================
# APPLICATIONS DOMAIN
# =============================================================================

class ApplicationsDomain(BaseDomain):
    domain_name  = "applications"
    service_name = "eop-applications"
    owner_team   = "platform-apm-team"
    description  = """
**Applications Observability Domain**

APM telemetry from AppDynamics, Dynatrace, New Relic, and Splunk APM.
Normalized to OTel trace/span/metric model with W3C TraceContext propagation.

**OTel Signals:** Traces, Metrics (RED), Logs  
**Semantic Conventions:** `http.*`, `db.*`, `rpc.*`, `messaging.*`  
**Retention:** Hot 7d | Warm 90d | Cold 3yr
"""

    def get_table_definitions(self) -> List[TableDefinition]:
        return [
            self._otel_traces(),
            self._otel_spans(),
            self._otel_metrics_http(),
            self._otel_metrics_jvm(),
            self._otel_logs_app(),
        ]

    def _otel_traces(self) -> TableDefinition:
        return TableDefinition(
            name="otel_traces",
            schema_name="app_traces",
            description="OTel distributed traces. One row per trace (aggregate of spans).",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="trace_id",              dataType=DataType.VARCHAR,   description="W3C TraceID (128-bit hex)"),
                Column(name="root_span_id",          dataType=DataType.VARCHAR,   description="Root span ID"),
                Column(name="root_service_name",     dataType=DataType.VARCHAR,   description="Service that initiated the trace"),
                Column(name="root_operation_name",   dataType=DataType.VARCHAR,   description="Root span name (e.g. HTTP GET /api/v1/users)"),
                Column(name="trace_duration_ms",     dataType=DataType.DOUBLE,    description="Total trace duration in milliseconds"),
                Column(name="span_count",            dataType=DataType.INT,       description="Number of spans in trace"),
                Column(name="error_span_count",      dataType=DataType.INT,       description="Spans with error status"),
                Column(name="has_error",             dataType=DataType.BOOLEAN,   description="True if any span has ERROR status"),
                Column(name="status_code",           dataType=DataType.VARCHAR,   description="OTel status code: OK|ERROR|UNSET"),
                Column(name="source_tool",           dataType=DataType.VARCHAR,   description="Originating APM tool (appdynamics|dynatrace|newrelic|otel)"),
            ]
        )

    def _otel_spans(self) -> TableDefinition:
        return TableDefinition(
            name="otel_spans",
            schema_name="app_traces",
            description="OTel individual spans. Core table for trace analysis and RED metrics.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="trace_id",              dataType=DataType.VARCHAR),
                Column(name="span_id",               dataType=DataType.VARCHAR,   description="OTel SpanID (64-bit hex)"),
                Column(name="parent_span_id",        dataType=DataType.VARCHAR,   description="Parent SpanID (null for root spans)"),
                Column(name="span_name",             dataType=DataType.VARCHAR,   description="OTel span name"),
                Column(name="span_kind",             dataType=DataType.VARCHAR,   description="INTERNAL|SERVER|CLIENT|PRODUCER|CONSUMER"),
                Column(name="start_time_unix_nano",  dataType=DataType.BIGINT),
                Column(name="end_time_unix_nano",    dataType=DataType.BIGINT),
                Column(name="duration_ms",           dataType=DataType.DOUBLE,    description="Span duration in milliseconds"),
                Column(name="status_code",           dataType=DataType.VARCHAR),
                Column(name="status_message",        dataType=DataType.TEXT),
                Column(name="http_method",           dataType=DataType.VARCHAR,   description="OTel: http.request.method"),
                Column(name="http_url",              dataType=DataType.VARCHAR,   description="OTel: url.full"),
                Column(name="http_status_code",      dataType=DataType.INT,       description="OTel: http.response.status_code"),
                Column(name="http_route",            dataType=DataType.VARCHAR,   description="OTel: http.route"),
                Column(name="db_system",             dataType=DataType.VARCHAR,   description="OTel: db.system (postgresql|mysql|redis...)"),
                Column(name="db_name",               dataType=DataType.VARCHAR,   description="OTel: db.name"),
                Column(name="db_operation",          dataType=DataType.VARCHAR,   description="OTel: db.operation"),
                Column(name="peer_service",          dataType=DataType.VARCHAR,   description="OTel: peer.service (downstream service)"),
                Column(name="slo_error_budget_impact", dataType=DataType.BOOLEAN, description="EOP: impacts SLO error budget"),
            ]
        )

    def _otel_metrics_http(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_http_server",
            schema_name="app_metrics",
            description="OTel `http.server.*` metrics (RED: Requests, Errors, Duration). Generated from span metrics.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",               dataType=DataType.VARCHAR),
                Column(name="metric_value",              dataType=DataType.DOUBLE),
                Column(name="http_request_method",       dataType=DataType.VARCHAR,  description="OTel: http.request.method"),
                Column(name="http_response_status_code", dataType=DataType.INT,      description="OTel: http.response.status_code"),
                Column(name="http_route",                dataType=DataType.VARCHAR),
                Column(name="url_scheme",                dataType=DataType.VARCHAR,  description="OTel: url.scheme (http|https)"),
                Column(name="server_address",            dataType=DataType.VARCHAR,  description="OTel: server.address"),
                Column(name="server_port",               dataType=DataType.INT,      description="OTel: server.port"),
                Column(name="p50_duration_ms",           dataType=DataType.DOUBLE,   description="50th percentile latency"),
                Column(name="p95_duration_ms",           dataType=DataType.DOUBLE,   description="95th percentile latency"),
                Column(name="p99_duration_ms",           dataType=DataType.DOUBLE,   description="99th percentile latency"),
                Column(name="error_rate",                dataType=DataType.DOUBLE,   description="Errors / Total requests"),
            ]
        )

    def _otel_metrics_jvm(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_jvm",
            schema_name="app_metrics",
            description="OTel `jvm.*` metrics. JVM heap, GC, threads, and class loading.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",               dataType=DataType.VARCHAR),
                Column(name="metric_value",              dataType=DataType.DOUBLE),
                Column(name="jvm_memory_type",           dataType=DataType.VARCHAR,  description="OTel: jvm.memory.type (heap|non_heap)"),
                Column(name="jvm_memory_pool_name",      dataType=DataType.VARCHAR,  description="OTel: jvm.memory.pool.name"),
                Column(name="jvm_gc_name",               dataType=DataType.VARCHAR,  description="OTel: jvm.gc.name"),
                Column(name="jvm_gc_action",             dataType=DataType.VARCHAR,  description="OTel: jvm.gc.action"),
                Column(name="jvm_thread_state",          dataType=DataType.VARCHAR,  description="OTel: jvm.thread.state"),
            ]
        )

    def _otel_logs_app(self) -> TableDefinition:
        return TableDefinition(
            name="otel_logs_app",
            schema_name="app_logs",
            description="OTel LogRecords from application services. Includes trace correlation.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="severity_number",   dataType=DataType.INT),
                Column(name="severity_text",     dataType=DataType.VARCHAR),
                Column(name="body",              dataType=DataType.TEXT),
                Column(name="trace_id",          dataType=DataType.VARCHAR),
                Column(name="span_id",           dataType=DataType.VARCHAR),
                Column(name="code_filepath",     dataType=DataType.VARCHAR,  description="OTel: code.filepath"),
                Column(name="code_function",     dataType=DataType.VARCHAR,  description="OTel: code.function"),
                Column(name="code_lineno",       dataType=DataType.INT,      description="OTel: code.lineno"),
                Column(name="thread_id",         dataType=DataType.VARCHAR,  description="OTel: thread.id"),
                Column(name="thread_name",       dataType=DataType.VARCHAR,  description="OTel: thread.name"),
                Column(name="exception_type",    dataType=DataType.VARCHAR,  description="OTel: exception.type"),
                Column(name="exception_message", dataType=DataType.TEXT,     description="OTel: exception.message"),
                Column(name="eop_fingerprint",   dataType=DataType.VARCHAR),
            ]
        )


# =============================================================================
# NETWORK DOMAIN
# =============================================================================

class NetworkDomain(BaseDomain):
    domain_name  = "network"
    service_name = "eop-network"
    owner_team   = "platform-network-team"
    description  = """
**Network Observability Domain**

Network telemetry from ThousandEyes, Logic Monitor, Selector AI, and SNMP polling.
Metrics mapped to OTel `network.*` and `system.network.*` conventions.

**OTel Signals:** Metrics, Flows  
**Source Tools:** ThousandEyes, Logic Monitor, Selector AI, SNMP Exporter  
**Retention:** Hot 14d | Warm 1yr | Cold 7yr
"""

    def get_table_definitions(self) -> List[TableDefinition]:
        return [
            self._otel_metrics_interface(),
            self._otel_metrics_connectivity(),
            self._otel_metrics_device(),
            self._otel_flows(),
        ]

    def _otel_metrics_interface(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_network_interface",
            schema_name="network_metrics",
            description="OTel `system.network.*` interface metrics from SNMP and Logic Monitor.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",                       dataType=DataType.VARCHAR),
                Column(name="metric_value",                      dataType=DataType.DOUBLE),
                Column(name="network_interface_name",            dataType=DataType.VARCHAR,  description="OTel: network.interface.name"),
                Column(name="network_interface_index",           dataType=DataType.INT),
                Column(name="network_interface_speed_mbps",      dataType=DataType.DOUBLE,   description="Interface max bandwidth in Mbps"),
                Column(name="network_interface_status",          dataType=DataType.VARCHAR,  description="up|down|testing"),
                Column(name="network_interface_receive_bytes",   dataType=DataType.BIGINT),
                Column(name="network_interface_transmit_bytes",  dataType=DataType.BIGINT),
                Column(name="network_interface_errors_receive",  dataType=DataType.BIGINT),
                Column(name="network_interface_errors_transmit", dataType=DataType.BIGINT),
                Column(name="net_device_name",                   dataType=DataType.VARCHAR,  description="Network device hostname"),
                Column(name="net_device_ip",                     dataType=DataType.VARCHAR,  description="Network device management IP"),
                Column(name="net_device_type",                   dataType=DataType.VARCHAR,  description="router|switch|firewall|load-balancer"),
            ]
        )

    def _otel_metrics_connectivity(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_connectivity",
            schema_name="network_metrics",
            description="ThousandEyes connectivity metrics: latency, loss, jitter, path trace.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",               dataType=DataType.VARCHAR),
                Column(name="metric_value",              dataType=DataType.DOUBLE),
                Column(name="network_test_name",         dataType=DataType.VARCHAR,  description="ThousandEyes test name"),
                Column(name="network_test_type",         dataType=DataType.VARCHAR,  description="http|agent-to-agent|dns|voice"),
                Column(name="network_agent_name",        dataType=DataType.VARCHAR,  description="ThousandEyes agent"),
                Column(name="network_target_host",       dataType=DataType.VARCHAR,  description="Target hostname or IP"),
                Column(name="network_latency_ms",        dataType=DataType.DOUBLE),
                Column(name="network_jitter_ms",         dataType=DataType.DOUBLE),
                Column(name="network_packet_loss_rate",  dataType=DataType.DOUBLE,   description="Packet loss ratio (0.0–1.0)"),
                Column(name="network_path_hops",         dataType=DataType.INT,      description="Number of hops in path trace"),
                Column(name="network_http_response_time",dataType=DataType.DOUBLE,   description="End-to-end HTTP response time ms"),
                Column(name="network_http_status_code",  dataType=DataType.INT),
            ]
        )

    def _otel_metrics_device(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_network_device",
            schema_name="network_metrics",
            description="Network device CPU/memory metrics (Cisco, Juniper, Arista) via SNMP.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",              dataType=DataType.VARCHAR),
                Column(name="metric_value",             dataType=DataType.DOUBLE),
                Column(name="net_device_name",          dataType=DataType.VARCHAR),
                Column(name="net_device_type",          dataType=DataType.VARCHAR),
                Column(name="net_device_vendor",        dataType=DataType.VARCHAR,  description="cisco|juniper|arista|palo-alto"),
                Column(name="net_device_model",         dataType=DataType.VARCHAR),
                Column(name="net_device_os_version",    dataType=DataType.VARCHAR),
                Column(name="system_cpu_utilization",   dataType=DataType.DOUBLE),
                Column(name="system_memory_utilization",dataType=DataType.DOUBLE),
                Column(name="system_memory_pool_name",  dataType=DataType.VARCHAR),
            ]
        )

    def _otel_flows(self) -> TableDefinition:
        return TableDefinition(
            name="otel_flows_network",
            schema_name="network_flows",
            description="NetFlow/sFlow network flow records normalized to OTel attributes.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="source_address",       dataType=DataType.VARCHAR,  description="OTel: source.address"),
                Column(name="destination_address",  dataType=DataType.VARCHAR,  description="OTel: destination.address"),
                Column(name="source_port",          dataType=DataType.INT,      description="OTel: source.port"),
                Column(name="destination_port",     dataType=DataType.INT,      description="OTel: destination.port"),
                Column(name="network_protocol",     dataType=DataType.VARCHAR,  description="OTel: network.protocol.name (tcp|udp|icmp)"),
                Column(name="network_bytes",        dataType=DataType.BIGINT,   description="Bytes transferred"),
                Column(name="network_packets",      dataType=DataType.BIGINT,   description="Packets transferred"),
                Column(name="flow_direction",       dataType=DataType.VARCHAR,  description="ingress|egress"),
                Column(name="flow_start_ns",        dataType=DataType.BIGINT),
                Column(name="flow_end_ns",          dataType=DataType.BIGINT),
                Column(name="flow_sampler_name",    dataType=DataType.VARCHAR,  description="Exporting device"),
            ]
        )


# =============================================================================
# EVENTS DOMAIN
# =============================================================================

class EventsDomain(BaseDomain):
    domain_name  = "events"
    service_name = "eop-events"
    owner_team   = "platform-events-team"
    description  = """
**Events Observability Domain**

AIOps events from Moogsoft and Splunk ITSI. All events normalized to
OTel LogRecord format with standard severity mapping and deduplication fingerprint.

**OTel Signals:** Logs (Events)  
**Source Tools:** Moogsoft, Splunk ITSI, BigPanda  
**Retention:** Hot 30d | Warm 1yr | Cold 7yr
"""

    def get_table_definitions(self) -> List[TableDefinition]:
        return [
            self._otel_events_raw(),
            self._otel_events_correlated(),
            self._otel_events_enriched(),
        ]

    def _otel_events_raw(self) -> TableDefinition:
        return TableDefinition(
            name="otel_events_raw",
            schema_name="events_raw",
            description="Raw OTel LogRecords from event sources before AIOps correlation.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="severity_number",       dataType=DataType.INT),
                Column(name="severity_text",         dataType=DataType.VARCHAR),
                Column(name="body",                  dataType=DataType.TEXT),
                Column(name="event_name",            dataType=DataType.VARCHAR,  description="Event signature or name"),
                Column(name="event_domain",          dataType=DataType.VARCHAR,  description="Source domain: infrastructure|application|network"),
                Column(name="event_source",          dataType=DataType.VARCHAR,  description="Source system or component"),
                Column(name="event_class",           dataType=DataType.VARCHAR,  description="Event class or type"),
                Column(name="event_correlation_id",  dataType=DataType.VARCHAR,  description="Upstream tool's event ID"),
                Column(name="event_status",          dataType=DataType.VARCHAR,  description="open|acknowledged|resolved"),
                Column(name="event_priority",        dataType=DataType.INT,      description="Priority 1–5 from source tool"),
                Column(name="net_host_name",         dataType=DataType.VARCHAR,  description="Affected host"),
                Column(name="net_host_ip",           dataType=DataType.VARCHAR,  description="Affected host IP"),
                Column(name="eop_fingerprint",       dataType=DataType.VARCHAR,  description="SHA-256 dedup fingerprint"),
                Column(name="eop_source_tool",       dataType=DataType.VARCHAR,  description="moogsoft|splunk-itsi|bigpanda"),
            ]
        )

    def _otel_events_correlated(self) -> TableDefinition:
        return TableDefinition(
            name="otel_events_correlated",
            schema_name="events_correlated",
            description="AIOps-correlated events with cross-domain TraceID linkage.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"], EOP_TAGS["dq_validated"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="severity_number",           dataType=DataType.INT),
                Column(name="severity_text",             dataType=DataType.VARCHAR),
                Column(name="body",                      dataType=DataType.TEXT),
                Column(name="event_name",                dataType=DataType.VARCHAR),
                Column(name="correlation_group_id",      dataType=DataType.VARCHAR,  description="AIOps correlation cluster ID"),
                Column(name="correlated_event_count",    dataType=DataType.INT,      description="Number of events in this correlation"),
                Column(name="root_cause_event_id",       dataType=DataType.VARCHAR,  description="Identified root cause event ID"),
                Column(name="cross_domain_trace_id",     dataType=DataType.VARCHAR,  description="W3C TraceID linking to app trace"),
                Column(name="affected_services",         dataType=DataType.ARRAY,    description="List of affected service names"),
                Column(name="affected_cis",              dataType=DataType.ARRAY,    description="Affected configuration items"),
                Column(name="aiops_confidence_score",    dataType=DataType.DOUBLE,   description="AI confidence in correlation (0.0–1.0)"),
                Column(name="mean_time_to_correlate_ms", dataType=DataType.DOUBLE,   description="Time from first event to correlation"),
                Column(name="eop_fingerprint",           dataType=DataType.VARCHAR),
            ]
        )

    def _otel_events_enriched(self) -> TableDefinition:
        return TableDefinition(
            name="otel_events_enriched",
            schema_name="events_enriched",
            description="Fully enriched events with CMDB context, service map, and team routing.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_7yr"], EOP_TAGS["dq_validated"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="severity_number",           dataType=DataType.INT),
                Column(name="severity_text",             dataType=DataType.VARCHAR),
                Column(name="body",                      dataType=DataType.TEXT),
                Column(name="event_name",                dataType=DataType.VARCHAR),
                Column(name="cmdb_ci_id",                dataType=DataType.VARCHAR,  description="ServiceNow CMDB CI sys_id"),
                Column(name="cmdb_ci_name",              dataType=DataType.VARCHAR,  description="CMDB configuration item name"),
                Column(name="cmdb_ci_class",             dataType=DataType.VARCHAR,  description="CMDB CI class (cmdb_ci_server|cmdb_ci_app_server...)"),
                Column(name="service_map_tier",          dataType=DataType.VARCHAR,  description="tier1|tier2|tier3"),
                Column(name="team_assignment_group",     dataType=DataType.VARCHAR,  description="ServiceNow assignment group"),
                Column(name="team_owner",                dataType=DataType.VARCHAR),
                Column(name="cost_center",               dataType=DataType.VARCHAR),
                Column(name="environment",               dataType=DataType.VARCHAR),
                Column(name="resolution_time_ms",        dataType=DataType.DOUBLE,   description="Time to resolve in ms"),
                Column(name="servicenow_incident_id",    dataType=DataType.VARCHAR,  description="Linked ServiceNow INC number"),
            ]
        )


# =============================================================================
# ALERTING DOMAIN
# =============================================================================

class AlertingDomain(BaseDomain):
    domain_name  = "alerting"
    service_name = "eop-alerting"
    owner_team   = "platform-itsm-team"
    description  = """
**Alerting Observability Domain**

Alert records from ServiceNow, Grafana AlertManager, OpsGenie, and PagerDuty.
All alerts normalized to OTel LogRecord format with deduplication and grouping.

**OTel Signals:** Logs (Alerts)  
**Source Tools:** ServiceNow, Grafana AM, OpsGenie, PagerDuty  
**Retention:** Hot 30d | Warm 3yr | Cold 7yr
"""

    def get_table_definitions(self) -> List[TableDefinition]:
        return [
            self._otel_alerts_raw(),
            self._otel_alerts_deduped(),
            self._otel_incidents(),
            self._otel_slo_burn_rate(),
        ]

    def _otel_alerts_raw(self) -> TableDefinition:
        return TableDefinition(
            name="otel_alerts_raw",
            schema_name="alerts_raw",
            description="Raw normalized alert records from all alert sources.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="severity_number",       dataType=DataType.INT),
                Column(name="severity_text",         dataType=DataType.VARCHAR),
                Column(name="body",                  dataType=DataType.TEXT,     description="Alert message"),
                Column(name="alert_name",            dataType=DataType.VARCHAR,  description="Alert rule name"),
                Column(name="alert_status",          dataType=DataType.VARCHAR,  description="firing|resolved|silenced"),
                Column(name="alert_fingerprint",     dataType=DataType.VARCHAR,  description="Grafana AM fingerprint or EOP SHA-256"),
                Column(name="alert_namespace",       dataType=DataType.VARCHAR,  description="K8s namespace or service namespace"),
                Column(name="alert_severity",        dataType=DataType.VARCHAR,  description="critical|warning|info"),
                Column(name="alert_starts_at_ns",    dataType=DataType.BIGINT,   description="Alert firing start timestamp ns"),
                Column(name="alert_ends_at_ns",      dataType=DataType.BIGINT,   description="Alert resolved timestamp ns (null if still firing)"),
                Column(name="alert_duration_ms",     dataType=DataType.DOUBLE,   description="Duration firing in ms"),
                Column(name="alert_source_url",      dataType=DataType.VARCHAR,  description="Generator URL"),
                Column(name="alert_runbook_url",     dataType=DataType.VARCHAR,  description="Runbook link"),
                Column(name="affected_service",      dataType=DataType.VARCHAR),
                Column(name="affected_host",         dataType=DataType.VARCHAR),
            ]
        )

    def _otel_alerts_deduped(self) -> TableDefinition:
        return TableDefinition(
            name="otel_alerts_deduped",
            schema_name="alerts_processed",
            description="Deduplicated and grouped alerts. Used for MTTR/MTTD analytics.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_7yr"], EOP_TAGS["dq_validated"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="severity_number",           dataType=DataType.INT),
                Column(name="severity_text",             dataType=DataType.VARCHAR),
                Column(name="body",                      dataType=DataType.TEXT),
                Column(name="alert_name",                dataType=DataType.VARCHAR),
                Column(name="alert_group_id",            dataType=DataType.VARCHAR,  description="AlertManager group ID"),
                Column(name="deduplicated_count",        dataType=DataType.INT,      description="Number of raw alerts merged"),
                Column(name="first_seen_ns",             dataType=DataType.BIGINT),
                Column(name="last_seen_ns",              dataType=DataType.BIGINT),
                Column(name="resolved_ns",               dataType=DataType.BIGINT),
                Column(name="mttd_ms",                   dataType=DataType.DOUBLE,   description="Mean Time To Detect (ms)"),
                Column(name="mttr_ms",                   dataType=DataType.DOUBLE,   description="Mean Time To Resolve (ms)"),
                Column(name="servicenow_incident_id",    dataType=DataType.VARCHAR),
                Column(name="oncall_user",               dataType=DataType.VARCHAR,  description="Engineer who responded (anonymized)"),
                Column(name="action_taken",              dataType=DataType.VARCHAR,  description="resolved|escalated|auto-remediated|false-positive"),
            ]
        )

    def _otel_incidents(self) -> TableDefinition:
        return TableDefinition(
            name="otel_incidents",
            schema_name="alerts_processed",
            description="ServiceNow incidents linked to alert events with full lifecycle tracking.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_7yr"], EOP_TAGS["dq_validated"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="incident_id",           dataType=DataType.VARCHAR,  description="ServiceNow INC number"),
                Column(name="incident_state",        dataType=DataType.VARCHAR,  description="new|in_progress|resolved|closed"),
                Column(name="incident_priority",     dataType=DataType.INT,      description="P1–P5"),
                Column(name="incident_category",     dataType=DataType.VARCHAR),
                Column(name="incident_subcategory",  dataType=DataType.VARCHAR),
                Column(name="cmdb_ci_name",          dataType=DataType.VARCHAR),
                Column(name="assignment_group",      dataType=DataType.VARCHAR),
                Column(name="short_description",     dataType=DataType.TEXT),
                Column(name="opened_at_ns",          dataType=DataType.BIGINT),
                Column(name="resolved_at_ns",        dataType=DataType.BIGINT),
                Column(name="closed_at_ns",          dataType=DataType.BIGINT),
                Column(name="mttd_ms",               dataType=DataType.DOUBLE),
                Column(name="mttr_ms",               dataType=DataType.DOUBLE),
                Column(name="linked_alert_count",    dataType=DataType.INT,      description="Number of alerts that triggered this incident"),
                Column(name="linked_event_ids",      dataType=DataType.ARRAY,    description="Correlated Moogsoft/ITSI event IDs"),
            ]
        )

    def _otel_slo_burn_rate(self) -> TableDefinition:
        return TableDefinition(
            name="otel_slo_burn_rate",
            schema_name="alerts_processed",
            description="SLO error budget burn rate metrics computed from alert and span data.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_7yr"], EOP_TAGS["dq_validated"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="slo_name",              dataType=DataType.VARCHAR,  description="SLO definition name"),
                Column(name="slo_target",            dataType=DataType.DOUBLE,   description="SLO target (e.g. 0.999 for 99.9%)"),
                Column(name="error_budget_remaining",dataType=DataType.DOUBLE,   description="Remaining error budget (0.0–1.0)"),
                Column(name="burn_rate_1h",          dataType=DataType.DOUBLE,   description="1-hour burn rate"),
                Column(name="burn_rate_6h",          dataType=DataType.DOUBLE,   description="6-hour burn rate"),
                Column(name="burn_rate_24h",         dataType=DataType.DOUBLE,   description="24-hour burn rate"),
                Column(name="window_start_ns",       dataType=DataType.BIGINT,   description="SLO window start"),
                Column(name="window_end_ns",         dataType=DataType.BIGINT,   description="SLO window end"),
                Column(name="good_events",           dataType=DataType.BIGINT,   description="Count of good events in window"),
                Column(name="total_events",          dataType=DataType.BIGINT,   description="Count of total events in window"),
            ]
        )
