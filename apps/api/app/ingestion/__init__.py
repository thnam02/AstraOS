"""Merchant data ingestion boundary.

External feeds converge here into the canonical AstraOS catalogue.
Downstream decision services do not know the source format.
"""

from app.ingestion.constants import SCHEMA_VERSION
from app.ingestion.result import IngestionIssue, IngestionResult

__all__ = ["SCHEMA_VERSION", "IngestionIssue", "IngestionResult"]
