"""
catalog/domains/infrastructure.py
OpenMetadata catalog registration for the Infrastructure observability domain.

Registers:
  - OTel metrics tables (system.cpu, system.memory, system.disk, etc.)
  - Infrastructure log tables
  - Cloud provider metrics tables (AWS, Azure, GCP)
  - K8s metrics tables
"""

from typing import List

from metadata.generated.schema.entity.data.table import (
    Column, ColumnDataType, DataType, TableType,
)
from metadata.generated.schema.type.tagLabel import TagLabel

from catalog.core.base_domain import BaseDomain, TableDefinition, EOP_TAGS


class InfrastructureDomain(BaseDomain):

    domain_name  = "infrastructure"
    service_name = "eop-infrastructure"
    owner_team   = "platform-infra-team"
    description  = """
**Infrastructure Observability Domain**

Telemetry from Cloud Insights (CI), Telegraf agents, VictoriaMetrics,
ClickHouse, and Kubernetes clusters.

All metrics conform to [OTel Semantic Conventions — system.*](https://opentelemetry.io/docs/specs/semconv/system/)

**Source Tools:** Cloud Insights, Telegraf, VictoriaMetrics, Loki  
**OTel Signals:** Metrics, Logs  
**Retention:** Hot 14d (ClickHouse) | Warm 1yr (Delta Lake) | Cold 7yr (S3)  
**DQ Framework:** Great Expectations `infra_metrics_suite`
"""

    def get_table_definitions(self) -> List[TableDefinition]:
        return [
            self._otel_metrics_cpu(),
            self._otel_metrics_memory(),
            self._otel_metrics_disk(),
            self._otel_metrics_network(),
            self._otel_metrics_filesystem(),
            self._otel_metrics_process(),
            self._otel_logs_infra(),
            self._otel_metrics_kubernetes(),
            self._otel_metrics_cloud_aws(),
        ]

    # ── CPU metrics ───────────────────────────────────────────────────────────
    def _otel_metrics_cpu(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_cpu",
            schema_name="infra_metrics",
            description="OTel `system.cpu.*` metrics. CPU utilization, time, and logical core counts per host.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",                   dataType=DataType.VARCHAR,   description="OTel metric name (e.g. system.cpu.utilization)"),
                Column(name="metric_value",                  dataType=DataType.DOUBLE,    description="Metric data point value"),
                Column(name="metric_unit",                   dataType=DataType.VARCHAR,   description="Unit of measure (1 = ratio, s = seconds)"),
                Column(name="aggregation_temporality",       dataType=DataType.VARCHAR,   description="CUMULATIVE or DELTA"),
                Column(name="system_cpu_logical_number",     dataType=DataType.INT,       description="OTel: system.cpu.logical_number — CPU core index"),
                Column(name="system_cpu_state",              dataType=DataType.VARCHAR,   description="OTel: system.cpu.state (user|system|idle|iowait|irq|softirq|steal|nice)"),
                Column(name="system_cpu_utilization",        dataType=DataType.DOUBLE,    description="Derived: CPU utilization ratio (0.0–1.0)"),
                Column(name="start_time_unix_nano",          dataType=DataType.BIGINT,    description="Metric start time for cumulative temporality"),
                Column(name="exemplar_trace_id",             dataType=DataType.VARCHAR,   description="OTel exemplar trace ID for correlated trace"),
                Column(name="exemplar_span_id",              dataType=DataType.VARCHAR,   description="OTel exemplar span ID"),
            ]
        )

    # ── Memory metrics ────────────────────────────────────────────────────────
    def _otel_metrics_memory(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_memory",
            schema_name="infra_metrics",
            description="OTel `system.memory.*` metrics. Memory usage and utilization per host.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",                   dataType=DataType.VARCHAR),
                Column(name="metric_value",                  dataType=DataType.DOUBLE),
                Column(name="metric_unit",                   dataType=DataType.VARCHAR),
                Column(name="system_memory_state",           dataType=DataType.VARCHAR,   description="OTel: system.memory.state (used|free|cached|buffered|slab_reclaimable|slab_unreclaimable)"),
                Column(name="system_memory_usage_bytes",     dataType=DataType.BIGINT,    description="Memory usage in bytes"),
                Column(name="system_memory_utilization",     dataType=DataType.DOUBLE,    description="Memory utilization ratio (0.0–1.0)"),
                Column(name="system_memory_total_bytes",     dataType=DataType.BIGINT,    description="Total physical memory in bytes"),
            ]
        )

    # ── Disk I/O metrics ──────────────────────────────────────────────────────
    def _otel_metrics_disk(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_disk",
            schema_name="infra_metrics",
            description="OTel `system.disk.*` metrics. Disk I/O operations and bytes.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",           dataType=DataType.VARCHAR),
                Column(name="metric_value",          dataType=DataType.DOUBLE),
                Column(name="system_disk_device",    dataType=DataType.VARCHAR,  description="OTel: system.disk.device name"),
                Column(name="system_disk_direction", dataType=DataType.VARCHAR,  description="OTel: system.disk.direction (read|write)"),
                Column(name="disk_io_bytes",         dataType=DataType.BIGINT,   description="system.disk.io — bytes read/written"),
                Column(name="disk_operations",       dataType=DataType.BIGINT,   description="system.disk.operations — I/O op count"),
                Column(name="disk_operation_time",   dataType=DataType.DOUBLE,   description="system.disk.operation_time — seconds"),
            ]
        )

    # ── Network I/O metrics ───────────────────────────────────────────────────
    def _otel_metrics_network(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_network",
            schema_name="infra_metrics",
            description="OTel `system.network.*` metrics. Network interface I/O, errors, and connections.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",                   dataType=DataType.VARCHAR),
                Column(name="metric_value",                  dataType=DataType.DOUBLE),
                Column(name="network_interface_name",        dataType=DataType.VARCHAR,  description="OTel: network.interface.name"),
                Column(name="system_network_direction",      dataType=DataType.VARCHAR,  description="OTel: system.network.direction (transmit|receive)"),
                Column(name="system_network_io_bytes",       dataType=DataType.BIGINT,   description="system.network.io"),
                Column(name="system_network_packets",        dataType=DataType.BIGINT,   description="system.network.packets"),
                Column(name="system_network_errors",         dataType=DataType.BIGINT,   description="system.network.errors"),
                Column(name="system_network_dropped",        dataType=DataType.BIGINT,   description="system.network.dropped"),
                Column(name="system_network_connections",    dataType=DataType.INT,      description="system.network.connections"),
                Column(name="network_state",                 dataType=DataType.VARCHAR,  description="TCP connection state (ESTABLISHED|LISTEN|CLOSE_WAIT...)"),
            ]
        )

    # ── Filesystem metrics ────────────────────────────────────────────────────
    def _otel_metrics_filesystem(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_filesystem",
            schema_name="infra_metrics",
            description="OTel `system.filesystem.*` metrics. Disk space utilization per mount point.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",                       dataType=DataType.VARCHAR),
                Column(name="metric_value",                      dataType=DataType.DOUBLE),
                Column(name="system_filesystem_mountpoint",      dataType=DataType.VARCHAR,  description="OTel: system.filesystem.mountpoint"),
                Column(name="system_filesystem_type",            dataType=DataType.VARCHAR,  description="OTel: system.filesystem.type (ext4|xfs|ntfs...)"),
                Column(name="system_filesystem_mode",            dataType=DataType.VARCHAR,  description="OTel: system.filesystem.mode (rw|ro)"),
                Column(name="system_filesystem_state",           dataType=DataType.VARCHAR,  description="OTel: system.filesystem.state (used|free|reserved)"),
                Column(name="system_filesystem_usage_bytes",     dataType=DataType.BIGINT),
                Column(name="system_filesystem_utilization",     dataType=DataType.DOUBLE,   description="Utilization ratio (0.0–1.0)"),
            ]
        )

    # ── Process metrics ───────────────────────────────────────────────────────
    def _otel_metrics_process(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_process",
            schema_name="infra_metrics",
            description="OTel `process.*` metrics. Per-process CPU, memory, and thread usage.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_7d"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",                   dataType=DataType.VARCHAR),
                Column(name="metric_value",                  dataType=DataType.DOUBLE),
                Column(name="process_pid",                   dataType=DataType.INT,      description="OTel: process.pid"),
                Column(name="process_executable_name",       dataType=DataType.VARCHAR,  description="OTel: process.executable.name"),
                Column(name="process_command_line",          dataType=DataType.VARCHAR,  description="OTel: process.command_line"),
                Column(name="process_owner",                 dataType=DataType.VARCHAR,  description="OTel: process.owner (OS user)"),
                Column(name="process_cpu_utilization",       dataType=DataType.DOUBLE),
                Column(name="process_memory_rss",            dataType=DataType.BIGINT,   description="RSS memory bytes"),
                Column(name="process_memory_virtual",        dataType=DataType.BIGINT,   description="Virtual memory bytes"),
                Column(name="process_threads",               dataType=DataType.INT),
            ]
        )

    # ── Infrastructure logs ───────────────────────────────────────────────────
    def _otel_logs_infra(self) -> TableDefinition:
        return TableDefinition(
            name="otel_logs_infra",
            schema_name="infra_logs",
            description="OTel LogRecord for infrastructure logs (syslog, kernel, auth, cloud-insights).",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="severity_number",  dataType=DataType.INT,       description="OTel SeverityNumber (1–24)"),
                Column(name="severity_text",    dataType=DataType.VARCHAR,   description="OTel SeverityText (TRACE|DEBUG|INFO|WARN|ERROR|FATAL)"),
                Column(name="body",             dataType=DataType.TEXT,      description="OTel log body (raw message)"),
                Column(name="trace_id",         dataType=DataType.VARCHAR,   description="OTel TraceID for correlated trace"),
                Column(name="span_id",          dataType=DataType.VARCHAR,   description="OTel SpanID"),
                Column(name="trace_flags",      dataType=DataType.INT,       description="OTel W3C trace flags"),
                Column(name="log_source",       dataType=DataType.VARCHAR,   description="Source log file or component"),
                Column(name="eop_fingerprint",  dataType=DataType.VARCHAR,   description="EOP dedup fingerprint (SHA-256 of body+host)"),
            ]
        )

    # ── Kubernetes metrics ────────────────────────────────────────────────────
    def _otel_metrics_kubernetes(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_kubernetes",
            schema_name="infra_metrics",
            description="OTel `k8s.*` metrics. Pod, node, and cluster metrics from Kubernetes.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",               dataType=DataType.VARCHAR),
                Column(name="metric_value",              dataType=DataType.DOUBLE),
                Column(name="k8s_cluster_name",          dataType=DataType.VARCHAR,  description="OTel: k8s.cluster.name"),
                Column(name="k8s_namespace_name",        dataType=DataType.VARCHAR,  description="OTel: k8s.namespace.name"),
                Column(name="k8s_pod_name",              dataType=DataType.VARCHAR,  description="OTel: k8s.pod.name"),
                Column(name="k8s_pod_uid",               dataType=DataType.VARCHAR,  description="OTel: k8s.pod.uid"),
                Column(name="k8s_container_name",        dataType=DataType.VARCHAR,  description="OTel: k8s.container.name"),
                Column(name="k8s_node_name",             dataType=DataType.VARCHAR,  description="OTel: k8s.node.name"),
                Column(name="k8s_deployment_name",       dataType=DataType.VARCHAR,  description="OTel: k8s.deployment.name"),
                Column(name="container_cpu_usage",       dataType=DataType.DOUBLE),
                Column(name="container_memory_rss",      dataType=DataType.BIGINT),
                Column(name="container_memory_limit",    dataType=DataType.BIGINT),
            ]
        )

    # ── AWS CloudWatch metrics ────────────────────────────────────────────────
    def _otel_metrics_cloud_aws(self) -> TableDefinition:
        return TableDefinition(
            name="otel_metrics_cloud_aws",
            schema_name="infra_metrics",
            description="AWS CloudWatch metrics normalized to OTel conventions. EC2, ECS, EKS, RDS.",
            tags=[EOP_TAGS["otel_standard"], EOP_TAGS["pii_false"], EOP_TAGS["retention_1yr"]],
            columns=self.resource_columns() + [
                self.timestamp_column(),
                Column(name="metric_name",           dataType=DataType.VARCHAR),
                Column(name="metric_value",          dataType=DataType.DOUBLE),
                Column(name="metric_unit",           dataType=DataType.VARCHAR),
                Column(name="aws_namespace",         dataType=DataType.VARCHAR,  description="CloudWatch namespace (e.g. AWS/EC2)"),
                Column(name="aws_dimension_name",    dataType=DataType.VARCHAR),
                Column(name="aws_dimension_value",   dataType=DataType.VARCHAR),
                Column(name="aws_instance_id",       dataType=DataType.VARCHAR),
                Column(name="aws_service",           dataType=DataType.VARCHAR,  description="AWS service type (ec2|ecs|eks|rds|lambda)"),
                Column(name="finops_cost_center",    dataType=DataType.VARCHAR,  description="FinOps cost center for billing attribution"),
            ]
        )
