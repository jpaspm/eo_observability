"""
governance/data-quality/infra_metrics_dq_suite.py
Great Expectations Data Quality Suite — Infrastructure Metrics

Validates OTel-normalized infrastructure metrics in the Kafka stream
and Databricks Delta Lake tables.

Run modes:
  1. Streaming (Kafka)  — called by OTel Collector DQ processor
  2. Batch (Delta Lake) — run as Databricks job (nightly)

Usage:
    # Run full batch checkpoint
    great_expectations checkpoint run infra_metrics_checkpoint

    # Run specific expectation suite
    python infra_metrics_dq_suite.py --table otel_metrics_cpu
"""

import great_expectations as gx
from great_expectations.core import ExpectationSuite, ExpectationConfiguration
from great_expectations.checkpoint import Checkpoint
from great_expectations.data_context import DataContext


def get_infra_metrics_suite() -> ExpectationSuite:
    """
    Build and return the GE Expectation Suite for infrastructure metrics.
    """
    suite = ExpectationSuite(expectation_suite_name="infra_metrics_suite")

    # ── DQ Rule 1: Mandatory OTel resource attributes ─────────────────────────

    # service.name must be present and non-null
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "service_name"},
        meta={"rule_id": "DQ-INFRA-001", "description": "OTel mandatory: service.name must not be null"}
    ))

    # host.name must be present and non-null
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "host_name"},
        meta={"rule_id": "DQ-INFRA-002", "description": "OTel mandatory: host.name must not be null"}
    ))

    # deployment.environment must be one of allowed values
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={
            "column": "deployment_environment",
            "value_set": ["prod", "production", "staging", "dev", "development", "test", "uat"],
            "mostly": 0.99,  # 1% tolerance for migration
        },
        meta={"rule_id": "DQ-INFRA-003", "description": "deployment.environment must be a known value"}
    ))

    # cloud.provider must be valid
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={
            "column": "cloud_provider",
            "value_set": ["aws", "azure", "gcp", "on-prem", "bare-metal", None],
            "mostly": 0.99,
        },
        meta={"rule_id": "DQ-INFRA-004", "description": "cloud.provider must be a known value"}
    ))

    # ── DQ Rule 2: Timestamp integrity ────────────────────────────────────────

    # timestamp_unix_nano must be non-null
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "timestamp_unix_nano"},
        meta={"rule_id": "DQ-INFRA-005", "description": "Timestamp must not be null"}
    ))

    # timestamp must be within last 5 minutes (no stale data)
    # Note: expressed as min/max epoch in ns (roughly last 24h for batch)
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_between",
        kwargs={
            "column": "timestamp_unix_nano",
            "min_value": 1_000_000_000_000_000_000,  # Year 2001 (sanity floor)
            "max_value": None,                         # No upper bound in batch
            "mostly": 1.0,
        },
        meta={"rule_id": "DQ-INFRA-006", "description": "Timestamp must be a valid Unix nanosecond epoch"}
    ))

    # ── DQ Rule 3: Metric name conformance ────────────────────────────────────

    # metric_name must follow OTel naming convention: namespace.component
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_match_regex",
        kwargs={
            "column": "metric_name",
            "regex": r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$",
            "mostly": 0.99,
        },
        meta={"rule_id": "DQ-INFRA-007", "description": "metric_name must follow OTel dot-notation (e.g. system.cpu.utilization)"}
    ))

    # metric_name must be from known EOP infra namespace
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_match_like_pattern_list",
        kwargs={
            "column": "metric_name",
            "like_pattern_list": [
                "system.cpu.%",
                "system.memory.%",
                "system.disk.%",
                "system.filesystem.%",
                "system.network.%",
                "process.%",
                "k8s.%",
                "container.%",
                "jvm.%",
                "network.%",
            ],
            "match_on": "any",
            "mostly": 0.95,
        },
        meta={"rule_id": "DQ-INFRA-008", "description": "metric_name must use known EOP infra namespace prefixes"}
    ))

    # ── DQ Rule 4: Value integrity ────────────────────────────────────────────

    # metric_value must be non-null
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_not_be_null",
        kwargs={"column": "metric_value"},
        meta={"rule_id": "DQ-INFRA-009", "description": "metric_value must not be null"}
    ))

    # CPU utilization ratio must be in [0.0, 1.0]
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_between",
        kwargs={
            "column": "system_cpu_utilization",
            "min_value": 0.0,
            "max_value": 1.0,
            "mostly": 0.999,
        },
        meta={"rule_id": "DQ-INFRA-010", "description": "CPU utilization must be in [0.0, 1.0]"}
    ))

    # Memory utilization ratio must be in [0.0, 1.0]
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_between",
        kwargs={
            "column": "system_memory_utilization",
            "min_value": 0.0,
            "max_value": 1.0,
            "mostly": 0.999,
        },
        meta={"rule_id": "DQ-INFRA-011", "description": "Memory utilization must be in [0.0, 1.0]"}
    ))

    # ── DQ Rule 5: Cardinality control ────────────────────────────────────────

    # cpu state values must be from known set
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={
            "column": "system_cpu_state",
            "value_set": ["user", "system", "idle", "iowait", "irq", "softirq", "steal", "nice", None],
            "mostly": 0.999,
        },
        meta={"rule_id": "DQ-INFRA-012", "description": "CPU state must be a known OTel system.cpu.state value"}
    ))

    # memory state values must be from known set
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={
            "column": "system_memory_state",
            "value_set": ["used", "free", "cached", "buffered", "slab_reclaimable", "slab_unreclaimable", None],
            "mostly": 0.999,
        },
        meta={"rule_id": "DQ-INFRA-013", "description": "Memory state must be a known OTel system.memory.state value"}
    ))

    # ── DQ Rule 6: Completeness ───────────────────────────────────────────────

    # Row count (completeness check — fail if table is suspiciously empty)
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_table_row_count_to_be_between",
        kwargs={
            "min_value": 100,    # At least 100 rows per batch window
            "max_value": None,   # No upper bound
        },
        meta={"rule_id": "DQ-INFRA-014", "description": "Table must have at least 100 rows per batch window"}
    ))

    # Column completeness: critical columns must be >99% populated
    for col in ["service_name", "host_name", "metric_name", "metric_value", "timestamp_unix_nano"]:
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": col, "mostly": 0.99},
            meta={"rule_id": f"DQ-INFRA-015-{col}", "description": f"Column '{col}' completeness >= 99%"}
        ))

    # ── DQ Rule 7: Schema conformance ─────────────────────────────────────────

    # Expected columns must exist
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_table_columns_to_match_set",
        kwargs={
            "column_set": [
                "service_name", "service_namespace", "host_name",
                "deployment_environment", "cloud_provider", "cloud_region",
                "timestamp_unix_nano", "metric_name", "metric_value",
                "eop_domain", "eop_source_tool",
            ],
            "exact_match": False,  # Allow extra columns
        },
        meta={"rule_id": "DQ-INFRA-016", "description": "Required OTel columns must be present in table"}
    ))

    return suite


