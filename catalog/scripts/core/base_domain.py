"""
catalog/core/base_domain.py
Abstract base class for all EOP observability domain catalog registrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from metadata.generated.schema.api.data.createDatabase import CreateDatabaseRequest
from metadata.generated.schema.api.data.createDatabaseSchema import CreateDatabaseSchemaRequest
from metadata.generated.schema.api.data.createTable import CreateTableRequest
from metadata.generated.schema.api.services.createDatabaseService import CreateDatabaseServiceRequest
from metadata.generated.schema.entity.data.table import (
    Column, ColumnDataType, DataType, TableType,
)
from metadata.generated.schema.entity.services.connections.database.customDatabaseConnection import (
    CustomDatabaseConnection,
)
from metadata.generated.schema.entity.services.databaseService import (
    DatabaseServiceType,
)
from metadata.generated.schema.type.basic import (
    EntityName, FullyQualifiedEntityName, Markdown,
)
from metadata.generated.schema.type.tagLabel import (
    TagLabel, TagSource, State, LabelType,
)
from metadata.ingestion.ometa.ometa_api import OpenMetadata


# ── EOP Standard Tags ─────────────────────────────────────────────────────────
EOP_TAG_CATEGORY = "EOP"

EOP_TAGS = {
    "otel_standard":    TagLabel(tagFQN="EOP.OTelStandard",    source=TagSource.Classification, state=State.Confirmed, labelType=LabelType.Automated),
    "pii_false":        TagLabel(tagFQN="EOP.NonPII",          source=TagSource.Classification, state=State.Confirmed, labelType=LabelType.Automated),
    "pii_true":         TagLabel(tagFQN="EOP.PII",             source=TagSource.Classification, state=State.Confirmed, labelType=LabelType.Automated),
    "retention_7d":     TagLabel(tagFQN="EOP.Retention7Days",  source=TagSource.Classification, state=State.Confirmed, labelType=LabelType.Automated),
    "retention_1yr":    TagLabel(tagFQN="EOP.Retention1Year",  source=TagSource.Classification, state=State.Confirmed, labelType=LabelType.Automated),
    "retention_7yr":    TagLabel(tagFQN="EOP.Retention7Years", source=TagSource.Classification, state=State.Confirmed, labelType=LabelType.Automated),
    "dq_validated":     TagLabel(tagFQN="EOP.DQValidated",     source=TagSource.Classification, state=State.Confirmed, labelType=LabelType.Automated),
}


@dataclass
class TableDefinition:
    """Describes a single OpenMetadata table to be registered."""
    name: str
    schema_name: str
    description: str
    columns: List[Column]
    table_type: TableType = TableType.Regular
    tags: List[TagLabel] = field(default_factory=list)
    owner: Optional[str] = None


class BaseDomain(ABC):
    """
    Abstract base for EOP domain catalog registrations.

    Each domain subclass must implement:
        - domain_name       : str
        - service_name      : str
        - description       : str
        - owner_team        : str
        - get_table_definitions() → List[TableDefinition]
    """

    def __init__(self, client: OpenMetadata, dry_run: bool = False):
        self.client   = client
        self.dry_run  = dry_run

    # ── Abstract interface ────────────────────────────────────────────────────
    @property
    @abstractmethod
    def domain_name(self) -> str: ...

    @property
    @abstractmethod
    def service_name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def owner_team(self) -> str: ...

    @abstractmethod
    def get_table_definitions(self) -> List[TableDefinition]: ...

    # ── OTel standard column helpers ──────────────────────────────────────────
    @staticmethod
    def resource_columns() -> List[Column]:
        """Standard OTel resource attribute columns — added to every table."""
        return [
            Column(name="service_name",            dataType=DataType.VARCHAR,   description="OTel: service.name"),
            Column(name="service_namespace",        dataType=DataType.VARCHAR,   description="OTel: service.namespace — EOP domain"),
            Column(name="service_version",          dataType=DataType.VARCHAR,   description="OTel: service.version"),
            Column(name="host_name",                dataType=DataType.VARCHAR,   description="OTel: host.name"),
            Column(name="deployment_environment",   dataType=DataType.VARCHAR,   description="OTel: deployment.environment (prod|staging|dev)"),
            Column(name="cloud_provider",           dataType=DataType.VARCHAR,   description="OTel: cloud.provider"),
            Column(name="cloud_region",             dataType=DataType.VARCHAR,   description="OTel: cloud.region"),
            Column(name="cloud_account_id",         dataType=DataType.VARCHAR,   description="OTel: cloud.account.id"),
            Column(name="telemetry_sdk_name",       dataType=DataType.VARCHAR,   description="OTel: telemetry.sdk.name"),
            Column(name="telemetry_sdk_version",    dataType=DataType.VARCHAR,   description="OTel: telemetry.sdk.version"),
            Column(name="eop_domain",               dataType=DataType.VARCHAR,   description="EOP: domain label"),
            Column(name="eop_source_tool",          dataType=DataType.VARCHAR,   description="EOP: originating tool"),
        ]

    @staticmethod
    def timestamp_column() -> Column:
        return Column(
            name="timestamp_unix_nano",
            dataType=DataType.BIGINT,
            description="OTel: event timestamp in Unix nanoseconds",
        )

    # ── Catalog registration methods ──────────────────────────────────────────
    def create_service(self):
        """Register the domain as an OpenMetadata Database Service."""
        request = CreateDatabaseServiceRequest(
            name=EntityName(self.service_name),
            displayName=f"EOP — {self.domain_name.title()} Domain",
            description=Markdown(self.description),
            serviceType=DatabaseServiceType.CustomDatabase,
            connection=CustomDatabaseConnection(
                config={"sourcePythonClass": f"eop.catalog.domains.{self.domain_name}"}
            ),
        )
        if not self.dry_run:
            self.client.create_or_update(request)
        else:
            print(f"[DRY RUN] Would create service: {self.service_name}")

    def create_schemas(self):
        """Register databases and schemas under the domain service."""
        # Main domain database
        db_request = CreateDatabaseRequest(
            name=EntityName(f"eop_{self.domain_name}"),
            displayName=f"EOP {self.domain_name.title()}",
            description=Markdown(f"OpenTelemetry telemetry database for the {self.domain_name} domain."),
            service=FullyQualifiedEntityName(self.service_name),
        )
        if not self.dry_run:
            self.client.create_or_update(db_request)
        else:
            print(f"[DRY RUN] Would create database: eop_{self.domain_name}")

        # Signal-type schemas (metrics / logs / traces / events / alerts)
        for schema_name in self._get_schema_names():
            schema_request = CreateDatabaseSchemaRequest(
                name=EntityName(schema_name),
                displayName=schema_name.replace("_", " ").title(),
                description=Markdown(f"OTel {schema_name.split('_')[-1]} schema for {self.domain_name} domain."),
                database=FullyQualifiedEntityName(f"{self.service_name}.eop_{self.domain_name}"),
            )
            if not self.dry_run:
                self.client.create_or_update(schema_request)
            else:
                print(f"[DRY RUN] Would create schema: {schema_name}")

    def create_tables(self):
        """Register all tables defined by the domain."""
        for tdef in self.get_table_definitions():
            fqn_prefix = f"{self.service_name}.eop_{self.domain_name}.{tdef.schema_name}"
            request = CreateTableRequest(
                name=EntityName(tdef.name),
                displayName=tdef.name.replace("_", " ").title(),
                description=Markdown(tdef.description),
                tableType=tdef.table_type,
                columns=tdef.columns,
                databaseSchema=FullyQualifiedEntityName(fqn_prefix),
                tags=tdef.tags or [EOP_TAGS["otel_standard"]],
            )
            if not self.dry_run:
                self.client.create_or_update(request)
                print(f"  ✓ Registered table: {fqn_prefix}.{tdef.name}")
            else:
                print(f"  [DRY RUN] Would create table: {fqn_prefix}.{tdef.name}")

    def _get_schema_names(self) -> List[str]:
        """Return schema names from table definitions."""
        return list({tdef.schema_name for tdef in self.get_table_definitions()})
