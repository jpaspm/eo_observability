"""
catalog/core/client.py
OpenMetadata client factory and connection utilities.
"""

import os
import logging
from typing import Optional

from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    OpenMetadataConnection,
)
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.ingestion.ometa.ometa_api import OpenMetadata

log = logging.getLogger("eop.catalog.client")


def get_om_client(
    host: str = "http://openmetadata:8585",
    token: Optional[str] = None,
) -> OpenMetadata:
    """
    Create and return an authenticated OpenMetadata client.

    Token resolution order:
      1. Explicit ``token`` parameter
      2. OM_JWT_TOKEN environment variable
      3. Raise ValueError
    """
    jwt_token = token or os.environ.get("OM_JWT_TOKEN")
    if not jwt_token:
        raise ValueError(
            "OpenMetadata JWT token required. "
            "Pass --om-token or set OM_JWT_TOKEN environment variable."
        )

    server_config = OpenMetadataConnection(
        hostPort=host,
        authProvider="openmetadata",
        securityConfig=OpenMetadataJWTClientConfig(jwtToken=jwt_token),
        # Retry settings for resilience
        retries=3,
        retryWait=2.0,
    )

    client = OpenMetadata(server_config)

    # Verify connection
    health = client.get_health_check()
    if not health:
        raise ConnectionError(f"Cannot reach OpenMetadata at {host}")

    log.info(f"Connected to OpenMetadata at {host}")
    return client