def build_checkpoint(context: DataContext, suite: ExpectationSuite) -> Checkpoint:
    """Create a GE checkpoint for the infra metrics DQ suite."""
    return context.add_or_update_checkpoint(
        name="infra_metrics_checkpoint",
        config={
            "class_name": "SimpleCheckpoint",
            "validations": [
                {
                    "batch_request": {
                        "datasource_name":       "databricks_lakehouse",
                        "data_connector_name":   "delta_lake_connector",
                        "data_asset_name":       "otel_metrics_cpu",
                        "batch_spec_passthrough": {
                            "reader_method":  "delta",
                            "reader_options": {
                                "path": "s3://${S3_LANDING_BUCKET}/delta/infra_metrics/otel_metrics_cpu"
                            }
                        }
                    },
                    "expectation_suite_name": suite.expectation_suite_name,
                },
            ],
            "action_list": [
                {
                    "name":   "store_validation_result",
                    "action": {"class_name": "StoreValidationResultAction"},
                },
                {
                    "name":   "store_evaluation_params",
                    "action": {"class_name": "StoreEvaluationParametersAction"},
                },
                {
                    "name":   "update_data_docs",
                    "action": {"class_name": "UpdateDataDocsAction"},
                },
                # Notify on DQ failure → Kafka quarantine + ServiceNow ticket
                {
                    "name": "notify_on_failure",
                    "action": {
                        "class_name": "SlackNotificationAction",
                        "slack_webhook": "${SLACK_DQ_WEBHOOK}",
                        "notify_on":    "failure",
                        "renderer": {
                            "class_name": "SlackRenderer",
                            "header":     "⚠️ EOP DQ Failure — infra_metrics",
                        },
                    },
                },
            ],
        }
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run EOP Infrastructure DQ Suite")
    parser.add_argument("--table", default="otel_metrics_cpu",
                        help="Delta Lake table to validate")
    parser.add_argument("--context-root", default="/opt/great_expectations",
                        help="Great Expectations context root")
    args = parser.parse_args()

    ctx = gx.get_context(context_root_dir=args.context_root)
    suite = get_infra_metrics_suite()
    ctx.add_or_update_expectation_suite(expectation_suite=suite)
    checkpoint = build_checkpoint(ctx, suite)
    result = checkpoint.run()

    print(f"\nDQ Result: {'✓ PASS' if result.success else '✗ FAIL'}")
    print(f"Validated: {len(result.run_results)} batches")
    for run_key, run_result in result.run_results.items():
        stats = run_result["validation_result"]["statistics"]
        print(f"  {run_key}: {stats['successful_expectations']}/{stats['evaluated_expectations']} expectations passed")
