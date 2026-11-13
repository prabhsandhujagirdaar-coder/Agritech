"""AgriChain AI — Request and response Pydantic schemas."""

from .cnn import CNNModelStatusResponse, CNNPredictionResponse
from .shipment import CreateShipmentRequest, ShipmentRecord, ShipmentStatus
from .telemetry import (
    AddTelemetryRequest,
    GeoWaypointCreate,
    GeoWaypointRecord,
    LSTMPredictionRequest,
    LSTMPredictionResponse,
    TelemetryPoint,
    TelemetryRecord,
)

__all__ = [
    "CNNModelStatusResponse",
    "CNNPredictionResponse",
    "CreateShipmentRequest",
    "ShipmentRecord",
    "ShipmentStatus",
    "AddTelemetryRequest",
    "TelemetryRecord",
    "GeoWaypointCreate",
    "GeoWaypointRecord",
    "TelemetryPoint",
    "LSTMPredictionRequest",
    "LSTMPredictionResponse",
]
