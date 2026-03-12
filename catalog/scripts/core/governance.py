"""
catalog/core/governance.py
Apply EOP governance tags, classifications, and ownership to all catalog assets.

Tags applied:
  - EOP.OTelStandard        — asset uses OTel semantic conventions
  - EOP.DQValidated         — asset passed DQ checkpoint
  - EOP.PII / EOP.NonPII    — data classification
  - EOP.RetentionXxx        — retention policy label
  - EOP.Domain.*            — domain ownership label
"""

import logging
from typing import List

from metadata.generated.schema.api.classification.createClassification import (
    CreateClassificationRequest,
)
from metadata.generated.schema.api.classification.createTag import CreateTagRequest
from metadata.generated.schema.entity.classification.classification import Classification
from metadata.generated.schema.entity.classification.tag import Tag
from metadata.generated.schema.type.basic import EntityName, Markdown
from metadata.ingestion.ometa.ometa_api import OpenMetadata

log = logging.getLogger("eop.catalog.governance")


# ── EOP Tag taxonomy ──────────────────────────────────────────────────────────

EOP_CLASSIFICATION = "EOP"

EOP_TAG_DEFINITIONS = [
    # OTel compliance
    {"name": "OTelStandard",        "description": "Asset uses OpenTelemetry semantic conventions v1.24+"},
    # PII classification
    {"name": "NonPII",              "description": "Asset contains no Personally Identifiable Information"},
    {"name": "PII",                 "description": "Asset may contain Personally Identifiable Information — handle with care"},
    # Retention tiers
    {"name": "Retention7Days",      "description": "Hot storage retention: 7 days (ClickHouse real-time tier)"},
    {"name": "Retention14Days",     "description": "Hot storage retention: 14 days"},
    {"name": "Retention30Days",     "description": "Hot storage retention: 30 days"},
    {"name": "Retention1Year",      "description": "Warm storage retention: 1 year (Delta Lake)"},
    {"name": "Retention3Years",     "description": "Warm storage retention: 3 years (Delta Lake)"},
    {"name": "Retention7Years",     "description": "Cold storage retention: 7 years (S3 Glacier / Azure Archive)"},
    # DQ status
    {"name": "DQValidated",         "description": "Asset passed all Great Expectations DQ checkpoints"},
    {"name": "DQFailed",            "description": "Asset currently failing one or more DQ rules — quarantined"},
    {"name": "DQPending",           "description": "DQ validation not yet run for this asset"},
    # Domain ownership
    {"name": "DomainInfrastructure","description": "Asset owned by the Infrastructure observability domain team"},
    {"name": "DomainApplications",  "description": "Asset owned by the Applications (APM) observability domain team"},
    {"name": "DomainNetwork",       "description": "Asset owned by the Network observability domain team"},
    {"name": "DomainEvents",        "description": "Asset owned by the Events (AIOps) observability domain team"},
    {"name": "DomainAlerting",      "description": "Asset owned by the Alerting/ITSM observability domain team"},
    # Criticality
    {"name": "Critical",            "description": "Tier-1 critical asset — SLO-tracked, incident-generating"},
    {"name": "NonCritical",         "description": "Non-critical asset — best-effort availability"},
    # Environment
    {"name": "Production",          "description": "Production environment asset"},
    {"name": "NonProduction",       "description": "Non-production (dev/staging) asset"},
]


def bootstrap_classification(client: OpenMetadata, dry_run: bool = False) -> None:
    """Create the EOP classification and all tags in OpenMetadata."""
    log.info("Creating EOP classification and tags...")

    # Create classification
    classification_request = CreateClassificationRequest(
        name=EntityName(EOP_CLASSIFICATION),
        displayName="Enterprise Observability Platform",
        description=Markdown(
            "Tags governing data assets in the Enterprise Observability Platform. "
            "Covers OTel compliance, data classification, retention, DQ status, and domain ownership."
        ),
        mutuallyExclusive=False,
    )
    if not dry_run:
        try:
            client.create_or_update(classification_request)
            log.info(f"  ✓ Classification '{EOP_CLASSIFICATION}' created/updated")
        except Exception as e:
            log.warning(f"  ⚠ Classification creation: {e}")
    else:
        log.info(f"  [DRY RUN] Would create classification: {EOP_CLASSIFICATION}")

    # Create all tags
    for tag_def in EOP_TAG_DEFINITIONS:
        tag_request = CreateTagRequest(
            name=EntityName(tag_def["name"]),
            displayName=tag_def["name"],
            description=Markdown(tag_def["description"]),
            classification=EntityName(EOP_CLASSIFICATION),
        )
        if not dry_run:
            try:
                client.create_or_update(tag_request)
                log.info(f"  ✓ Tag '{EOP_CLASSIFICATION}.{tag_def['name']}' created")
            except Exception as e:
                log.warning(f"  ⚠ Tag '{tag_def['name']}': {e}")
        else:
            log.info(f"  [DRY RUN] Would create tag: {EOP_CLASSIFICATION}.{tag_def['name']}")


def apply_governance_tags(
    client: OpenMetadata,
    domain,
    dry_run: bool = False,
) -> None:
    """
    Apply standard governance tags to all tables registered by a domain.

    Tags applied per domain:
      - EOP.OTelStandard
      - EOP.NonPII (default; override per table if PII suspected)
      - EOP.DomainXxx
      - Retention tag based on schema name
    """
    domain_tag = f"EOP.Domain{domain.domain_name.title()}"
    retention_map = {
        "infra_metrics":    "EOP.Retention1Year",
        "infra_logs":       "EOP.Retention1Year",
        "app_traces":       "EOP.Retention1Year",
        "app_metrics":      "EOP.Retention1Year",
        "app_logs":         "EOP.Retention1Year",
        "network_metrics":  "EOP.Retention1Year",
        "network_flows":    "EOP.Retention1Year",
        "events_raw":       "EOP.Retention1Year",
        "events_correlated":"EOP.Retention1Year",
        "events_enriched":  "EOP.Retention7Years",
        "alerts_raw":       "EOP.Retention1Year",
        "alerts_processed": "EOP.Retention7Years",
    }

    for tdef in domain.get_table_definitions():
        retention_tag = retention_map.get(tdef.schema_name, "EOP.Retention1Year")
        tags_to_apply = [
            "EOP.OTelStandard",
            "EOP.NonPII",
            domain_tag,
            retention_tag,
        ]

        fqn = f"{domain.service_name}.eop_{domain.domain_name}.{tdef.schema_name}.{tdef.name}"

        if dry_run:
            log.info(f"  [DRY RUN] Would apply tags to {fqn}: {tags_to_apply}")
            continue

        try:
            # Fetch the table entity by FQN
            table = client.get_by_name(entity=client.table_entity, fqn=fqn)
            if table:
                # Patch tags onto the table
                client.patch_tag(entity=type(table), source=table, tag_fqn=tags_to_apply)
                log.info(f"  ✓ Tags applied to {tdef.name}: {tags_to_apply}")
        except Exception as e:
            log.warning(f"  ⚠ Could not apply tags to {fqn}: {e}")
