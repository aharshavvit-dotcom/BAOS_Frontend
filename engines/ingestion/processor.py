"""Processor entrypoint for data ingestion."""
from engines.ingestion.ingest import ingest_port_data

Processor = ingest_port_data

__all__ = ["Processor", "ingest_port_data"]
