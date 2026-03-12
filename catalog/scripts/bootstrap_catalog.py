#!/usr/bin/env python3
"""
bootstrap_catalog.py
Enterprise Observability Platform — OpenMetadata Catalog Bootstrap

Creates the complete EOP data catalog in OpenMetadata:
  - 5 Observability Domains as OpenMetadata Services & Databases
  - OTel-standardized schemas per signal type (metrics, logs, traces, events, alerts)
  - Data lineage: source tool → OTel Collector → Kafka → Databricks Delta Lake
  - Ownership, classification, and governance tags
  - Data quality expectation links

Usage:
    python bootstrap_catalog.py --domain all
    python bootstrap_catalog.py --domain infrastructure
    python bootstrap_catalog.py --domain applications --dry-run

Requirements:
    pip install openmetadata-ingestion apache-airflow-providers-openmetadata
"""

import argparse
import logging
import sys
from typing import Optional

from catalog.domains.infrastructure import InfrastructureDomain
from catalog.domains.applications    import ApplicationsDomain
from catalog.domains.network         import NetworkDomain
from catalog.domains.events          import EventsDomain
from catalog.domains.alerting        import AlertingDomain
from catalog.core.client             import get_om_client
from catalog.core.governance         import apply_governance_tags
from catalog.core.lineage            import build_lineage_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("eop.catalog.bootstrap")

DOMAINS = {
    "infrastructure": InfrastructureDomain,
    "applications":   ApplicationsDomain,
    "network":        NetworkDomain,
    "events":         EventsDomain,
    "alerting":       AlertingDomain,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap Enterprise Observability Platform catalog in OpenMetadata"
    )
    parser.add_argument(
        "--domain",
        choices=list(DOMAINS.keys()) + ["all"],
        default="all",
        help="Which domain to bootstrap (default: all)"
    )
    parser.add_argument(
        "--om-host",
        default="http://openmetadata:8585",
        help="OpenMetadata server URL"
    )
    parser.add_argument(
        "--om-token",
        default=None,
        help="OpenMetadata JWT token (or set OM_JWT_TOKEN env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without actually creating it"
    )
    parser.add_argument(
        "--skip-lineage",
        action="store_true",
        help="Skip lineage graph creation (faster for schema-only updates)"
    )
    return parser.parse_args()


def bootstrap_domain(
    domain_name: str,
    domain_cls,
    client,
    dry_run: bool = False,
    skip_lineage: bool = False,
) -> bool:
    log.info("━" * 60)
    log.info(f"Bootstrapping domain: {domain_name.upper()}")
    log.info("━" * 60)

    try:
        domain = domain_cls(client=client, dry_run=dry_run)

        # 1. Create/update the domain service in OpenMetadata
        log.info(f"[{domain_name}] Creating service...")
        domain.create_service()

        # 2. Register all databases / schemas
        log.info(f"[{domain_name}] Registering schemas...")
        domain.create_schemas()

        # 3. Register all tables (metric tables, log tables, trace tables)
        log.info(f"[{domain_name}] Registering tables...")
        domain.create_tables()

        # 4. Apply governance: ownership, tags, classification
        log.info(f"[{domain_name}] Applying governance tags...")
        apply_governance_tags(client, domain, dry_run=dry_run)

        # 5. Build lineage graph
        if not skip_lineage:
            log.info(f"[{domain_name}] Building lineage graph...")
            build_lineage_graph(client, domain, dry_run=dry_run)

        log.info(f"[{domain_name}] ✓ Bootstrap complete")
        return True

    except Exception as exc:
        log.error(f"[{domain_name}] ✗ Bootstrap failed: {exc}", exc_info=True)
        return False


def main() -> int:
    args = parse_args()

    log.info("=" * 60)
    log.info("Enterprise Observability Platform — Catalog Bootstrap")
    log.info("=" * 60)
    log.info(f"OpenMetadata: {args.om_host}")
    log.info(f"Domain:       {args.domain}")
    log.info(f"Dry run:      {args.dry_run}")

    # Connect to OpenMetadata
    client = get_om_client(host=args.om_host, token=args.om_token)
    log.info("✓ Connected to OpenMetadata")

    # Determine which domains to run
    domains_to_run = (
        list(DOMAINS.items()) if args.domain == "all"
        else [(args.domain, DOMAINS[args.domain])]
    )

    results = {}
    for domain_name, domain_cls in domains_to_run:
        results[domain_name] = bootstrap_domain(
            domain_name=domain_name,
            domain_cls=domain_cls,
            client=client,
            dry_run=args.dry_run,
            skip_lineage=args.skip_lineage,
        )

    # Summary
    log.info("=" * 60)
    log.info("BOOTSTRAP SUMMARY")
    log.info("=" * 60)
    success_count = sum(results.values())
    for domain_name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        log.info(f"  {domain_name:<20} {status}")
    log.info(f"\n  {success_count}/{len(results)} domains bootstrapped successfully")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
