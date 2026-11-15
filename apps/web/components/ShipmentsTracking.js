"use client";
import React, { useState, useEffect, useRef, useMemo } from "react";
import TrackingMapClient from "./TrackingMapClient";
import {
  fetchShipments,
  fetchShipmentWaypoints,
  fetchShipmentRisk,
  fetchShipmentTelemetry,
  fetchShipmentEvents,
  addShipmentEvent,
  fetchFacilitySuitability,
  createShipment,
  addShipmentWaypoint,
  addShipmentTelemetry,
  simulateShipmentStep,
  evaluateLstmRisk,
  isValidCoordinate,
  isWithinIndia,
  normalizeShipmentCoordinates,
  fetchFacilities,
  fetchShipmentRoute,
  searchSimulationLocations,
  previewSimulationRoute,
  createSimulationSession,
  fetchSimulationSession,
  fetchSimulationSessions,
  controlSimulation,
  updateSimulationControls,
  fetchSimulationTelemetry,
  fetchSimulationHistory,
} from "../lib/api";

export default function ShipmentsTracking({ backendHealth, onRetryHealth }) {
  // Shipments state
  const [shipments, setShipments] = useState([]);
  const [loadingShipments, setLoadingShipments] = useState(true);
  const [shipmentsError, setShipmentsError] = useState(null);

  // Dynamic shipment-specific real-road routing state
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [routeError, setRouteError] = useState(null);

  // Storage facilities state (Godowns, Cold Stores, Packhouses, Mandis)
  const [facilities, setFacilities] = useState([]);
  const [loadingFacilities, setLoadingFacilities] = useState(false);

  // Selected shipment & sub-entities
  const [selectedShipment, setSelectedShipment] = useState(null);
  const [waypoints, setWaypoints] = useState([]);
  const [loadingWaypoints, setLoadingWaypoints] = useState(false);

  // Events state (Phase 13 lifecycle timeline)
  const [events, setEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [showAddEvent, setShowAddEvent] = useState(false);
  const [loggingEvent, setLoggingEvent] = useState(false);
  const [eventFormError, setEventFormError] = useState(null);
  const [newEvent, setNewEvent] = useState({
    event_type: "facility_handover",
    facility_id: "",
    description: "",
    source: "manual_operator",
  });

  const [riskInfo, setRiskInfo] = useState(null);
  const [loadingRisk, setLoadingRisk] = useState(false);

  const [telemetry, setTelemetry] = useState([]);
  const [loadingTelemetry, setLoadingTelemetry] = useState(false);
  const [telemetryError, setTelemetryError] = useState(null);

  // Simulation step state (Legacy Step Trigger)
  const [simulatingStep, setSimulatingStep] = useState(false);
  const [simulateNotice, setSimulateNotice] = useState(null);

  // Dynamic Real-Road Simulation Studio state
  const [simulationActiveTab, setSimulationActiveTab] = useState(true);
  const [simulationsList, setSimulationsList] = useState([]);
  const [activeSimulation, setActiveSimulation] = useState(null);
  const [simulationRoute, setSimulationRoute] = useState(null);
  const [simulationTelemetry, setSimulationTelemetry] = useState([]);

  // Route Planner inputs
  const [simOriginQuery, setSimOriginQuery] = useState("Abohar Kinnow & Guava Packhouse");
  const [simOriginCoords, setSimOriginCoords] = useState({ lat: 30.1453, lon: 74.1994, name: "Abohar Packhouse" });
  const [simOriginResults, setSimOriginResults] = useState([]);
  const [searchingOrigin, setSearchingOrigin] = useState(false);

  const [simDestQuery, setSimDestQuery] = useState("Azadpur APMC Mega Mandi");
  const [simDestCoords, setSimDestCoords] = useState({ lat: 28.7161, lon: 77.1772, name: "Azadpur APMC Mega Mandi" });
  const [simDestResults, setSimDestResults] = useState([]);
  const [searchingDest, setSearchingDest] = useState(false);

  const [previewingRoute, setPreviewingRoute] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [routePreviewData, setRoutePreviewData] = useState(null);

  // Studio Controls & HUD
  const [simSpeedMultiplier, setSimSpeedMultiplier] = useState(2.0);
  const [simScenario, setSimScenario] = useState("normal");
  const [simActionLoading, setSimActionLoading] = useState(false);
  const [mapPickTarget, setMapPickTarget] = useState(null); // 'origin' | 'destination' | null
  const [simAssociateShipmentId, setSimAssociateShipmentId] = useState("");
  // Task 1 & 3: Auto-sync & Route override tracking
  const [isCustomRoute, setIsCustomRoute] = useState(false);

  // Historical Replay
  const [replayMode, setReplayMode] = useState(false);
  const [replayIndex, setReplayIndex] = useState(0);

  // LSTM Evaluation state
  const [evaluatingLstm, setEvaluatingLstm] = useState(false);
  const [lstmResult, setLstmResult] = useState(null);
  const [lstmError, setLstmError] = useState(null);

  // WebSocket state
  const [wsConnected, setWsConnected] = useState(false);

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creatingShipment, setCreatingShipment] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [newShipment, setNewShipment] = useState({
    produce_type: "Guava",
    origin: "",
    destination: "",
    origin_facility_id: "",
    destination_facility_id: "",
    intermediate_facility_id: "",
    origin_operation: "packhouse_cooling",
    destination_operation: "market_auction",
    intermediate_operation: "transit_hub",
    planned_departure: "",
    planned_arrival: "",
    quantity: "",
    status: "in_transit",
  });

  // Facility Suitability Check in Create Modal
  const [originSuitability, setOriginSuitability] = useState(null);
  const [destSuitability, setDestSuitability] = useState(null);
  const [interSuitability, setInterSuitability] = useState(null);
  const [checkingOriginSuit, setCheckingOriginSuit] = useState(false);
  const [checkingDestSuit, setCheckingDestSuit] = useState(false);
  const [checkingInterSuit, setCheckingInterSuit] = useState(false);

  const [showAddTelemetry, setShowAddTelemetry] = useState(false);
  const [loggingTelemetry, setLoggingTelemetry] = useState(false);
  const [telemetryFormError, setTelemetryFormError] = useState(null);
  const [newTelemetry, setNewTelemetry] = useState({
    temperature: "6.2",
    humidity: "86.5",
    sensor_id: "SNS-COLD-01",
    location: "Malout Bypass Corridor",
  });

  const [showAddWaypoint, setShowAddWaypoint] = useState(false);
  const [loggingWaypoint, setLoggingWaypoint] = useState(false);
  const [waypointFormError, setWaypointFormError] = useState(null);
  const [newWaypoint, setNewWaypoint] = useState({
    latitude: "30.1915",
    longitude: "74.4989",
    altitude_m: "192.0",
    speed_kmh: "55.0",
    heading_deg: "75.0",
    checkpoint: "Malout Corridor Checkpoint",
  });

  // Track map view mode (split vs expanded)
  const [mapExpanded, setMapExpanded] = useState(false);
  const [showAllWaypoints, setShowAllWaypoints] = useState(false);
  const [showAllTelemetry, setShowAllTelemetry] = useState(false);

  // Search & Status filters for shipment list
  const [shipmentSearch, setShipmentSearch] = useState("");
  const [shipmentStatusFilter, setShipmentStatusFilter] = useState("all");

  // Computed summary metrics
  const activeInTransitCount = useMemo(() => {
    return shipments.filter((s) => {
      const st = (s.status || "").toLowerCase();
      return st === "in_transit" || st === "in transit" || st === "dispatched";
    }).length;
  }, [shipments]);

  const highRiskCount = useMemo(() => {
    return shipments.filter((s) => (s.risk_index ?? 0) > 40).length;
  }, [shipments]);

  const geolocatedCount = useMemo(() => {
    return shipments.filter((s) => Boolean(normalizeShipmentCoordinates(s))).length;
  }, [shipments]);

  // Filtered shipments based on search and status
  const filteredShipments = useMemo(() => {
    return shipments.filter((s) => {
      if (shipmentStatusFilter !== "all") {
        const st = (s.status || "").toLowerCase();
        if (shipmentStatusFilter === "in_transit") {
          if (st !== "in_transit" && st !== "in transit" && st !== "dispatched") return false;
        } else if (shipmentStatusFilter === "pending") {
          if (st !== "pending" && st !== "created") return false;
        } else if (shipmentStatusFilter === "delivered") {
          if (st !== "delivered" && st !== "completed") return false;
        }
      }
      if (!shipmentSearch.trim()) return true;
      const q = shipmentSearch.toLowerCase();
      return (
        (s.id && String(s.id).toLowerCase().includes(q)) ||
        (s.produce_type && s.produce_type.toLowerCase().includes(q)) ||
        (s.origin && s.origin.toLowerCase().includes(q)) ||
        (s.destination && s.destination.toLowerCase().includes(q)) ||
        (s.origin_facility?.name && s.origin_facility.name.toLowerCase().includes(q)) ||
        (s.destination_facility?.name && s.destination_facility.name.toLowerCase().includes(q))
      );
    });
  }, [shipments, shipmentSearch, shipmentStatusFilter]);

  // Handle ESC key to exit fullscreen map or close modals
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        if (showCreateModal) setShowCreateModal(false);
        else if (showAddEvent) setShowAddEvent(false);
        else if (showAddWaypoint) setShowAddWaypoint(false);
        else if (showAddTelemetry) setShowAddTelemetry(false);
        else if (mapExpanded) setMapExpanded(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mapExpanded, showCreateModal, showAddEvent, showAddWaypoint, showAddTelemetry]);

  // Clean up fullscreen map on unmount
  useEffect(() => {
    return () => {
      setMapExpanded(false);
    };
  }, []);

  // Load all shipments
  const loadShipments = async () => {
    setLoadingShipments(true);
    setShipmentsError(null);
    try {
      const data = await fetchShipments();
      setShipments(data);

      // Preserve selection or select first
      if (data.length > 0) {
        setSelectedShipment((prev) => {
          if (!prev) return data[0];
          const found = data.find((s) => s.id === prev.id);
          return found || data[0];
        });
      } else {
        setSelectedShipment(null);
      }
    } catch (err) {
      setShipmentsError(err.message || "Failed to load shipments");
    } finally {
      setLoadingShipments(false);
    }
  };

  // Load storage facilities (Godowns, Cold Stores, Packhouses, Mandis)
  const loadFacilities = async () => {
    setLoadingFacilities(true);
    try {
      const data = await fetchFacilities();
      setFacilities(data);
    } catch (err) {
      console.error("Failed to load facilities:", err);
    } finally {
      setLoadingFacilities(false);
    }
  };

  // Load sub-resources for selected shipment (waypoints, risk, telemetry, events)
  const loadShipmentDetails = async (shipmentId) => {
    if (!shipmentId) {
      setWaypoints([]);
      setRiskInfo(null);
      setTelemetry([]);
      setEvents([]);
      setLstmResult(null);
      return;
    }

    setLoadingWaypoints(true);
    setLoadingRisk(true);
    setLoadingTelemetry(true);
    setLoadingEvents(true);
    setTelemetryError(null);
    setLstmResult(null);

    // Run parallel fetches
    Promise.allSettled([
      fetchShipmentWaypoints(shipmentId),
      fetchShipmentRisk(shipmentId),
      fetchShipmentTelemetry(shipmentId),
      fetchShipmentEvents(shipmentId),
    ]).then(([wpResult, riskResult, telResult, evResult]) => {
      if (wpResult.status === "fulfilled") {
        setWaypoints(wpResult.value);
      } else {
        setWaypoints([]);
      }
      setLoadingWaypoints(false);

      if (riskResult.status === "fulfilled") {
        setRiskInfo(riskResult.value);
      } else {
        setRiskInfo(null);
      }
      setLoadingRisk(false);

      if (telResult.status === "fulfilled") {
        setTelemetry(telResult.value);
      } else {
        setTelemetry([]);
        setTelemetryError(telResult.reason?.message || "Failed to load telemetry readings");
      }
      setLoadingTelemetry(false);

      if (evResult.status === "fulfilled") {
        setEvents(evResult.value);
      } else {
        setEvents([]);
      }
      setLoadingEvents(false);
    });
  };

  // Initial load
  useEffect(() => {
    loadShipments();
    loadFacilities();
  }, []);

  // Details reload on selection change
  useEffect(() => {
    if (selectedShipment?.id) {
      loadShipmentDetails(selectedShipment.id);
    }
  }, [selectedShipment?.id]);

  // TASK 1: Auto-sync Simulation Studio whenever selected shipment changes
  useEffect(() => {
    if (!selectedShipment) {
      setActiveSimulation(null);
      setSimulationTelemetry([]);
      return;
    }
    setIsCustomRoute(false);
    setSimAssociateShipmentId(selectedShipment.id);

    const origName =
      selectedShipment.origin_facility?.name ||
      selectedShipment.origin ||
      "Origin Mandi / Hub";
    const destName =
      selectedShipment.destination_facility?.name ||
      selectedShipment.destination ||
      "Destination Terminal / Mandi";

    setSimOriginQuery(origName);
    setSimDestQuery(destName);

    if (
      selectedShipment.origin_facility?.latitude != null &&
      selectedShipment.origin_facility?.longitude != null
    ) {
      setSimOriginCoords({
        lat: Number(selectedShipment.origin_facility.latitude),
        lon: Number(selectedShipment.origin_facility.longitude),
        name: origName,
      });
    } else if (selectedShipment.origin_lat != null && selectedShipment.origin_lon != null) {
      setSimOriginCoords({
        lat: Number(selectedShipment.origin_lat),
        lon: Number(selectedShipment.origin_lon),
        name: origName,
      });
    }

    if (
      selectedShipment.destination_facility?.latitude != null &&
      selectedShipment.destination_facility?.longitude != null
    ) {
      setSimDestCoords({
        lat: Number(selectedShipment.destination_facility.latitude),
        lon: Number(selectedShipment.destination_facility.longitude),
        name: destName,
      });
    } else if (selectedShipment.destination_lat != null && selectedShipment.destination_lon != null) {
      setSimDestCoords({
        lat: Number(selectedShipment.destination_lat),
        lon: Number(selectedShipment.destination_lon),
        name: destName,
      });
    }

    // STRICT SESSION ISOLATION: Fetch simulation session specifically for this selected shipment
    fetchSimulationSessions(selectedShipment.id)
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setSimulationsList(list);
        const match = list.find(
          (s) => s.shipment_id === selectedShipment.id && (s.status === "RUNNING" || s.status === "PAUSED" || s.status === "READY")
        );
        if (match) {
          setActiveSimulation(match);
          setSimulationRoute(match.route_geojson);
          fetchSimulationTelemetry(match.id).then(setSimulationTelemetry).catch(() => {});
        } else {
          setActiveSimulation(null);
          setSimulationTelemetry([]);
        }
      })
      .catch(() => {
        setActiveSimulation(null);
        setSimulationTelemetry([]);
      });
  }, [selectedShipment?.id]);

  // Dynamic Real-Road Route fetch for selected shipment with AbortController to prevent race conditions
  useEffect(() => {
    if (!selectedShipment?.id) {
      setSelectedRoute(null);
      setRouteError(null);
      return;
    }

    const controller = new AbortController();
    setSelectedRoute(null);
    setRouteError(null);
    setLoadingRoute(true);

    fetchShipmentRoute(selectedShipment.id, { signal: controller.signal })
      .then((data) => {
        // Prevent race conditions: ensure response belongs to currently selected shipment
        if (data && data.shipment_id === selectedShipment.id) {
          setSelectedRoute(data);

          // TASK 1 & 3: Auto-sync Simulation Studio route if not manually overridden
          setIsCustomRoute((currentIsCustom) => {
            if (!currentIsCustom) {
              setRoutePreviewData(data);
              if (data.geometry) {
                setSimulationRoute(data.geometry);
              }
              if (data.origin) {
                setSimOriginCoords({
                  lat: data.origin.latitude,
                  lon: data.origin.longitude,
                  name: data.origin_name,
                });
                setSimOriginQuery(data.origin_name);
              }
              if (data.destination) {
                setSimDestCoords({
                  lat: data.destination.latitude,
                  lon: data.destination.longitude,
                  name: data.destination_name,
                });
                setSimDestQuery(data.destination_name);
              }
            }
            return currentIsCustom;
          });
        }
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        console.warn(`Could not fetch dynamic route for ${selectedShipment.id}:`, err);
        setRouteError(err.message || "Failed to calculate dynamic route");
      })
      .finally(() => {
        setLoadingRoute(false);
      });

    return () => {
      controller.abort();
    };
  }, [selectedShipment?.id]);

  // Live Suitability validation for selected facilities in modal
  useEffect(() => {
    if (newShipment.origin_facility_id) {
      setCheckingOriginSuit(true);
      fetchFacilitySuitability(newShipment.origin_facility_id, newShipment.origin_operation || "packhouse_cooling", "Guava")
        .then((res) => setOriginSuitability(res))
        .catch(() => setOriginSuitability(null))
        .finally(() => setCheckingOriginSuit(false));
    } else {
      setOriginSuitability(null);
    }
  }, [newShipment.origin_facility_id, newShipment.origin_operation]);

  useEffect(() => {
    if (newShipment.destination_facility_id) {
      setCheckingDestSuit(true);
      fetchFacilitySuitability(newShipment.destination_facility_id, newShipment.destination_operation || "market_auction", "Guava")
        .then((res) => setDestSuitability(res))
        .catch(() => setDestSuitability(null))
        .finally(() => setCheckingDestSuit(false));
    } else {
      setDestSuitability(null);
    }
  }, [newShipment.destination_facility_id, newShipment.destination_operation]);

  useEffect(() => {
    if (newShipment.intermediate_facility_id) {
      setCheckingInterSuit(true);
      fetchFacilitySuitability(newShipment.intermediate_facility_id, newShipment.intermediate_operation || "transit_hub", "Guava")
        .then((res) => setInterSuitability(res))
        .catch(() => setInterSuitability(null))
        .finally(() => setCheckingInterSuit(false));
    } else {
      setInterSuitability(null);
    }
  }, [newShipment.intermediate_facility_id, newShipment.intermediate_operation]);

  // Real-time WebSocket event connection
  useEffect(() => {
    let ws = null;
    let pingInterval = null;
    let reconnectTimeout = null;

    function connect() {
      if (typeof window === "undefined") return;
      try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsHost =
          process.env.NEXT_PUBLIC_WS_URL ||
          `${protocol}//${window.location.hostname}:8000/api/v1/ws/shipments`;

        ws = new WebSocket(wsHost);

        ws.onopen = () => {
          setWsConnected(true);
          pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: "ping" }));
            }
          }, 25000);
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.event === "shipment_created" || msg.event === "shipment_update") {
              loadShipments();
            } else if (msg.event === "waypoint_update" || msg.event === "location_update") {
              loadShipments();
              if (selectedShipment?.id && (msg.data?.shipment_id === selectedShipment.id || msg.data?.id === selectedShipment.id)) {
                fetchShipmentWaypoints(selectedShipment.id).then(setWaypoints).catch(() => {});
              }
            } else if (msg.event === "telemetry_update") {
              loadShipments();
              if (selectedShipment?.id && (msg.data?.shipment_id === selectedShipment.id || msg.data?.id === selectedShipment.id)) {
                fetchShipmentTelemetry(selectedShipment.id).then(setTelemetry).catch(() => {});
                fetchShipmentRisk(selectedShipment.id).then(setRiskInfo).catch(() => {});
              }
            } else if (msg.event === "risk_update") {
              if (selectedShipment?.id && (msg.data?.shipment_id === selectedShipment.id || msg.data?.id === selectedShipment.id)) {
                fetchShipmentRisk(selectedShipment.id).then(setRiskInfo).catch(() => {});
              }
            } else if (msg.event === "event_update") {
              if (selectedShipment?.id && (msg.data?.shipment_id === selectedShipment.id || msg.shipment_id === selectedShipment.id)) {
                fetchShipmentEvents(selectedShipment.id).then(setEvents).catch(() => {});
              }
            } else if (msg.event === "simulation_telemetry_update") {
              const simData = msg.data;
              if (simData) {
                setActiveSimulation((prev) => {
                  if (!prev || (simData.simulation_id && prev.id !== simData.simulation_id)) return prev;
                  return {
                    ...prev,
                    current_lat: simData.telemetry?.latitude ?? prev.current_lat,
                    current_lon: simData.telemetry?.longitude ?? prev.current_lon,
                    current_heading_deg: simData.telemetry?.heading_deg ?? prev.current_heading_deg,
                    current_speed_kmh: simData.telemetry?.speed_kmh ?? prev.current_speed_kmh,
                    current_distance_km: simData.telemetry?.distance_travelled_km ?? prev.current_distance_km,
                    status: simData.status || prev.status,
                    latest_telemetry: simData.telemetry,
                  };
                });
                if (simData.telemetry) {
                  setSimulationTelemetry((prev) => [...prev, simData.telemetry]);
                }
              }
            } else if (msg.event === "simulation_status_update") {
              const simData = msg.data;
              if (simData) {
                setActiveSimulation((prev) =>
                  prev && prev.id === simData.simulation_id
                    ? { ...prev, status: simData.status, speed_multiplier: simData.speed_multiplier, scenario: simData.scenario }
                    : prev
                );
              }
            } else if (msg.event === "simulation_completed") {
              setActiveSimulation((prev) => (prev ? { ...prev, status: "COMPLETED" } : prev));
            }
          } catch {}
        };

        ws.onclose = () => {
          setWsConnected(false);
          if (pingInterval) clearInterval(pingInterval);
          reconnectTimeout = setTimeout(connect, 4000);
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch {
        setWsConnected(false);
      }
    }

    connect();

    return () => {
      if (pingInterval) clearInterval(pingInterval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [selectedShipment?.id]);

  // Corridor Presets for 1-click demonstration
  const CORRIDOR_PRESETS = [
    {
      label: "Abohar ➔ Azadpur APMC Mandi (Delhi)",
      origin: { name: "Abohar Kinnow & Guava Packhouse", lat: 30.1453, lon: 74.1994 },
      dest: { name: "Azadpur APMC Mega Mandi", lat: 28.7161, lon: 77.1772 },
      desc: "NH-7 / NH-9 Northern Interstate Cold Corridor (~360 km)",
    },
    {
      label: "Fazilka CA Store ➔ Ludhiana Agro Cold Chain",
      origin: { name: "Fazilka CA Cold Store Hub", lat: 30.4037, lon: 74.0254 },
      dest: { name: "Ludhiana Agro Cold Chain Terminal", lat: 30.9010, lon: 75.8573 },
      desc: "Muktsar-Moga-Jagraon Agricultural Expressway (~185 km)",
    },
    {
      label: "PAGREXCO Kangmai ➔ Azadpur Mandi (Delhi)",
      origin: { name: "PAGREXCO Kangmai Cold Storage", lat: 31.6677, lon: 75.7923 },
      dest: { name: "Azadpur APMC Mega Mandi", lat: 28.7161, lon: 77.1772 },
      desc: "NH-44 Grand Trunk Commercial Agro Corridor (~390 km)",
    },
    {
      label: "Bathinda Transit Hub ➔ Rohtak Logistics Hub",
      origin: { name: "Bathinda Multimodal Transit Hub", lat: 30.2110, lon: 74.9455 },
      dest: { name: "Rohtak Bypass Food Logistics Hub", lat: 28.8955, lon: 76.6066 },
      desc: "Sirsa-Hisar Cold Freight Corridor (~240 km)",
    },
  ];

  // Initial load of simulation sessions
  useEffect(() => {
    fetchSimulationSessions()
      .then((data) => {
        setSimulationsList(data);
        if (data && data.length > 0 && !activeSimulation && !selectedShipment) {
          const runningOrPaused = data.find((s) => (s.status === "RUNNING" || s.status === "PAUSED") && !s.shipment_id);
          if (runningOrPaused) {
            setActiveSimulation(runningOrPaused);
            setSimulationRoute(runningOrPaused.route_geojson);
            fetchSimulationTelemetry(runningOrPaused.id).then(setSimulationTelemetry).catch(() => {});
          }
        }
      })
      .catch(() => {});
  }, []);

  // Poller for active running simulation to keep UI responsive
  useEffect(() => {
    if (!activeSimulation || activeSimulation.status !== "RUNNING") return;
    const interval = setInterval(async () => {
      try {
        const updated = await fetchSimulationSession(activeSimulation.id);
        setActiveSimulation(updated);
        const tel = await fetchSimulationTelemetry(activeSimulation.id, 100);
        setSimulationTelemetry(tel);
      } catch (err) {
        console.error("Simulation poll error:", err);
      }
    }, 1200);
    return () => clearInterval(interval);
  }, [activeSimulation?.id, activeSimulation?.status]);

  const handleRevertToSelectedShipment = () => {
    if (!selectedShipment) return;
    setIsCustomRoute(false);
    setSimAssociateShipmentId(selectedShipment.id);

    if (selectedRoute) {
      setRoutePreviewData(selectedRoute);
      if (selectedRoute.geometry) {
        setSimulationRoute(selectedRoute.geometry);
      }
      if (selectedRoute.origin) {
        setSimOriginCoords({
          lat: selectedRoute.origin.latitude,
          lon: selectedRoute.origin.longitude,
          name: selectedRoute.origin_name,
        });
        setSimOriginQuery(selectedRoute.origin_name);
      }
      if (selectedRoute.destination) {
        setSimDestCoords({
          lat: selectedRoute.destination.latitude,
          lon: selectedRoute.destination.longitude,
          name: selectedRoute.destination_name,
        });
        setSimDestQuery(selectedRoute.destination_name);
      }
    } else {
      const origName =
        selectedShipment.origin_facility?.name || selectedShipment.origin || "Origin Mandi / Hub";
      const destName =
        selectedShipment.destination_facility?.name || selectedShipment.destination || "Destination Terminal / Mandi";
      setSimOriginQuery(origName);
      setSimDestQuery(destName);
      if (selectedShipment.origin_facility?.latitude != null && selectedShipment.origin_facility?.longitude != null) {
        setSimOriginCoords({
          lat: Number(selectedShipment.origin_facility.latitude),
          lon: Number(selectedShipment.origin_facility.longitude),
          name: origName,
        });
      }
      if (selectedShipment.destination_facility?.latitude != null && selectedShipment.destination_facility?.longitude != null) {
        setSimDestCoords({
          lat: Number(selectedShipment.destination_facility.latitude),
          lon: Number(selectedShipment.destination_facility.longitude),
          name: destName,
        });
      }
    }
  };

  const handleSelectPreset = (preset) => {
    setIsCustomRoute(true);
    setSimOriginQuery(preset.origin.name);
    setSimOriginCoords(preset.origin);
    setSimDestQuery(preset.dest.name);
    setSimDestCoords(preset.dest);
    triggerRoutePreview(preset.origin, preset.dest);
  };

  const triggerRoutePreview = async (origin, dest) => {
    setPreviewingRoute(true);
    setPreviewError(null);
    try {
      const preview = await previewSimulationRoute({
        origin_lat: origin.lat,
        origin_lon: origin.lon,
        destination_lat: dest.lat,
        destination_lon: dest.lon,
        origin_name: origin.name,
        destination_name: dest.name,
      });
      setRoutePreviewData(preview);
      setSimulationRoute(preview.geometry);
    } catch (err) {
      setPreviewError(err.message || "Route calculation failed");
    } finally {
      setPreviewingRoute(false);
    }
  };

  const handleSearchOrigin = async (q) => {
    setIsCustomRoute(true);
    setSimOriginQuery(q);
    if (!q || q.trim().length < 2) {
      setSimOriginResults([]);
      return;
    }
    setSearchingOrigin(true);
    try {
      const res = await searchSimulationLocations(q, 6);
      setSimOriginResults(res);
    } catch {
      setSimOriginResults([]);
    } finally {
      setSearchingOrigin(false);
    }
  };

  const handleSearchDest = async (q) => {
    setIsCustomRoute(true);
    setSimDestQuery(q);
    if (!q || q.trim().length < 2) {
      setSimDestResults([]);
      return;
    }
    setSearchingDest(true);
    try {
      const res = await searchSimulationLocations(q, 6);
      setSimDestResults(res);
    } catch {
      setSimDestResults([]);
    } finally {
      setSearchingDest(false);
    }
  };

  const handleCreateSimulationSession = async (autoStart = false) => {
    setSimActionLoading(true);
    try {
      const activeShipmentId = !isCustomRoute && selectedShipment ? selectedShipment.id : (simAssociateShipmentId || null);
      const activeTotalDist = routePreviewData?.distance_km || selectedRoute?.distance_km || null;
      const activeRouteId = routePreviewData?.route_identifier || (activeShipmentId ? `ROUTE-${activeShipmentId}-${activeTotalDist}` : null);
      const activeGeom = routePreviewData?.geometry || selectedRoute?.geometry || simulationRoute;

      const payload = {
        shipment_id: activeShipmentId,
        route_identifier: activeRouteId,
        origin_name: simOriginCoords.name || simOriginQuery,
        origin_lat: simOriginCoords.lat,
        origin_lon: simOriginCoords.lon,
        destination_name: simDestCoords.name || simDestQuery,
        destination_lat: simDestCoords.lat,
        destination_lon: simDestCoords.lon,
        total_distance_km: activeTotalDist,
        speed_multiplier: simSpeedMultiplier,
        scenario: simScenario,
        route_geometry: activeGeom,
      };
      let session = await createSimulationSession(payload);
      if (autoStart && session?.id) {
        session = await controlSimulation(session.id, "start");
      }
      setActiveSimulation(session);
      setSimulationRoute(session.route_geojson);
      setSimulationTelemetry([]);
      setSimulationsList((prev) => [session, ...prev.filter((s) => s.id !== session.id)]);
      return session;
    } catch (err) {
      alert("Failed to initialize simulation: " + err.message);
      return null;
    } finally {
      setSimActionLoading(false);
    }
  };

  const handleControlAction = async (action, advanceKm = null) => {
    if (!activeSimulation) {
      if (action === "start") {
        await handleCreateSimulationSession(true);
      }
      return;
    }
    setSimActionLoading(true);
    try {
      const updated = await controlSimulation(activeSimulation.id, action, advanceKm);
      setActiveSimulation(updated);
      if (action === "reset" || action === "stop") {
        setSimulationRoute(null);
      }
      const tel = await fetchSimulationTelemetry(activeSimulation.id, 100);
      setSimulationTelemetry(tel);
    } catch (err) {
      alert(`Simulation action '${action}' error: ${err.message}`);
    } finally {
      setSimActionLoading(false);
    }
  };

  const handleUpdateControls = async (multiplier, scenario) => {
    if (!activeSimulation) return;
    setSimSpeedMultiplier(multiplier);
    setSimScenario(scenario);
    try {
      const updated = await updateSimulationControls(activeSimulation.id, {
        speed_multiplier: multiplier,
        scenario,
      });
      setActiveSimulation(updated);
    } catch (err) {
      console.error("Control update failed:", err);
    }
  };

  const handleMapPick = (coords) => {
    setIsCustomRoute(true);
    if (mapPickTarget === "origin") {
      const loc = { lat: coords[0], lon: coords[1], name: `Map Fix (${coords[0].toFixed(3)}°N, ${coords[1].toFixed(3)}°E)` };
      setSimOriginCoords(loc);
      setSimOriginQuery(loc.name);
      setMapPickTarget(null);
    } else if (mapPickTarget === "destination") {
      const loc = { lat: coords[0], lon: coords[1], name: `Map Fix (${coords[0].toFixed(3)}°N, ${coords[1].toFixed(3)}°E)` };
      setSimDestCoords(loc);
      setSimDestQuery(loc.name);
      setMapPickTarget(null);
    }
  };

  // Create Shipment (Phase 13: Multi-hub & Facility Suitability Integration)
  const handleCreateShipment = async (e) => {
    e.preventDefault();
    setCreatingShipment(true);
    setCreateError(null);

    const payload = {
      produce_type: newShipment.produce_type.trim(),
      origin: newShipment.origin.trim(),
      destination: newShipment.destination.trim(),
      quantity: parseFloat(newShipment.quantity) || 0,
      status: newShipment.status || "created",
      origin_facility_id: newShipment.origin_facility_id || undefined,
      destination_facility_id: newShipment.destination_facility_id || undefined,
      intermediate_facility_id: newShipment.intermediate_facility_id || undefined,
      origin_operation: newShipment.origin_operation || undefined,
      destination_operation: newShipment.destination_operation || undefined,
      intermediate_operation: newShipment.intermediate_operation || undefined,
      planned_departure: newShipment.planned_departure ? new Date(newShipment.planned_departure).toISOString() : undefined,
      planned_arrival: newShipment.planned_arrival ? new Date(newShipment.planned_arrival).toISOString() : undefined,
    };

    try {
      const created = await createShipment(payload);
      setShowCreateModal(false);
      setNewShipment({
        produce_type: "Guava",
        origin: "",
        destination: "",
        origin_facility_id: "",
        destination_facility_id: "",
        intermediate_facility_id: "",
        origin_operation: "packhouse_cooling",
        destination_operation: "market_auction",
        intermediate_operation: "transit_hub",
        planned_departure: "",
        planned_arrival: "",
        quantity: "",
        status: "in_transit",
      });
      setOriginSuitability(null);
      setDestSuitability(null);
      setInterSuitability(null);
      await loadShipments();
      setSelectedShipment(created);
    } catch (err) {
      setCreateError(err.message || "Failed to create shipment");
    } finally {
      setCreatingShipment(false);
    }
  };

  // Phase 13: Add Shipment Event (Auditable Timeline)
  const handleAddEvent = async (e) => {
    e.preventDefault();
    if (!selectedShipment?.id) return;
    setLoggingEvent(true);
    setEventFormError(null);

    const payload = {
      event_type: newEvent.event_type,
      facility_id: newEvent.facility_id || undefined,
      description: newEvent.description.trim(),
      source: newEvent.source || "manual_operator",
    };

    try {
      await addShipmentEvent(selectedShipment.id, payload);
      setShowAddEvent(false);
      setNewEvent({
        event_type: "facility_handover",
        facility_id: "",
        description: "",
        source: "manual_operator",
      });
      const evs = await fetchShipmentEvents(selectedShipment.id);
      setEvents(evs);
      await loadShipments();
    } catch (err) {
      setEventFormError(err.message || "Failed to record event");
    } finally {
      setLoggingEvent(false);
    }
  };

  // Add Telemetry Reading
  const handleAddTelemetry = async (e) => {
    e.preventDefault();
    if (!selectedShipment?.id) return;
    setLoggingTelemetry(true);
    setTelemetryFormError(null);

    const payload = {
      temperature: parseFloat(newTelemetry.temperature),
      humidity: parseFloat(newTelemetry.humidity),
      sensor_id: newTelemetry.sensor_id.trim() || undefined,
      location: newTelemetry.location.trim() || undefined,
    };

    try {
      await addShipmentTelemetry(selectedShipment.id, payload);
      setShowAddTelemetry(false);
      // Refresh telemetry and risk
      const [tel, rk] = await Promise.all([
        fetchShipmentTelemetry(selectedShipment.id),
        fetchShipmentRisk(selectedShipment.id),
      ]);
      setTelemetry(tel);
      setRiskInfo(rk);
    } catch (err) {
      setTelemetryFormError(err.message || "Failed to record reading");
    } finally {
      setLoggingTelemetry(false);
    }
  };

  // Add GPS Waypoint
  const handleAddWaypoint = async (e) => {
    e.preventDefault();
    if (!selectedShipment?.id) return;
    setLoggingWaypoint(true);
    setWaypointFormError(null);

    const lat = parseFloat(newWaypoint.latitude);
    const lon = parseFloat(newWaypoint.longitude);

    if (!isValidCoordinate(lat, lon)) {
      setWaypointFormError("Latitude must be between -90 and 90, and Longitude between -180 and 180.");
      setLoggingWaypoint(false);
      return;
    }

    if (!isWithinIndia(lat, lon)) {
      setWaypointFormError("Coordinates must fall within Indian territory (Lat 8.0°-37.5°N, Lon 68.0°-97.5°E).");
      setLoggingWaypoint(false);
      return;
    }

    const payload = {
      latitude: lat,
      longitude: lon,
      altitude_m: newWaypoint.altitude_m ? parseFloat(newWaypoint.altitude_m) : undefined,
      speed_kmh: newWaypoint.speed_kmh ? parseFloat(newWaypoint.speed_kmh) : undefined,
      heading_deg: newWaypoint.heading_deg ? parseFloat(newWaypoint.heading_deg) : undefined,
      location_metadata: {
        checkpoint: newWaypoint.checkpoint.trim() || "Manual Route Point",
      },
    };

    try {
      await addShipmentWaypoint(selectedShipment.id, payload);
      setShowAddWaypoint(false);
      // Refresh waypoints & shipments list so map marker updates immediately
      const [wps, shps] = await Promise.all([
        fetchShipmentWaypoints(selectedShipment.id),
        fetchShipments(),
      ]);
      setWaypoints(wps);
      setShipments(shps);
      const updatedSel = shps.find((s) => s.id === selectedShipment.id);
      if (updatedSel) setSelectedShipment(updatedSel);
    } catch (err) {
      setWaypointFormError(err.message || "Failed to record GPS waypoint");
    } finally {
      setLoggingWaypoint(false);
    }
  };

  // Run LSTM Risk Scoring
  const handleRunLstm = async () => {
    if (!selectedShipment?.id) return;
    setEvaluatingLstm(true);
    setLstmError(null);

    try {
      // Build 24-step sequence from telemetry or simulate steps based on real readings
      const baseTemp = selectedShipment.temperature_c ?? 6.2;
      const sequence = Array.from({ length: 24 }, (_, i) => ({
        hour: i,
        temperature: telemetry[i]?.temperature ?? baseTemp + (Math.sin(i / 3) * 1.2),
        humidity: telemetry[i]?.humidity ?? 85.0,
        delay_minutes: 0,
        speed_kmh: 55.0,
        distance_remaining_km: Math.max(0, 300 - i * 12),
      }));

      const res = await evaluateLstmRisk({
        shipment_id: selectedShipment.id,
        sequence,
      });
      setLstmResult(res);
    } catch (err) {
      setLstmError(err.message || "Failed to evaluate LSTM model");
    } finally {
      setEvaluatingLstm(false);
    }
  };

  // Trigger Demo Transit Simulation Step (POST /api/shipments/[id]/simulate-step)
  const handleSimulateStep = async () => {
    if (!selectedShipment?.id) return;
    setSimulatingStep(true);
    setSimulateNotice(null);
    try {
      const res = await simulateShipmentStep(selectedShipment.id);
      setSimulateNotice({
        type: "success",
        message: `Corridor step simulated: ${res.waypoint?.latitude?.toFixed(4)}°N, ${res.waypoint?.longitude?.toFixed(4)}°E (${res.telemetry?.temperature}°C). [DEMO / SIMULATION ONLY — not verified GPS]`,
      });
      await loadShipments();
      await loadShipmentDetails(selectedShipment.id);
    } catch (err) {
      setSimulateNotice({
        type: "error",
        message: err.message || "Failed to trigger simulation step",
      });
    } finally {
      setSimulatingStep(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case "delivered":
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
      case "in_transit":
        return "bg-sky-100 text-sky-800 border-sky-200";
      case "delayed":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "quarantined":
        return "bg-rose-100 text-rose-800 border-rose-200";
      case "created":
      default:
        return "bg-slate-100 text-slate-800 border-slate-200";
    }
  };

  const getTempColor = (temp) => {
    if (temp == null || typeof temp !== "number") return "text-outline";
    if (temp > 8.0) return "text-rose-600";
    if (temp < 4.0) return "text-amber-600";
    return "text-digital-mint";
  };

  const getTempBadge = (temp) => {
    if (temp == null || typeof temp !== "number") return "bg-surface-container-high text-outline";
    if (temp > 8.0) return "bg-rose-100 text-rose-800 border border-rose-200";
    if (temp < 4.0) return "bg-amber-100 text-amber-800 border border-amber-200";
    return "bg-digital-mint/15 text-emerald-forest border border-digital-mint/30";
  };

  const latestReading = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
  const temps = telemetry.map((r) => r.temperature).filter((t) => typeof t === "number");
  const humids = telemetry.map((r) => r.humidity).filter((h) => typeof h === "number");
  const avgTemp = temps.length ? (temps.reduce((a, b) => a + b, 0) / temps.length).toFixed(1) : null;
  const avgHumid = humids.length ? (humids.reduce((a, b) => a + b, 0) / humids.length).toFixed(1) : null;
  // Phase 13 Helpers: Honest Tracking & Telemetry Transparency
  const getTrackingModeInfo = (shipment, wps) => {
    const mode = shipment?.tracking_mode;
    const hasSimulatedWp = wps?.some(
      (w) =>
        w.location_metadata?.source === "demo_simulated" ||
        w.location_metadata?.simulated === true ||
        w.location_metadata?.label?.includes("SIMULATED")
    );
    const hasLiveWp = wps?.some((w) => w.location_metadata?.source === "live_gps");

    if (mode === "live_gps" || (hasLiveWp && !hasSimulatedWp)) {
      return {
        label: "LIVE GPS ACTIVE",
        subtext: "Verified hardware GNSS feed reporting real-time coordinates",
        badgeClass: "bg-emerald-600 text-white border-emerald-700 shadow-sm",
        icon: "satellite_alt",
        pulse: true,
      };
    }
    if (mode === "last_known" || shipment?.status === "delivered") {
      return {
        label: "LAST KNOWN LOCATION",
        subtext: "Live hardware signal disconnected — coordinates preserved from last verified fix",
        badgeClass: "bg-slate-700 text-white border-slate-800",
        icon: "history_toggle_off",
        pulse: false,
      };
    }
    return {
      label: "DEMO / SIMULATED ROUTE",
      subtext: "Synthetic PostGIS coordinates for demonstration (No active hardware GPS tracker connected)",
      badgeClass: "bg-amber-600 text-white border-amber-700 shadow-sm",
      icon: "science",
      pulse: false,
    };
  };

  const getTelemetryModeInfo = (shipment, telem) => {
    const mode = shipment?.telemetry_mode;
    if (mode === "live_sensor") {
      return {
        label: "LIVE IOT SENSOR STREAM",
        subtext: "Physical certified probe transmitting real-time temperature & humidity",
        badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-300",
        icon: "sensors",
        isDemo: false,
      };
    }
    if (mode === "unavailable" || telem.length === 0) {
      return {
        label: "SENSOR HARDWARE UNAVAILABLE",
        subtext: "No physical IoT thermal probe connected. Sensor readings are unavailable.",
        badgeClass: "bg-slate-100 text-slate-700 border-slate-300",
        icon: "sensors_off",
        isDemo: false,
      };
    }
    return {
      label: "SIMULATED TELEMETRY (DEMO)",
      subtext: "Temperature and humidity values are synthetically simulated for demonstration purposes. No real probe connected.",
      badgeClass: "bg-amber-50 text-amber-900 border-amber-300",
      icon: "science",
      isDemo: true,
    };
  };

  const renderCapabilityChip = (label, status) => {
    const s = String(status || "unknown").toLowerCase();
    let color = "bg-slate-100 text-slate-700 border-slate-200";
    let icon = "help_outline";
    let display = "Unknown";

    if (s === "verified") {
      color = "bg-emerald-100 text-emerald-800 border-emerald-300 font-bold";
      icon = "verified";
      display = "Verified";
    } else if (s === "partially_verified") {
      color = "bg-amber-100 text-amber-900 border-amber-300 font-semibold";
      icon = "warning";
      display = "Partial";
    } else if (s === "unsuitable") {
      color = "bg-rose-100 text-rose-800 border-rose-300 font-bold";
      icon = "cancel";
      display = "Unsuitable";
    } else if (s === "active") {
      color = "bg-emerald-100 text-emerald-800 border-emerald-300 font-bold";
      icon = "check_circle";
      display = "Active";
    } else if (s === "unconfirmed" || s === "unknown") {
      color = "bg-slate-100 text-slate-600 border-slate-200";
      icon = "help_outline";
      display = "Unconfirmed";
    }

    return (
      <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border ${color}`} title={`${label}: ${display}`}>
        <span className="material-symbols-outlined text-[11px]">{icon}</span>
        <span>{label}: <strong>{display}</strong></span>
      </span>
    );
  };

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case "shipment_created":
        return { icon: "add_circle", color: "text-emerald-600 bg-emerald-50 border-emerald-200" };
      case "facility_association_updated":
        return { icon: "hub", color: "text-purple-600 bg-purple-50 border-purple-200" };
      case "shipment_dispatched":
        return { icon: "local_shipping", color: "text-sky-600 bg-sky-50 border-sky-200" };
      case "in_transit":
        return { icon: "navigation", color: "text-sky-600 bg-sky-50 border-sky-200" };
      case "arrival_recorded":
        return { icon: "where_to_vote", color: "text-indigo-600 bg-indigo-50 border-indigo-200" };
      case "facility_handover":
        return { icon: "handshake", color: "text-amber-600 bg-amber-50 border-amber-200" };
      case "delivery_completed":
        return { icon: "task_alt", color: "text-emerald-700 bg-emerald-100 border-emerald-300" };
      case "tracking_signal_lost":
        return { icon: "signal_disconnected", color: "text-rose-600 bg-rose-50 border-rose-200" };
      case "tracking_signal_restored":
        return { icon: "cell_tower", color: "text-emerald-600 bg-emerald-50 border-emerald-200" };
      case "temperature_excursion_alert":
        return { icon: "warning", color: "text-rose-600 bg-rose-100 border-rose-300" };
      default:
        return { icon: "radio_button_checked", color: "text-slate-600 bg-slate-50 border-slate-200" };
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Banner & Control Bar */}
      <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="font-bold text-lg text-emerald-forest flex items-center gap-2">
              <span className="material-symbols-outlined text-digital-mint">travel_explore</span>
              PostGIS Geospatial Tracking &amp; Cold-Chain Ledger
            </h3>
            {/* FastAPI REST API Health Indicator */}
            {backendHealth?.status === "checking" ? (
              <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border bg-amber-500/15 text-amber-800 border-amber-500/30 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                FastAPI Checking...
              </span>
            ) : (backendHealth?.status === "healthy" || backendHealth?.api_status === "online") ? (
              <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border bg-digital-mint/15 text-emerald-forest border-digital-mint/30 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-digital-mint"></span>
                FastAPI Online {backendHealth?.latencyMs ? `(${backendHealth.latencyMs}ms)` : ""}
              </span>
            ) : (
              <div className="flex items-center gap-1.5">
                <span
                  className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border bg-error/15 text-error border-error/30 flex items-center gap-1.5"
                  title={backendHealth?.error || "FastAPI server unreachable at http://127.0.0.1:8000"}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
                  FastAPI Offline
                </span>
                {onRetryHealth && (
                  <button
                    onClick={onRetryHealth}
                    title="Retry connecting to FastAPI"
                    className="p-1 hover:bg-surface-container-high rounded-md text-error hover:text-primary transition-colors flex items-center"
                    aria-label="Retry connection"
                  >
                    <span className="material-symbols-outlined text-xs">refresh</span>
                  </button>
                )}
              </div>
            )}

            {/* Database / Ledger Mode Indicator */}
            <span
              className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border bg-surface-container-high text-on-surface-variant border-outline-variant/60"
              title={backendHealth?.database?.message || "File-based session persistence active"}
            >
              DB: {backendHealth?.database?.enabled ? (backendHealth?.database?.connected ? "PostGIS Online" : "PostGIS Offline") : "File Ledger"}
            </span>

            {/* WebSocket Streaming Indicator */}
            <span
              className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border flex items-center gap-1.5 ${
                wsConnected
                  ? "bg-digital-mint/15 text-emerald-forest border-digital-mint/30"
                  : "bg-surface-container-high text-on-surface-variant border-outline-variant/60"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? "bg-digital-mint animate-pulse" : "bg-outline"}`}></span>
              WS {wsConnected ? "Streaming" : "Standby"}
            </span>
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            Real-time PostGIS (SRID 4326) waypoint positioning, sensor telemetry, and thermal spoilage risk engine.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={() => setMapExpanded(!mapExpanded)}
            className="flex-1 md:flex-none border border-outline-variant/60 hover:bg-surface-container-high text-primary px-3.5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-colors"
          >
            <span className="material-symbols-outlined text-sm">
              {mapExpanded ? "view_sidebar" : "fullscreen"}
            </span>
            {mapExpanded ? "Split View" : "Expand Map"}
          </button>

          <button
            onClick={() => {
              loadShipments();
              loadFacilities();
              if (selectedShipment?.id) loadShipmentDetails(selectedShipment.id);
            }}
            className="flex-1 md:flex-none border border-outline-variant/60 hover:bg-surface-container-high text-primary px-3.5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-colors"
            title="Refresh Ledger"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            Refresh
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex-1 md:flex-none bg-emerald-forest hover:bg-primary text-white px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 shadow-sm transition-colors"
          >
            <span className="material-symbols-outlined text-sm">add</span>
            New Shipment
          </button>
        </div>
      </div>

      {/* Backend Offline Explanatory Banner */}
      {(backendHealth?.status === "offline" || shipmentsError) && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fade-in">
          <div className="flex items-start gap-3 text-xs">
            <span className="material-symbols-outlined text-amber-700 text-2xl shrink-0 mt-0.5">cloud_off</span>
            <div>
              <h4 className="font-bold text-amber-950 uppercase tracking-wide">FastAPI Backend Offline — Simulated Demo Mode Active</h4>
              <p className="text-amber-900 mt-1 leading-relaxed">
                Unable to reach FastAPI backend at <code className="bg-amber-200/50 px-1 py-0.5 rounded font-mono font-bold text-amber-950">http://127.0.0.1:8000</code>.
                Displaying cached demo tracking waypoints. Start the backend with:
                <code className="block mt-1 bg-amber-200/60 text-amber-950 px-2 py-1 rounded font-mono text-[11px] w-max">
                  uvicorn app.main:app --host 127.0.0.1 --port 8000
                </code>
              </p>
              {shipmentsError && (
                <p className="text-amber-800 text-[11px] mt-1">
                  Detail: <code className="font-mono">{shipmentsError}</code>
                </p>
              )}
            </div>
          </div>
          {onRetryHealth && (
            <button
              onClick={onRetryHealth}
              className="px-3.5 py-2 bg-amber-800 hover:bg-amber-900 text-white rounded-xl text-xs font-bold shrink-0 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <span className="material-symbols-outlined text-sm">refresh</span>
              Retry Health Check
            </button>
          )}
        </div>
      )}

      {/* SECTION 2: SUMMARY METRICS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
        {/* Metric 1: Total Shipments */}
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-outline-variant/60 premium-shadow flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-2xl">inventory_2</span>
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Registered Batches</span>
            <span className="text-xl sm:text-2xl font-extrabold text-primary font-mono">{shipments.length}</span>
            <span className="text-[10px] text-on-surface-variant block truncate">Ledger synchronized</span>
          </div>
        </div>

        {/* Metric 2: Active in Transit */}
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-outline-variant/60 premium-shadow flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-sky-100 text-sky-800 flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-2xl">local_shipping</span>
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Active Transit</span>
            <span className="text-xl sm:text-2xl font-extrabold text-sky-900 font-mono">{activeInTransitCount}</span>
            <span className="text-[10px] text-on-surface-variant block truncate">Moving corridors</span>
          </div>
        </div>

        {/* Metric 3: GPS Coordinates */}
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-outline-variant/60 premium-shadow flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-purple-100 text-purple-800 flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-2xl">pin_drop</span>
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">GPS Fixes</span>
            <span className="text-xl sm:text-2xl font-extrabold text-purple-900 font-mono">{geolocatedCount}</span>
            <span className="text-[10px] text-on-surface-variant block truncate">PostGIS EPSG:4326</span>
          </div>
        </div>

        {/* Metric 4: Cold-Chain Thermal Risk Alerts */}
        <div className={`rounded-2xl p-4 sm:p-5 border premium-shadow flex items-center gap-3.5 transition-colors ${
          highRiskCount > 0
            ? "bg-rose-50/80 border-rose-200 text-rose-950"
            : "bg-white border-outline-variant/60"
        }`}>
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${
            highRiskCount > 0 ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-800"
          }`}>
            <span className="material-symbols-outlined text-2xl">
              {highRiskCount > 0 ? "warning" : "health_and_safety"}
            </span>
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Thermal Alerts</span>
            <span className={`text-xl sm:text-2xl font-extrabold font-mono ${
              highRiskCount > 0 ? "text-rose-700" : "text-emerald-800"
            }`}>
              {highRiskCount}
            </span>
            <span className="text-[10px] text-on-surface-variant block truncate">
              {highRiskCount > 0 ? "Thermal excursion (>40%)" : "Optimal 4°C–8°C window"}
            </span>
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* SECTION 3.5: DYNAMIC REAL-ROAD VEHICLE SIMULATION & COLD-CHAIN STUDIO */}
      {/* ===================================================================== */}
      <div className="bg-gradient-to-br from-white via-slate-50 to-emerald-50/30 rounded-2xl p-5 sm:p-6 border border-emerald-900/15 premium-shadow flex flex-col gap-5">
        {/* Studio Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3 border-b border-outline-variant/40 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-700 text-white flex items-center justify-center shadow-md">
              <span className="material-symbols-outlined text-2xl">route</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-emerald-950 uppercase tracking-wide">
                  Dynamic Real-Road Vehicle Simulation Studio
                </h3>
                <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider border border-emerald-300">
                  Authoritative Engine
                </span>
              </div>
              <p className="text-xs text-on-surface-variant mt-0.5 max-w-2xl">
                Simulates real-road commercial transit along Indian highway networks (LineString geometry). Features distance-based polyline interpolation, synthetic sensor telemetry, and 24-step cold-chain risk scoring (rule-based estimator; trained LSTM pending).
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end md:self-auto">
            {mapPickTarget && (
              <span className="text-xs bg-amber-100 text-amber-900 font-bold px-3 py-1 rounded-xl border border-amber-300 animate-pulse">
                Click map to set {mapPickTarget}
              </span>
            )}
            <button
              onClick={() => setSimulationActiveTab(!simulationActiveTab)}
              className="text-xs font-bold text-slate-700 hover:text-emerald-800 bg-white border border-outline-variant/60 hover:bg-slate-50 px-3.5 py-1.5 rounded-xl shadow-sm flex items-center gap-1.5 transition-colors"
            >
              <span className="material-symbols-outlined text-sm">
                {simulationActiveTab ? "expand_less" : "tune"}
              </span>
              {simulationActiveTab ? "Collapse Studio" : "Open Studio Deck"}
            </button>
          </div>
        </div>

        {simulationActiveTab && (
          <div className="flex flex-col gap-5 animate-fade-in">
            {/* TASK 1 & 3: Auto-Sync Selected Shipment Link Banner */}
            {selectedShipment && (
              <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-sky-50 border border-emerald-200/80 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-sm">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 animate-pulse"></span>
                    <span className="text-xs font-bold text-emerald-950 font-mono">
                      #{selectedShipment.id}
                    </span>
                    <span className="text-xs text-emerald-800 font-semibold">
                      ({selectedShipment.produce_type || "Guava"} • {selectedShipment.quantity ? `${selectedShipment.quantity} kg` : "N/A"})
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 flex items-center gap-1.5">
                    <span className="font-semibold text-slate-800">{selectedShipment.origin || "Origin"}</span>
                    <span>&rarr;</span>
                    <span className="font-semibold text-slate-800">{selectedShipment.destination || "Destination"}</span>
                  </div>
                  {selectedRoute?.distance_km && (
                    <span className="text-[11px] font-mono font-bold bg-white text-emerald-900 border border-emerald-300 px-2 py-0.5 rounded-md shadow-xs">
                      🛣️ {selectedRoute.distance_km} km
                    </span>
                  )}
                  {selectedRoute?.duration_s && (
                    <span className="text-[11px] font-mono font-bold bg-white text-slate-700 border border-slate-200 px-2 py-0.5 rounded-md shadow-xs">
                      ⏱️ {(selectedRoute.duration_s / 3600).toFixed(1)} hrs
                    </span>
                  )}
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    Status: {selectedShipment.status}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {isCustomRoute ? (
                    <>
                      <span className="bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-amber-600"></span>
                        Custom Route
                      </span>
                      <button
                        onClick={handleRevertToSelectedShipment}
                        className="text-[11px] font-bold bg-white hover:bg-emerald-50 text-emerald-700 border border-emerald-300 px-2.5 py-1 rounded-lg transition-colors shadow-xs flex items-center gap-1"
                        title="Revert simulation inputs to selected shipment's route"
                      >
                        <span className="material-symbols-outlined text-xs">sync</span>
                        Use Selected Shipment Route
                      </button>
                    </>
                  ) : (
                    <span className="bg-emerald-100 text-emerald-800 border border-emerald-300 text-[10px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1.5 shadow-xs">
                      <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
                      Using Selected Shipment
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Quick Presets Bar */}
            <div className="flex flex-col gap-2 bg-white/80 backdrop-blur-sm p-3.5 rounded-xl border border-outline-variant/50">
              <span className="text-[11px] font-bold text-outline uppercase tracking-wider flex items-center gap-1.5">
                <span className="material-symbols-outlined text-xs text-emerald-600">bolt</span>
                1-Click Indian Agro Corridor Presets:
              </span>
              <div className="flex flex-wrap gap-2">
                {CORRIDOR_PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSelectPreset(preset)}
                    className="text-xs font-medium bg-slate-100 hover:bg-emerald-100/70 hover:text-emerald-900 text-slate-800 px-3 py-1.5 rounded-lg border border-outline-variant/40 transition-colors flex items-center gap-1"
                  >
                    <span>{preset.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Dynamic Route Planner Grid */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
              {/* Origin Search */}
              <div className="md:col-span-5 relative">
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-bold text-emerald-900 uppercase tracking-wide flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-600"></span> Origin Mandi / Hub
                  </label>
                  <button
                    onClick={() => setMapPickTarget(mapPickTarget === "origin" ? null : "origin")}
                    className={`text-[10px] font-bold px-2 py-0.5 rounded transition-colors ${
                      mapPickTarget === "origin" ? "bg-amber-500 text-white" : "text-emerald-700 hover:underline"
                    }`}
                  >
                    {mapPickTarget === "origin" ? "Cancel Pick" : "📍 Pick on Map"}
                  </button>
                </div>
                <input
                  type="text"
                  value={simOriginQuery}
                  onChange={(e) => handleSearchOrigin(e.target.value)}
                  placeholder="Search Indian mandi, packhouse, or city..."
                  className="w-full bg-white border border-outline-variant rounded-xl p-2.5 text-xs font-semibold focus:outline-none focus:border-emerald-600 shadow-sm"
                />
                {searchingOrigin && (
                  <span className="absolute right-3 top-8 text-[10px] text-slate-400">Searching...</span>
                )}
                {simOriginResults.length > 0 && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-outline-variant rounded-xl shadow-xl z-30 max-h-48 overflow-y-auto">
                    {simOriginResults.map((loc, i) => (
                      <div
                        key={i}
                        onClick={() => {
                          setIsCustomRoute(true);
                          setSimOriginCoords({ lat: loc.latitude, lon: loc.longitude, name: loc.name });
                          setSimOriginQuery(loc.name);
                          setSimOriginResults([]);
                        }}
                        className="px-3 py-2 hover:bg-emerald-50 cursor-pointer border-b border-outline-variant/30 text-xs"
                      >
                        <div className="font-bold text-slate-800">{loc.name}</div>
                        <div className="text-[10px] text-slate-500 truncate">{loc.display_name}</div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="text-[10px] text-slate-500 font-mono mt-1">
                  GPS: {simOriginCoords.lat.toFixed(4)}° N, {simOriginCoords.lon.toFixed(4)}° E
                </div>
              </div>

              {/* Destination Search */}
              <div className="md:col-span-5 relative">
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-bold text-rose-900 uppercase tracking-wide flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-600"></span> Destination Mandi / Terminal
                  </label>
                  <button
                    onClick={() => setMapPickTarget(mapPickTarget === "destination" ? null : "destination")}
                    className={`text-[10px] font-bold px-2 py-0.5 rounded transition-colors ${
                      mapPickTarget === "destination" ? "bg-amber-500 text-white" : "text-rose-700 hover:underline"
                    }`}
                  >
                    {mapPickTarget === "destination" ? "Cancel Pick" : "📍 Pick on Map"}
                  </button>
                </div>
                <input
                  type="text"
                  value={simDestQuery}
                  onChange={(e) => handleSearchDest(e.target.value)}
                  placeholder="Search Indian terminal, godown, or city..."
                  className="w-full bg-white border border-outline-variant rounded-xl p-2.5 text-xs font-semibold focus:outline-none focus:border-emerald-600 shadow-sm"
                />
                {searchingDest && (
                  <span className="absolute right-3 top-8 text-[10px] text-slate-400">Searching...</span>
                )}
                {simDestResults.length > 0 && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-outline-variant rounded-xl shadow-xl z-30 max-h-48 overflow-y-auto">
                    {simDestResults.map((loc, i) => (
                      <div
                        key={i}
                        onClick={() => {
                          setIsCustomRoute(true);
                          setSimDestCoords({ lat: loc.latitude, lon: loc.longitude, name: loc.name });
                          setSimDestQuery(loc.name);
                          setSimDestResults([]);
                        }}
                        className="px-3 py-2 hover:bg-emerald-50 cursor-pointer border-b border-outline-variant/30 text-xs"
                      >
                        <div className="font-bold text-slate-800">{loc.name}</div>
                        <div className="text-[10px] text-slate-500 truncate">{loc.display_name}</div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="text-[10px] text-slate-500 font-mono mt-1">
                  GPS: {simDestCoords.lat.toFixed(4)}° N, {simDestCoords.lon.toFixed(4)}° E
                </div>
              </div>

              {/* Action Buttons */}
              <div className="md:col-span-2 flex flex-col gap-2 pt-5">
                <button
                  onClick={() => triggerRoutePreview(simOriginCoords, simDestCoords)}
                  disabled={previewingRoute}
                  className="w-full bg-slate-800 hover:bg-slate-900 disabled:opacity-50 text-white text-xs font-bold py-2.5 px-3 rounded-xl shadow-sm flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">navigation</span>
                  {previewingRoute ? "Routing..." : "Preview Route"}
                </button>
                <button
                  onClick={handleCreateSimulationSession}
                  disabled={simActionLoading}
                  className="w-full bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white text-xs font-bold py-2.5 px-3 rounded-xl shadow-sm flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">play_circle</span>
                  Init Session
                </button>
              </div>
            </div>

            {/* Route Summary Pill */}
            {routePreviewData && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-bold text-blue-900">🛣️ Highway Route Calculated:</span>
                  <span className="font-mono font-bold text-blue-800 bg-blue-100 px-2 py-0.5 rounded">
                    {routePreviewData.distance_km} km
                  </span>
                  <span className="text-slate-600">
                    Est. Duration: <strong>{(routePreviewData.duration_s / 3600).toFixed(1)} hrs</strong>
                  </span>
                  <span className="text-slate-500 font-mono text-[11px]">
                    ({routePreviewData.waypoint_count} road vertices • {routePreviewData.routing_source})
                  </span>
                </div>
                <div className="text-[11px] text-blue-900 font-medium">
                  {routePreviewData.origin.name} &rarr; {routePreviewData.destination.name}
                </div>
              </div>
            )}

            {/* Simulation Ready Deck (When route is ready but simulation not yet started) */}
            {!activeSimulation && (routePreviewData || selectedRoute) && (
              <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center">
                    <span className="material-symbols-outlined text-2xl">route</span>
                  </div>
                  <div>
                    <h5 className="font-bold text-slate-800 text-sm">Simulation Ready: Route Verified</h5>
                    <p className="text-xs text-slate-600 mt-0.5">
                      Verified Highway Distance: <strong className="text-emerald-900 font-mono">{(routePreviewData?.distance_km || selectedRoute?.distance_km || 0).toFixed(1)} km</strong> • Progress: <span className="font-mono font-semibold">0.0 km (0.0%)</span>
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                  <button
                    onClick={() => handleCreateSimulationSession(true)}
                    disabled={simActionLoading}
                    className="bg-emerald-700 hover:bg-emerald-800 text-white px-5 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition-colors w-full md:w-auto"
                  >
                    <span className="material-symbols-outlined text-base">play_arrow</span>
                    {simActionLoading ? "Starting Simulation..." : "Run Simulation Along Route"}
                  </button>
                </div>
              </div>
            )}

            {/* Simulation Control Deck & HUD (Active Session) */}
            {activeSimulation && (
              <div className="bg-white rounded-xl p-4 border border-outline-variant/60 shadow-sm flex flex-col gap-4">
                {/* Control Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/30 pb-3">
                  {/* Playback Controls */}
                  <div className="flex items-center gap-2">
                    {activeSimulation.status === "RUNNING" ? (
                      <button
                        onClick={() => handleControlAction("pause")}
                        disabled={simActionLoading}
                        className="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors"
                      >
                        <span className="material-symbols-outlined text-base">pause</span> Pause
                      </button>
                    ) : (
                      <button
                        onClick={() => handleControlAction("start")}
                        disabled={simActionLoading}
                        className="bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors"
                      >
                        <span className="material-symbols-outlined text-base">play_arrow</span> Run Simulation
                      </button>
                    )}

                    <button
                      onClick={() => handleControlAction("step", 15.0)}
                      disabled={simActionLoading || activeSimulation.status === "RUNNING"}
                      className="bg-slate-100 hover:bg-slate-200 text-slate-800 px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 border border-outline-variant/50 transition-colors"
                      title="Advance vehicle by discrete step (+15 km)"
                    >
                      <span className="material-symbols-outlined text-base">step_forward</span> Step (+15 km)
                    </button>

                    <button
                      onClick={() => handleControlAction("reset")}
                      disabled={simActionLoading}
                      className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-xl text-xs font-bold flex items-center gap-1 border border-outline-variant/50 transition-colors"
                      title="Reset vehicle back to origin"
                    >
                      <span className="material-symbols-outlined text-base">restart_alt</span> Reset
                    </button>

                    <button
                      onClick={() => handleControlAction("stop")}
                      disabled={simActionLoading}
                      className="bg-rose-50 hover:bg-rose-100 text-rose-700 px-3 py-2 rounded-xl text-xs font-bold flex items-center gap-1 border border-rose-200 transition-colors"
                    >
                      <span className="material-symbols-outlined text-base">stop</span> Stop
                    </button>
                  </div>

                  {/* Speed Multiplier */}
                  <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs border border-outline-variant/40">
                    <span className="text-[10px] font-bold text-slate-500 uppercase px-1.5">Speed:</span>
                    {[1.0, 2.0, 5.0, 10.0].map((m) => (
                      <button
                        key={m}
                        onClick={() => handleUpdateControls(m, simScenario)}
                        className={`px-2 py-0.5 rounded-lg font-bold font-mono transition-colors ${
                          activeSimulation.speed_multiplier === m
                            ? "bg-slate-800 text-white"
                            : "text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {m}x
                      </button>
                    ))}
                  </div>

                  {/* Cold-Chain Scenario Selector */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">Scenario:</span>
                    <select
                      value={activeSimulation.scenario || simScenario}
                      onChange={(e) => handleUpdateControls(activeSimulation.speed_multiplier || simSpeedMultiplier, e.target.value)}
                      className="bg-slate-50 border border-outline-variant/60 rounded-xl px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:border-emerald-600"
                    >
                      <option value="normal">Normal (4–7°C, Safe)</option>
                      <option value="temperature_excursion">Temp Excursion (&gt;8°C Reefer Alert)</option>
                      <option value="delay">Highway Traffic Jam (Speed 0, Delay)</option>
                      <option value="high_humidity">High Humidity (&gt;95% Condensation)</option>
                    </select>
                  </div>
                </div>

                {/* Traversal Progress Bar */}
                <div>
                  <div className="flex justify-between items-center text-xs mb-1 font-semibold">
                    <span className="text-slate-700">
                      🛣️ Road Distance Travelled: <strong>{activeSimulation.current_distance_km.toFixed(1)} km</strong> of {activeSimulation.total_distance_km.toFixed(1)} km
                    </span>
                    <span className="font-mono text-emerald-800 font-bold">
                      {((activeSimulation.current_distance_km / (activeSimulation.total_distance_km || 1)) * 100).toFixed(1)}% Completed
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-emerald-600 to-teal-500 transition-all duration-300"
                      style={{
                        width: `${Math.min(100, (activeSimulation.current_distance_km / (activeSimulation.total_distance_km || 1)) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Live Telemetry Gauges HUD */}
                {(() => {
                  const tel = activeSimulation.latest_telemetry || {};
                  const temp = tel.temperature_c ?? 5.5;
                  const hum = tel.humidity_pct ?? 87.0;
                  const speed = activeSimulation.current_speed_kmh ?? 50.0;
                  const heading = activeSimulation.current_heading_deg ?? 0.0;
                  const delay = tel.delay_minutes ?? 0;
                  const risk = tel.predicted_arrival_risk ?? 11.2;
                  const alertActive = tel.alert || risk > 50.0 || temp > 8.0;

                  return (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-1">
                      {/* Gauge 1: Temperature */}
                      <div className={`p-3 rounded-xl border flex flex-col justify-between ${
                        temp > 8.0 ? "bg-rose-50 border-rose-300 text-rose-950" : "bg-emerald-50/70 border-emerald-200 text-emerald-950"
                      }`}>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Reefer Temp</span>
                        <div className="flex items-baseline gap-1 mt-1">
                          <span className="text-2xl font-mono font-extrabold">{temp.toFixed(1)}</span>
                          <span className="text-xs font-bold">°C</span>
                        </div>
                        <span className="text-[10px] font-semibold mt-1">
                          {temp > 8.0 ? "⚠️ Excursion Alert" : "✅ Cold Window (4-8°C)"}
                        </span>
                      </div>

                      {/* Gauge 2: Relative Humidity */}
                      <div className={`p-3 rounded-xl border flex flex-col justify-between ${
                        hum > 95.0 ? "bg-amber-50 border-amber-300 text-amber-950" : "bg-sky-50/70 border-sky-200 text-sky-950"
                      }`}>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Relative Humidity</span>
                        <div className="flex items-baseline gap-1 mt-1">
                          <span className="text-2xl font-mono font-extrabold">{hum.toFixed(1)}</span>
                          <span className="text-xs font-bold">% RH</span>
                        </div>
                        <span className="text-[10px] font-semibold mt-1">
                          {hum > 95.0 ? "⚠️ Condensation Risk" : "✅ Nominal Range"}
                        </span>
                      </div>

                      {/* Gauge 3: Ground Speed & Bearing */}
                      <div className="p-3 rounded-xl border bg-slate-50 border-slate-200 text-slate-900 flex flex-col justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Speed &amp; Heading</span>
                        <div className="flex items-baseline gap-2 mt-1">
                          <span className="text-2xl font-mono font-extrabold">{speed.toFixed(0)}</span>
                          <span className="text-xs font-bold text-slate-500">km/h</span>
                          <span className="text-xs font-mono text-slate-600 ml-auto">{heading.toFixed(0)}°</span>
                        </div>
                        <span className="text-[10px] text-slate-500 font-semibold mt-1">
                          Delay: {delay} mins
                        </span>
                      </div>

                      {/* Gauge 4: Cold-Chain Risk Estimator */}
                      <div className={`p-3 rounded-xl border flex flex-col justify-between ${
                        alertActive ? "bg-rose-100 border-rose-400 text-rose-950 animate-pulse" : "bg-teal-50 border-teal-200 text-teal-950"
                      }`}>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Transit Risk (Rule-Based)</span>
                        <div className="flex items-baseline gap-1 mt-1">
                          <span className="text-2xl font-mono font-extrabold">{risk.toFixed(1)}</span>
                          <span className="text-xs font-bold">%</span>
                        </div>
                        <span className="text-[10px] font-bold mt-1">
                          {alertActive ? "🚨 CRITICAL SPOILAGE RISK" : "🛡️ Cold Chain Protected"}
                        </span>
                      </div>
                    </div>
                  );
                })()}

                {/* Attribution & Provenance Watermark */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 text-[10px] text-slate-500 border-t border-outline-variant/30 font-mono">
                  <span>Hardware Transponder ID: <strong>SNS-SIM-DEMO</strong></span>
                  <span>Data Provenance: <strong>data_source: simulation</strong></span>
                  <span>Current Fix: {activeSimulation.current_lat.toFixed(4)}° N, {activeSimulation.current_lon.toFixed(4)}° E</span>
                  <span>Step #{activeSimulation.step_count}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      <div className="bg-white rounded-2xl p-5 sm:p-6 border border-outline-variant/60 premium-shadow flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <div>
            <h4 className="font-bold text-emerald-forest text-sm uppercase tracking-wide flex items-center gap-2">
              <span className="material-symbols-outlined text-digital-mint text-base">pin_drop</span>
              Active Transit Corridors Map
            </h4>
            <p className="text-[11px] text-on-surface-variant mt-0.5">
              Visualizes PostGIS coordinates (WGS84 EPSG:4326), godowns &amp; cold stores, and verified transit routes across Punjab &amp; North India.
            </p>
          </div>
          <div className="flex items-center gap-2 self-end sm:self-auto">
            {selectedShipment && (
              <span className="text-xs font-mono font-bold text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                Selected: #{selectedShipment.id}
              </span>
            )}
            <button
              onClick={() => setMapExpanded(true)}
              className="border border-outline-variant/60 hover:bg-surface-container-high text-primary px-3 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors"
              title="Expand map to full viewport modal"
            >
              <span className="material-symbols-outlined text-sm">fullscreen</span>
              Expand Map
            </button>
          </div>
        </div>

        {/* Fullscreen Backdrop when expanded */}
        {mapExpanded && (
          <div
            className="fixed inset-0 z-40 bg-black/75 backdrop-blur-sm animate-fade-in"
            onClick={() => setMapExpanded(false)}
          />
        )}

        {/* Map Container: responsive inline layout when normal; fixed viewport modal when expanded */}
        <div
          className={`w-full rounded-2xl overflow-hidden border border-outline-variant/40 transition-all duration-300 ${
            mapExpanded
              ? "fixed inset-3 md:inset-6 z-50 bg-white shadow-2xl flex flex-col max-w-7xl mx-auto my-auto h-[calc(100vh-2rem)] md:h-[calc(100vh-3rem)]"
              : "h-[520px] sm:h-[580px] md:h-[650px] lg:h-[720px] relative isolate z-0"
          }`}
        >
          {mapExpanded && (
            <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant/60 bg-surface shrink-0">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-digital-mint text-xl">pin_drop</span>
                <div>
                  <h3 className="text-sm font-bold text-emerald-forest uppercase tracking-wide">
                    Active Transit Corridors Map (Expanded View)
                  </h3>
                  <p className="text-[11px] text-on-surface-variant">
                    PostGIS EPSG:4326 corridor tracking • Press Esc or click Exit Fullscreen
                  </p>
                </div>
              </div>
              <button
                onClick={() => setMapExpanded(false)}
                className="px-3.5 py-2 rounded-xl bg-surface-container-high hover:bg-surface-container-highest text-primary font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-colors border border-outline-variant/60"
              >
                <span className="material-symbols-outlined text-sm">close_fullscreen</span>
                Exit Fullscreen
              </button>
            </div>
          )}
          <div className="flex-1 w-full h-full min-h-0 relative isolate z-0 overflow-hidden">
            <TrackingMapClient
              className="w-full h-full"
              shipments={shipments}
              selectedShipment={selectedShipment}
              selectedRoute={selectedRoute}
              loadingRoute={loadingRoute}
              waypoints={waypoints}
              facilities={facilities}
              simulationSession={activeSimulation}
              simulationRoute={simulationRoute}
              mapPickMode={mapPickTarget}
              onMapPick={handleMapPick}
              onSelectShipment={(shp) => setSelectedShipment(shp)}
            />
          </div>
        </div>
      </div>

      {/* Main Grid: Shipments List (Left) + Selected Shipment & Telemetry (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* SECTION 3: REGISTERED BATCHES LIST (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl p-5 sm:p-6 border border-outline-variant/60 premium-shadow flex flex-col gap-3.5">
          <div className="flex justify-between items-center pb-2 border-b border-outline-variant/40">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-bold tracking-wider text-outline">Registered Batches</span>
              <span className="text-xs font-bold bg-surface-container-high text-primary px-2 py-0.5 rounded-full">
                {filteredShipments.length} of {shipments.length}
              </span>
            </div>
            <span className="text-[10px] text-on-surface-variant">Tap batch to track</span>
          </div>

          {/* Search Input & Filter Pills */}
          <div className="flex flex-col gap-2">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-2.5 text-outline text-sm">search</span>
              <input
                type="text"
                placeholder="Search ID, fruit, origin, destination..."
                value={shipmentSearch}
                onChange={(e) => setShipmentSearch(e.target.value)}
                className="w-full bg-surface-container-low/50 border border-outline-variant/60 rounded-xl pl-9 pr-8 py-2 text-xs focus:outline-none focus:border-digital-mint text-primary"
              />
              {shipmentSearch && (
                <button
                  onClick={() => setShipmentSearch("")}
                  className="absolute right-2.5 top-2.5 text-outline hover:text-primary"
                >
                  <span className="material-symbols-outlined text-xs">close</span>
                </button>
              )}
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[10px] scrollbar-thin">
              {[
                { id: "all", label: "All" },
                { id: "in_transit", label: "In Transit" },
                { id: "pending", label: "Pending" },
                { id: "delivered", label: "Delivered" },
              ].map((flt) => (
                <button
                  key={flt.id}
                  onClick={() => setShipmentStatusFilter(flt.id)}
                  className={`px-2.5 py-1 rounded-lg font-bold uppercase tracking-wider shrink-0 transition-colors ${
                    shipmentStatusFilter === flt.id
                      ? "bg-emerald-forest text-white"
                      : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                >
                  {flt.label}
                </button>
              ))}
            </div>
          </div>

          {loadingShipments ? (
            <div className="py-12 flex flex-col items-center justify-center text-outline gap-2">
              <div className="w-8 h-8 rounded-full border-2 border-digital-mint border-t-transparent animate-spin" />
              <span className="text-xs">Loading shipments...</span>
            </div>
          ) : shipments.length === 0 ? (
            <div className="py-12 text-center text-outline flex flex-col items-center justify-center gap-3">
              <span className="material-symbols-outlined text-4xl text-outline/60">inbox</span>
              <p className="text-xs">No shipments found in ledger.</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="text-xs font-bold text-digital-mint hover:underline"
              >
                + Register First Shipment
              </button>
            </div>
          ) : filteredShipments.length === 0 ? (
            <div className="py-10 text-center text-outline flex flex-col items-center justify-center gap-2">
              <span className="material-symbols-outlined text-3xl text-outline/50">search_off</span>
              <p className="text-xs">No batches match search criteria.</p>
              <button
                onClick={() => {
                  setShipmentSearch("");
                  setShipmentStatusFilter("all");
                }}
                className="text-xs font-bold text-digital-mint hover:underline"
              >
                Reset filters
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2.5 max-h-[660px] overflow-y-auto pr-1 scrollbar-thin">
              {filteredShipments.map((s) => {
                const isSelected = selectedShipment?.id === s.id;
                const coords = normalizeShipmentCoordinates(s);
                return (
                  <div
                    key={s.id}
                    onClick={() => setSelectedShipment(s)}
                    className={`p-4 rounded-xl border text-left cursor-pointer transition-all ${
                      isSelected
                        ? "border-digital-mint bg-digital-mint/5 shadow-sm ring-1 ring-digital-mint"
                        : "border-outline-variant/50 hover:bg-surface-container-low hover:border-outline-variant"
                    }`}
                  >
                    <div className="flex justify-between items-start gap-2 mb-2">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-xs text-primary font-mono">#{s.id}</span>
                        <span className="font-semibold text-xs text-emerald-forest">{s.produce_type || "Produce"}</span>
                      </div>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${getStatusBadge(s.status)}`}>
                        {s.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-on-surface-variant mb-2">
                      <span className="truncate max-w-[130px]">{s.origin || "Origin"}</span>
                      <span className="material-symbols-outlined text-xs text-outline shrink-0">arrow_forward</span>
                      <span className="truncate max-w-[130px] font-semibold text-primary">{s.destination || "Destination"}</span>
                    </div>

                    <div className="flex flex-wrap justify-between items-center text-[10px] text-outline pt-2 border-t border-outline-variant/30 gap-1.5">
                      <div className="flex items-center gap-1.5">
                        <span>{s.quantity} kg</span>
                        <span className="text-slate-300">•</span>
                        {coords ? (
                          <span className="bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.5 rounded font-mono font-medium flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 inline-block" />
                            GPS: {coords[0].toFixed(2)}°, {coords[1].toFixed(2)}°
                          </span>
                        ) : (
                          <span className="bg-slate-100 text-slate-500 border border-slate-200 px-1.5 py-0.5 rounded">
                            GPS Pending
                          </span>
                        )}
                      </div>

                      <span className={`font-mono font-bold ${
                        (s.risk_index ?? 0) > 40 ? "text-rose-600" : "text-emerald-700"
                      }`}>
                        Risk: {s.risk_index ?? 0}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Shipment Detail, Risk & Telemetry (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {selectedShipment ? (
            <>
              {/* Selected Shipment Summary Card */}
              {/* Phase 13 Tracking & Telemetry Transparency Header */}
              {(() => {
                const trkInfo = getTrackingModeInfo(selectedShipment, waypoints);
                const telInfo = getTelemetryModeInfo(selectedShipment, telemetry);
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Tracking Mode Card */}
                    <div className="p-4 bg-white rounded-2xl border border-outline-variant/60 premium-shadow flex items-start gap-3">
                      <div className="p-2.5 rounded-xl bg-surface-container-high text-primary shrink-0">
                        <span className="material-symbols-outlined text-xl">{trkInfo.icon}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${trkInfo.badgeClass} flex items-center gap-1`}>
                            {trkInfo.pulse && <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping inline-block" />}
                            {trkInfo.label}
                          </span>
                          {selectedShipment.current_coordinates?.timestamp && (
                            <span className="text-[10px] font-mono text-outline">
                              Fix: {new Date(selectedShipment.current_coordinates.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-on-surface-variant leading-relaxed">
                          {trkInfo.subtext}
                        </p>
                      </div>
                    </div>

                    {/* Telemetry Mode Card */}
                    <div className="p-4 bg-white rounded-2xl border border-outline-variant/60 premium-shadow flex items-start gap-3">
                      <div className="p-2.5 rounded-xl bg-surface-container-high text-primary shrink-0">
                        <span className="material-symbols-outlined text-xl">{telInfo.icon}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${telInfo.badgeClass}`}>
                            {telInfo.label}
                          </span>
                          <span className="text-[10px] font-mono text-outline">
                            {telemetry.length} reading{telemetry.length === 1 ? "" : "s"}
                          </span>
                        </div>
                        <p className="text-[11px] text-on-surface-variant leading-relaxed">
                          {telInfo.subtext}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Selected Shipment Summary Card */}
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-outline-variant/40">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-primary">Shipment #{selectedShipment.id}</span>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${getStatusBadge(selectedShipment.status)}`}>
                        {selectedShipment.status}
                      </span>
                    </div>
                    <h4 className="text-base font-bold text-emerald-forest mt-1">
                      {selectedShipment.produce_type} — {selectedShipment.quantity} kg ({selectedShipment.quantity_crates || 0} crates)
                    </h4>
                    {/* Dynamic Real-Road Route & Calculated Distance Badge */}
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {loadingRoute ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          <span className="w-3 h-3 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
                          Calculating Road Route...
                        </span>
                      ) : selectedRoute && selectedRoute.shipment_id === selectedShipment.id ? (
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold bg-blue-50 text-blue-900 border border-blue-200 shadow-sm">
                          <span className="material-symbols-outlined text-sm text-blue-600">alt_route</span>
                          <span>Road Route: <strong className="font-mono text-blue-950 font-bold">{selectedRoute.distance_km} km</strong></span>
                          <span className="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-mono uppercase font-semibold">
                            {selectedRoute.routing_source}
                          </span>
                          <span className="text-[10px] text-slate-500 font-normal">
                            ({selectedRoute.waypoint_count} pts)
                          </span>
                        </div>
                      ) : routeError ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          <span className="material-symbols-outlined text-sm">warning</span>
                          Route Error: {routeError}
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <button
                      onClick={handleSimulateStep}
                      disabled={simulatingStep}
                      className="border border-amber-500/60 bg-amber-50 text-amber-900 hover:bg-amber-100 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors disabled:opacity-50"
                      title="Advance transit corridor by one simulated step [DEMO / SIMULATION ONLY]"
                    >
                      <span className="material-symbols-outlined text-sm">fast_forward</span>
                      {simulatingStep ? "Simulating..." : "Simulate Step [DEMO]"}
                    </button>

                    <button
                      onClick={() => setShowAddWaypoint(true)}
                      className="border border-digital-mint text-emerald-forest hover:bg-digital-mint/10 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors"
                      title="Record GPS Waypoint"
                    >
                      <span className="material-symbols-outlined text-sm">add_location_alt</span>
                      Add GPS
                    </button>

                    <button
                      onClick={() => setShowAddTelemetry(true)}
                      className="bg-digital-mint hover:bg-emerald-forest text-white px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-sm transition-colors"
                    >
                      <span className="material-symbols-outlined text-sm">add_chart</span>
                      Log Reading
                    </button>
                  </div>
                </div>

                {simulateNotice && (
                  <div
                    className={`p-3 rounded-xl text-xs flex items-center justify-between border ${
                      simulateNotice.type === "success"
                        ? "bg-amber-50 border-amber-300 text-amber-900"
                        : "bg-error/10 border-error/20 text-error"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-sm">
                        {simulateNotice.type === "success" ? "science" : "error"}
                      </span>
                      <span>{simulateNotice.message}</span>
                    </div>
                    <button
                      onClick={() => setSimulateNotice(null)}
                      className="text-outline hover:text-primary"
                    >
                      <span className="material-symbols-outlined text-sm">close</span>
                    </button>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-surface-container-low/60 rounded-xl border border-outline-variant/30">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-outline block">Planned Departure</span>
                    <span className="font-semibold text-primary block mt-0.5 font-mono text-[11px]">
                      {selectedShipment.planned_departure
                        ? new Date(selectedShipment.planned_departure).toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                        : "Immediate"}
                    </span>
                  </div>
                  <div className="p-3 bg-surface-container-low/60 rounded-xl border border-outline-variant/30">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-outline block">Planned Arrival</span>
                    <span className="font-semibold text-primary block mt-0.5 font-mono text-[11px]">
                      {selectedShipment.planned_arrival
                        ? new Date(selectedShipment.planned_arrival).toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                        : "Target TBD"}
                    </span>
                  </div>
                  <div className="p-3 bg-surface-container-low/60 rounded-xl border border-outline-variant/30">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-outline block">Latest Coordinates</span>
                    <span className="font-mono font-semibold text-primary truncate block mt-0.5">
                      {selectedShipment.current_coordinates
                        ? `${selectedShipment.current_coordinates.latitude.toFixed(4)}°, ${selectedShipment.current_coordinates.longitude.toFixed(4)}°`
                        : "No GPS Fix"}
                    </span>
                  </div>
                  <div className="p-3 bg-surface-container-low/60 rounded-xl border border-outline-variant/30">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-outline block">Road Distance</span>
                    <div className="flex items-center justify-between mt-0.5">
                      <span className="font-mono font-bold text-blue-700 text-[13px]">
                        {selectedRoute?.distance_km != null ? `${selectedRoute.distance_km} km` : loadingRoute ? "..." : "TBD"}
                      </span>
                      <span className="font-mono text-outline text-[11px]">
                        {waypoints.length} waypoints
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Phase 13: CONNECTED AGRICULTURAL FACILITIES & PROVENANCE AUDIT */}
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow flex flex-col gap-4">
                <div className="flex justify-between items-center pb-2 border-b border-outline-variant/40">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-digital-mint">hub</span>
                    <div>
                      <h4 className="font-bold text-emerald-forest text-sm uppercase tracking-wide">
                        Connected Guava Facilities &amp; Provenance
                      </h4>
                      <p className="text-[11px] text-on-surface-variant">
                        Multi-hub supply chain routing with verified trading, handling, and cold-chain readiness.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                  {/* Origin Facility Card */}
                  <div className="p-4 rounded-xl border border-emerald-200/80 bg-emerald-50/20 flex flex-col justify-between gap-3">
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                          Origin Facility
                        </span>
                        <span className="text-[10px] font-mono text-outline font-semibold">
                          Op: {selectedShipment.origin_operation?.replace('_', ' ') || "packhouse cooling"}
                        </span>
                      </div>

                      {selectedShipment.origin_facility ? (
                        <>
                          <h5 className="font-bold text-xs text-primary leading-tight">
                            {selectedShipment.origin_facility.name}
                          </h5>
                          <span className="text-[10px] text-on-surface-variant font-medium block mt-0.5">
                            {selectedShipment.origin_facility.district}, {selectedShipment.origin_facility.state} • {selectedShipment.origin_facility.facility_type.replace('_', ' ')}
                          </span>

                          <div className="flex flex-wrap gap-1 mt-2.5">
                            {renderCapabilityChip("Trading", selectedShipment.origin_facility.guava_trading_status)}
                            {renderCapabilityChip("Handling", selectedShipment.origin_facility.guava_handling_status)}
                            {renderCapabilityChip("Cold Chain", selectedShipment.origin_facility.guava_cold_chain_status)}
                            {renderCapabilityChip("Status", selectedShipment.origin_facility.operational_status || "unknown")}
                          </div>

                          <div className="mt-3 pt-2 border-t border-emerald-100 text-[10px] flex flex-col gap-1">
                            <span className="text-slate-600 flex items-center gap-1">
                              <span className="material-symbols-outlined text-xs">
                                {selectedShipment.origin_facility.approximate_coordinates ? "near_me" : "place"}
                              </span>
                              {selectedShipment.origin_facility.approximate_coordinates
                                ? "Approximate village centroid"
                                : "Verified facility coordinates"}
                            </span>
                            {selectedShipment.origin_facility.source_url && (
                              <a
                                href={selectedShipment.origin_facility.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-emerald-700 hover:underline flex items-center gap-1 font-semibold"
                              >
                                <span>Source Provenance (Tier {selectedShipment.origin_facility.citation_tier || 2})</span>
                                <span className="material-symbols-outlined text-[11px]">open_in_new</span>
                              </a>
                            )}
                          </div>
                        </>
                      ) : (
                        <div className="text-xs text-on-surface-variant">
                          <strong className="text-primary block">{selectedShipment.origin || "Not linked"}</strong>
                          <span className="text-[10px] text-outline">Custom origin landmark (no directory facility bound)</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Intermediate Transit Hub Card */}
                  <div className={`p-4 rounded-xl border flex flex-col justify-between gap-3 ${
                    selectedShipment.intermediate_facility
                      ? "border-purple-200/80 bg-purple-50/20"
                      : "border-outline-variant/40 bg-surface-container-low/40"
                  }`}>
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-300">
                          Intermediate Hub
                        </span>
                        <span className="text-[10px] font-mono text-outline font-semibold">
                          Op: {selectedShipment.intermediate_operation?.replace('_', ' ') || "direct transit"}
                        </span>
                      </div>

                      {selectedShipment.intermediate_facility ? (
                        <>
                          <h5 className="font-bold text-xs text-primary leading-tight">
                            {selectedShipment.intermediate_facility.name}
                          </h5>
                          <span className="text-[10px] text-on-surface-variant font-medium block mt-0.5">
                            {selectedShipment.intermediate_facility.district}, {selectedShipment.intermediate_facility.state} • {selectedShipment.intermediate_facility.facility_type.replace('_', ' ')}
                          </span>

                          <div className="flex flex-wrap gap-1 mt-2.5">
                            {renderCapabilityChip("Trading", selectedShipment.intermediate_facility.guava_trading_status)}
                            {renderCapabilityChip("Handling", selectedShipment.intermediate_facility.guava_handling_status)}
                            {renderCapabilityChip("Cold Chain", selectedShipment.intermediate_facility.guava_cold_chain_status)}
                            {renderCapabilityChip("Status", selectedShipment.intermediate_facility.operational_status || "unknown")}
                          </div>

                          <div className="mt-3 pt-2 border-t border-purple-100 text-[10px] flex flex-col gap-1">
                            <span className="text-slate-600 flex items-center gap-1">
                              <span className="material-symbols-outlined text-xs">
                                {selectedShipment.intermediate_facility.approximate_coordinates ? "near_me" : "place"}
                              </span>
                              {selectedShipment.intermediate_facility.approximate_coordinates
                                ? "Approximate centroid"
                                : "Verified hub coordinates"}
                            </span>
                            {selectedShipment.intermediate_facility.source_url && (
                              <a
                                href={selectedShipment.intermediate_facility.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-purple-700 hover:underline flex items-center gap-1 font-semibold"
                              >
                                <span>Source Provenance (Tier {selectedShipment.intermediate_facility.citation_tier || 2})</span>
                                <span className="material-symbols-outlined text-[11px]">open_in_new</span>
                              </a>
                            )}
                          </div>
                        </>
                      ) : (
                        <div className="text-xs text-on-surface-variant flex flex-col items-center justify-center py-6 text-center text-outline">
                          <span className="material-symbols-outlined text-2xl mb-1 text-outline/60">straighten</span>
                          <span className="font-semibold text-slate-600">Direct Transit Corridor</span>
                          <span className="text-[10px] text-outline mt-0.5">No intermediate packhouse or holding godown selected.</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Destination Facility Card */}
                  <div className="p-4 rounded-xl border border-sky-200/80 bg-sky-50/20 flex flex-col justify-between gap-3">
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-sky-100 text-sky-800 border border-sky-300">
                          Destination Facility
                        </span>
                        <span className="text-[10px] font-mono text-outline font-semibold">
                          Op: {selectedShipment.destination_operation?.replace('_', ' ') || "market auction"}
                        </span>
                      </div>

                      {selectedShipment.destination_facility ? (
                        <>
                          <h5 className="font-bold text-xs text-primary leading-tight">
                            {selectedShipment.destination_facility.name}
                          </h5>
                          <span className="text-[10px] text-on-surface-variant font-medium block mt-0.5">
                            {selectedShipment.destination_facility.district}, {selectedShipment.destination_facility.state} • {selectedShipment.destination_facility.facility_type.replace('_', ' ')}
                          </span>

                          <div className="flex flex-wrap gap-1 mt-2.5">
                            {renderCapabilityChip("Trading", selectedShipment.destination_facility.guava_trading_status)}
                            {renderCapabilityChip("Handling", selectedShipment.destination_facility.guava_handling_status)}
                            {renderCapabilityChip("Cold Chain", selectedShipment.destination_facility.guava_cold_chain_status)}
                            {renderCapabilityChip("Status", selectedShipment.destination_facility.operational_status || "unknown")}
                          </div>

                          <div className="mt-3 pt-2 border-t border-sky-100 text-[10px] flex flex-col gap-1">
                            <span className="text-slate-600 flex items-center gap-1">
                              <span className="material-symbols-outlined text-xs">
                                {selectedShipment.destination_facility.approximate_coordinates ? "near_me" : "place"}
                              </span>
                              {selectedShipment.destination_facility.approximate_coordinates
                                ? "Approximate terminal centroid"
                                : "Verified terminal coordinates"}
                            </span>
                            {selectedShipment.destination_facility.source_url && (
                              <a
                                href={selectedShipment.destination_facility.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-sky-700 hover:underline flex items-center gap-1 font-semibold"
                              >
                                <span>Source Provenance (Tier {selectedShipment.destination_facility.citation_tier || 2})</span>
                                <span className="material-symbols-outlined text-[11px]">open_in_new</span>
                              </a>
                            )}
                          </div>
                        </>
                      ) : (
                        <div className="text-xs text-on-surface-variant">
                          <strong className="text-primary block">{selectedShipment.destination || "Not linked"}</strong>
                          <span className="text-[10px] text-outline">Custom destination address (no directory facility bound)</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Phase 13: SUITABILITY WARNINGS & CAVEATS */}
              {selectedShipment.suitability_warnings && selectedShipment.suitability_warnings.length > 0 && (
                <div className="p-4 bg-amber-50/80 border border-amber-300 rounded-2xl flex flex-col gap-2">
                  <div className="flex items-center gap-2 text-amber-900 font-bold text-xs uppercase tracking-wide">
                    <span className="material-symbols-outlined text-amber-700 text-base">warning</span>
                    <span>Guava Supply-Chain Suitability &amp; Availability Caveats</span>
                  </div>
                  <ul className="list-disc pl-5 text-[11px] text-amber-950/90 space-y-1">
                    {selectedShipment.suitability_warnings.map((w, idx) => (
                      <li key={idx} className="leading-relaxed">
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* COLD-CHAIN SPOILAGE RISK CARD */}
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow flex flex-col gap-4">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-amber-600">health_and_safety</span>
                    <h4 className="font-bold text-emerald-forest text-sm uppercase tracking-wide">
                      Cold-Chain Spoilage Risk Engine
                    </h4>
                  </div>

                  <button
                    onClick={handleRunLstm}
                    disabled={evaluatingLstm}
                    className="bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-bold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    <span className="material-symbols-outlined text-sm">psychology</span>
                    {evaluatingLstm ? "Evaluating..." : "Run 24h Risk Estimator"}
                  </button>
                </div>

                {loadingRisk ? (
                  <div className="py-4 text-center text-outline text-xs">
                    Evaluating sensor history against thermal thresholds...
                  </div>
                ) : riskInfo ? (
                  <div className={`p-4 rounded-xl border ${
                    riskInfo.alert ? "bg-rose-50 border-rose-200" : "bg-emerald-50/60 border-emerald-200"
                  }`}>
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <span className={`text-xs font-bold uppercase tracking-wider ${
                          riskInfo.alert ? "text-rose-700" : "text-emerald-800"
                        }`}>
                          {riskInfo.alert ? "⚠️ Thermal Excursion Alert" : "✅ Cold-Chain Stable"}
                        </span>
                        <p className="text-[11px] text-slate-600 mt-0.5">
                          Evaluated against 4.0°C – 8.0°C fresh produce transit window (Rule-based decision estimator).
                        </p>
                      </div>

                      <div className="text-right">
                        <span className="text-[10px] text-slate-500 uppercase font-semibold block">Predicted Arrival Risk</span>
                        <span className={`text-lg font-bold font-mono ${
                          riskInfo.alert ? "text-rose-700" : "text-emerald-800"
                        }`}>
                          {riskInfo.predicted_arrival_risk}%
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-4 gap-2 text-center text-[11px] pt-2 border-t border-slate-200/60">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Current Risk</span>
                        <strong className="font-mono text-slate-800">{riskInfo.current_risk}%</strong>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Avg Temp</span>
                        <strong className="font-mono text-slate-800">{riskInfo.avg_temperature_c}°C</strong>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Excursions</span>
                        <strong className={`font-mono ${riskInfo.excursion_events > 0 ? "text-rose-600" : "text-slate-800"}`}>
                          {riskInfo.excursion_events}
                        </strong>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Sensor Points</span>
                        <strong className="font-mono text-slate-800">{riskInfo.telemetry_points_evaluated}</strong>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-slate-50 rounded-xl text-center text-xs text-slate-500">
                    No risk score computed yet for this batch. Log telemetry to evaluate spoilage risk.
                  </div>
                )}

                {/* 24h Sequence Evaluation Result Notice */}
                {lstmResult && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs flex justify-between items-center">
                    <div>
                      <span className="font-bold text-amber-900">24h Risk Sequence (Rule-Based Heuristic):</span>
                      <span className="text-amber-800 ml-1.5">
                        Predicted arrival risk: <strong>{lstmResult.predicted_arrival_risk}%</strong> ({lstmResult.inference_ms} ms)
                      </span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      lstmResult.alert ? "bg-rose-600 text-white" : "bg-emerald-600 text-white"
                    }`}>
                      {lstmResult.alert ? "RISK HIGH" : "RISK LOW"}
                    </span>
                  </div>
                )}
                {lstmError && (
                  <div className="p-2 bg-rose-50 text-rose-700 text-xs rounded-lg border border-rose-200">
                    Risk Evaluation: {lstmError}
                  </div>
                )}
              </div>

              {/* LOCATION HISTORY & WAYPOINTS LIST */}
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow flex flex-col gap-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-bold text-emerald-forest text-sm uppercase tracking-wide flex items-center gap-2">
                      <span className="material-symbols-outlined text-digital-mint text-base">route</span>
                      PostGIS Waypoint History
                    </h4>
                    <p className="text-[11px] text-on-surface-variant mt-0.5">
                      GPS points stored in PostGIS table `geo_waypoints` (Point, 4326).
                    </p>
                  </div>
                  <button
                    onClick={() => setShowAddWaypoint(true)}
                    className="text-xs font-bold text-emerald-700 hover:text-emerald-900 flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-sm">add</span>
                    Record Waypoint
                  </button>
                </div>

                {loadingWaypoints ? (
                  <div className="py-4 text-center text-xs text-slate-500">Loading waypoints...</div>
                ) : waypoints.length === 0 ? (
                  <div className="p-4 bg-slate-50 rounded-xl text-center text-xs text-slate-500">
                    No GPS waypoints recorded for this shipment yet. Click &quot;Record Waypoint&quot; to log current coordinates.
                  </div>
                ) : (
                  <>
                    <div className="overflow-x-auto min-w-0 w-full scrollbar-thin">
                      <table className="w-full text-left text-xs border-collapse min-w-[520px]">
                        <thead className="sticky top-0 bg-white">
                          <tr className="border-b border-outline-variant/60 text-outline text-[10px] uppercase font-bold tracking-wider">
                            <th className="pb-2">Waypoint</th>
                            <th className="pb-2">Type</th>
                            <th className="pb-2">Coordinates (Lat, Lon)</th>
                            <th className="pb-2">Speed</th>
                            <th className="pb-2">Metadata</th>
                            <th className="pb-2">Time</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(showAllWaypoints ? [...waypoints].reverse() : [...waypoints].reverse().slice(0, 6)).map((w, idx) => {
                            const isSimulated = Boolean(
                              w.location_metadata?.simulated ||
                              w.location_metadata?.source === "demo_simulated" ||
                              w.location_metadata?.label?.includes("SIMULATED")
                            );
                            return (
                              <tr key={w.id || idx} className="border-b border-outline-variant/30 hover:bg-surface-container-low/40">
                                <td className="py-2 font-mono font-bold text-emerald-800">{w.id}</td>
                                <td className="py-2">
                                  {isSimulated ? (
                                    <span className="bg-amber-100 text-amber-800 border border-amber-300 text-[9px] uppercase font-bold px-1.5 py-0.5 rounded font-mono">
                                      DEMO
                                    </span>
                                  ) : (
                                    <span className="bg-emerald-100 text-emerald-800 border border-emerald-300 text-[9px] uppercase font-bold px-1.5 py-0.5 rounded font-mono">
                                      LIVE GPS
                                    </span>
                                  )}
                                </td>
                                <td className="py-2 font-mono text-slate-700">
                                  {w.latitude.toFixed(4)}°, {w.longitude.toFixed(4)}°
                                </td>
                                <td className="py-2 font-mono text-slate-700">
                                  {w.speed_kmh != null ? `${w.speed_kmh} km/h` : "—"}
                                </td>
                                <td className="py-2 text-slate-600 truncate max-w-[140px]">
                                  {w.location_metadata?.checkpoint || w.location_metadata?.hub || w.location_metadata?.corridor || "En route"}
                                </td>
                                <td className="py-2 text-slate-400 font-mono text-[10px]">
                                  {w.recorded_at ? new Date(w.recorded_at).toLocaleTimeString() : "—"}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    {waypoints.length > 6 && (
                      <div className="pt-2 border-t border-outline-variant/30 flex justify-center">
                        <button
                          type="button"
                          onClick={() => setShowAllWaypoints(!showAllWaypoints)}
                          className="text-xs font-semibold text-emerald-700 hover:text-emerald-900 flex items-center gap-1 transition-colors"
                        >
                          {showAllWaypoints ? "Show recent 6 waypoints" : `Show all ${waypoints.length} waypoints`}
                          <span className="material-symbols-outlined text-sm">{showAllWaypoints ? "expand_less" : "expand_more"}</span>
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Telemetry Visual Trend Visualizer / Chart */}
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h4 className="font-bold text-emerald-forest text-sm uppercase tracking-tight flex items-center gap-2">
                      <span className="material-symbols-outlined text-digital-mint text-base">insights</span>
                      Cold Chain Sensor Readings
                    </h4>
                    <p className="text-[10px] text-on-surface-variant mt-0.5">
                      {telemetry.length} data point{telemetry.length === 1 ? "" : "s"} recorded
                    </p>
                  </div>
                  {telemetry.length > 0 && (
                    <div className="flex items-center gap-4 text-[10px] font-mono">
                      <span className="flex items-center gap-1 text-sky-700 font-semibold">
                        <span className="w-2.5 h-2.5 rounded-full bg-sky-500 inline-block" /> Avg Temp: {avgTemp}°C
                      </span>
                      <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                        <span className="w-2.5 h-2.5 rounded-full bg-digital-mint inline-block" /> Avg Humid: {avgHumid}%
                      </span>
                    </div>
                  )}
                </div>

                {/* SVG Visual Chart */}
                {telemetry.length > 1 ? (
                  <div className="w-full bg-surface-container-low/40 rounded-xl p-4 border border-outline-variant/30">
                    <div className="h-44 w-full relative flex items-end">
                      <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20">
                        <div className="border-b border-outline" />
                        <div className="border-b border-outline" />
                        <div className="border-b border-outline" />
                      </div>

                      <div className="w-full h-full flex items-end justify-between gap-1.5 z-10 pt-4">
                        {telemetry.slice(-15).map((reading, idx) => {
                          const tempHeight = Math.min(100, Math.max(15, ((reading.temperature + 5) / 30) * 100));
                          const humidHeight = Math.min(100, Math.max(15, (reading.humidity / 100) * 100));
                          return (
                            <div key={reading.id || idx} className="flex-1 flex flex-col items-center gap-1 h-full justify-end group relative">
                              <div className="absolute -top-12 bg-primary text-white text-[9px] font-mono p-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-md whitespace-nowrap z-20">
                                Temp: {reading.temperature}°C | Hum: {reading.humidity}%
                                {reading.sensor_id && ` | ${reading.sensor_id}`}
                              </div>

                              <div className="w-full flex items-end justify-center gap-0.5 h-full">
                                <div
                                  style={{ height: `${tempHeight}%` }}
                                  className={`w-1/2 rounded-t transition-all ${
                                    reading.temperature > 8.0
                                      ? "bg-rose-500"
                                      : reading.temperature < 4.0
                                      ? "bg-amber-500"
                                      : "bg-sky-500"
                                  }`}
                                  title={`Temp: ${reading.temperature}°C`}
                                />
                                <div
                                  style={{ height: `${humidHeight}%` }}
                                  className="w-1/2 bg-digital-mint/80 rounded-t transition-all"
                                  title={`Humidity: ${reading.humidity}%`}
                                />
                              </div>

                              <span className="text-[8px] text-outline font-mono truncate max-w-full">
                                #{idx + 1}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="flex flex-wrap justify-between items-center text-[10px] text-outline mt-3 pt-2 border-t border-outline-variant/30 gap-2">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="flex items-center gap-1">
                          <span className="w-2 h-2 rounded bg-sky-500 inline-block" /> Temp (4–8°C Optimal)
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="w-2 h-2 rounded bg-amber-500 inline-block" /> Temp (&lt;4°C Chilling Hazard)
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="w-2 h-2 rounded bg-rose-500 inline-block" /> Temp (&gt;8°C Warm Excursion)
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="w-2 h-2 rounded bg-digital-mint inline-block" /> Humidity (%)
                        </span>
                      </div>
                      <span className="font-mono">Last {Math.min(15, telemetry.length)} logs shown</span>
                    </div>
                  </div>
                ) : telemetry.length === 1 ? (
                  <div className="p-4 bg-surface-container-low/40 rounded-xl border border-outline-variant/30 text-center">
                    <p className="text-xs text-on-surface-variant">
                      Single telemetry point logged: <strong className="font-mono">{telemetry[0].temperature}°C</strong> at <strong className="font-mono">{telemetry[0].humidity}%</strong> humidity.
                    </p>
                    <p className="text-[10px] text-outline mt-1">Log at least two readings to visualize trend lines.</p>
                  </div>
                ) : (
                  <div className="p-8 bg-surface-container-low/30 rounded-xl border border-dashed border-outline-variant/60 text-center">
                    <span className="material-symbols-outlined text-outline text-3xl mb-1">query_stats</span>
                    <p className="text-xs text-on-surface-variant font-semibold">No telemetry logged yet</p>
                    <p className="text-[10px] text-outline mt-0.5">Use &quot;Log Reading&quot; above to submit sensor data.</p>
                  </div>
                )}
              </div>

              {/* Telemetry History Table */}
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="font-bold text-emerald-forest text-sm uppercase tracking-tight">Telemetry Log History</h4>
                  <span className="text-[10px] font-mono text-outline">GET /api/shipments/{selectedShipment.id}/telemetry</span>
                </div>

                {loadingTelemetry ? (
                  <div className="py-8 flex flex-col items-center justify-center text-outline gap-2">
                    <div className="w-6 h-6 rounded-full border-2 border-digital-mint border-t-transparent animate-spin" />
                    <span className="text-xs">Loading telemetry records...</span>
                  </div>
                ) : telemetryError ? (
                  <div className="py-6 px-4 bg-error/10 border border-error/20 rounded-xl text-center flex flex-col items-center gap-2">
                    <span className="material-symbols-outlined text-error text-2xl">error</span>
                    <p className="text-xs text-error font-medium">{telemetryError}</p>
                  </div>
                ) : telemetry.length === 0 ? (
                  <div className="py-6 text-center text-outline text-xs">
                    No sensor readings recorded for this shipment.
                  </div>
                ) : (
                  <>
                    <div className="overflow-x-auto min-w-0 w-full scrollbar-thin">
                      <table className="w-full text-left text-xs border-collapse min-w-[500px]">
                        <thead className="sticky top-0 bg-white">
                          <tr className="border-b border-outline-variant/60 text-outline text-[10px] uppercase font-bold tracking-wider">
                            <th className="pb-2.5">Time / ID</th>
                            <th className="pb-2.5">Temperature</th>
                            <th className="pb-2.5">Humidity</th>
                            <th className="pb-2.5">Sensor ID</th>
                            <th className="pb-2.5">Location</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(showAllTelemetry ? [...telemetry].reverse() : [...telemetry].reverse().slice(0, 6)).map((t, idx) => (
                            <tr key={t.id || idx} className="border-b border-outline-variant/30 hover:bg-surface-container-low/40">
                              <td className="py-2.5 font-mono text-on-surface-variant">
                                {t.timestamp
                                  ? new Date(t.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
                                  : `#${t.id || idx + 1}`}
                              </td>
                              <td className="py-2.5">
                                <span className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${getTempBadge(t.temperature)}`}>
                                  {t.temperature}°C
                                </span>
                              </td>
                              <td className="py-2.5 font-mono font-semibold text-primary">
                                {t.humidity}%
                              </td>
                              <td className="py-2.5 font-mono text-on-surface-variant">
                                {t.sensor_id || "—"}
                              </td>
                              <td className="py-2.5 text-on-surface-variant">
                                {t.location || "In Transit"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {telemetry.length > 6 && (
                      <div className="pt-2 border-t border-outline-variant/30 flex justify-center">
                        <button
                          type="button"
                          onClick={() => setShowAllTelemetry(!showAllTelemetry)}
                          className="text-xs font-semibold text-emerald-700 hover:text-emerald-900 flex items-center gap-1 transition-colors"
                        >
                          {showAllTelemetry ? "Show recent 6 readings" : `Show all ${telemetry.length} readings`}
                          <span className="material-symbols-outlined text-sm">{showAllTelemetry ? "expand_less" : "expand_more"}</span>
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Phase 13: Auditable Shipment Custody & Event Timeline */}
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow flex flex-col gap-4">
                <div className="flex justify-between items-center pb-2 border-b border-outline-variant/40">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-digital-mint">timeline</span>
                    <div>
                      <h4 className="font-bold text-emerald-forest text-sm uppercase tracking-wide">
                        Shipment Custody &amp; Event Timeline
                      </h4>
                      <p className="text-[11px] text-on-surface-variant">
                        Chronological immutable audit log of status updates, handovers, and tracking events.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setShowAddEvent(true)}
                    className="bg-emerald-forest hover:bg-primary text-white text-xs font-bold px-3 py-1.5 rounded-xl uppercase tracking-wider flex items-center gap-1.5 shadow-sm transition-colors"
                  >
                    <span className="material-symbols-outlined text-sm">post_add</span>
                    Record Event
                  </button>
                </div>

                {loadingEvents ? (
                  <div className="py-8 flex flex-col items-center justify-center text-outline gap-2">
                    <div className="w-6 h-6 rounded-full border-2 border-digital-mint border-t-transparent animate-spin" />
                    <span className="text-xs">Loading custody events...</span>
                  </div>
                ) : events.length === 0 ? (
                  <div className="p-6 bg-slate-50 rounded-xl text-center text-xs text-slate-500">
                    No custody events recorded for this shipment yet. Click &quot;Record Event&quot; to log handover or status update.
                  </div>
                ) : (
                  <div className="relative pl-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-outline-variant/50 space-y-4 max-h-[360px] overflow-y-auto pr-2">
                    {events.map((ev) => {
                      const iconMeta = getEventIcon(ev.event_type);
                      const isSimulated = ev.source === "demo_simulated";
                      return (
                        <div key={ev.id} className="relative flex items-start gap-3 text-xs">
                          <span className={`absolute -left-[1.65rem] top-0.5 w-6 h-6 rounded-full border flex items-center justify-center bg-white ${iconMeta.color}`}>
                            <span className="material-symbols-outlined text-xs">{iconMeta.icon}</span>
                          </span>
                          <div className="flex-1 bg-surface-container-low/50 p-3 rounded-xl border border-outline-variant/40">
                            <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
                              <span className="font-bold text-primary font-mono capitalize">
                                {ev.event_type.replace(/_/g, " ")}
                              </span>
                              <div className="flex items-center gap-1.5">
                                <span className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded border ${
                                  isSimulated
                                    ? "bg-amber-100 text-amber-800 border-amber-300"
                                    : "bg-surface-container-high text-primary border-outline-variant/60"
                                }`}>
                                  {ev.source.replace(/_/g, " ")}
                                </span>
                                <span className="text-[10px] text-outline font-mono">
                                  {ev.timestamp ? new Date(ev.timestamp).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                                </span>
                              </div>
                            </div>
                            <p className="text-on-surface-variant text-[11px] leading-relaxed">
                              {ev.description}
                            </p>
                            {ev.facility_id && (
                              <div className="mt-1.5 text-[10px] text-emerald-800 font-mono font-semibold flex items-center gap-1">
                                <span className="material-symbols-outlined text-xs text-digital-mint">storefront</span>
                                Facility Ref: {ev.facility_id}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-white rounded-2xl p-12 border border-outline-variant/60 premium-shadow flex flex-col items-center justify-center text-center text-outline min-h-[400px]">
              <span className="material-symbols-outlined text-5xl text-outline/50 mb-3">pin_drop</span>
              <h4 className="font-bold text-sm text-primary">No Shipment Selected</h4>
              <p className="text-xs text-on-surface-variant max-w-sm mt-1">
                Choose a shipment batch from the left list or click a marker on the PostGIS map above to inspect route telemetry and spoilage risk.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Create Shipment */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 md:p-8 border border-outline-variant shadow-2xl relative">
            <button
              onClick={() => setShowCreateModal(false)}
              className="absolute top-5 right-5 text-outline hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>

            <h3 className="text-lg font-bold text-emerald-forest mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-digital-mint">add_circle</span>
              Register New Cold-Chain Shipment
            </h3>
            <p className="text-xs text-on-surface-variant mb-6">
              Create a produce shipment batch on the backend (`POST /api/shipments`).
            </p>

            {createError && (
              <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-xl text-xs text-error font-medium">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateShipment} className="flex flex-col gap-4 text-xs">
              <div>
                <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Produce Type</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Guava (Allahabad Safeda / Shweta)"
                  value={newShipment.produce_type}
                  onChange={(e) => setNewShipment({ ...newShipment, produce_type: e.target.value })}
                  className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                />
              </div>

              {/* Facility Selection & Operations Grid */}
              {facilities.length > 0 && (
                <div className="flex flex-col gap-3.5 bg-surface-container-low/40 p-3.5 rounded-xl border border-outline-variant/40">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Guava Supply-Chain Facilities &amp; Operations
                  </span>

                  {/* Origin Facility & Operation */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5">
                    <div className="md:col-span-8">
                      <label className="block font-bold text-primary uppercase tracking-wider mb-1 text-[10px]">
                        Origin Facility
                      </label>
                      <select
                        value={newShipment.origin_facility_id || ""}
                        onChange={(e) => {
                          const facId = e.target.value;
                          const fac = facilities.find((f) => f.id === facId);
                          setNewShipment((prev) => ({
                            ...prev,
                            origin_facility_id: facId,
                            origin: fac ? `${fac.name}, ${fac.district}, ${fac.state}` : prev.origin,
                          }));
                        }}
                        className="w-full bg-background border border-outline-variant rounded-xl p-2.5 font-semibold focus:outline-none focus:border-digital-mint text-xs"
                      >
                        <option value="">-- Choose Origin Packhouse / Godown --</option>
                        {facilities.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.name} ({f.facility_type.replace('_', ' ')} • {f.district})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="md:col-span-4">
                      <label className="block font-bold text-primary uppercase tracking-wider mb-1 text-[10px]">
                        Origin Operation
                      </label>
                      <select
                        value={newShipment.origin_operation || "packhouse_cooling"}
                        onChange={(e) => setNewShipment({ ...newShipment, origin_operation: e.target.value })}
                        className="w-full bg-background border border-outline-variant rounded-xl p-2.5 font-semibold focus:outline-none focus:border-digital-mint text-xs"
                      >
                        <option value="packhouse_cooling">Packhouse Cooling</option>
                        <option value="harvesting_aggregation">Harvesting Aggregation</option>
                        <option value="cold_storage">Cold Storage</option>
                      </select>
                    </div>
                  </div>

                  {/* Origin Suitability Feedback */}
                  {newShipment.origin_facility_id && (
                    <div className="text-[11px] p-2 rounded-lg border bg-white flex items-start gap-1.5">
                      <span className="material-symbols-outlined text-xs mt-0.5 shrink-0">
                        {checkingOriginSuit ? "hourglass_empty" : originSuitability?.suitable ? "check_circle" : "warning"}
                      </span>
                      <div className="flex-1">
                        {checkingOriginSuit ? (
                          <span className="text-slate-500">Checking guava suitability...</span>
                        ) : originSuitability ? (
                          <div>
                            <span className={`font-bold ${originSuitability.suitable ? "text-emerald-800" : "text-amber-800"}`}>
                              {originSuitability.suitable ? "Guava Suitable: " : "Suitability Caveat: "}
                            </span>
                            <span className="text-slate-700">{originSuitability.reasons?.[0]}</span>
                            {originSuitability.warnings?.length > 0 && (
                              <p className="text-[10px] text-amber-700 mt-0.5">{originSuitability.warnings[0]}</p>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-500">Suitability verification pending</span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Intermediate Hub (Optional) & Operation */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5 pt-2 border-t border-outline-variant/30">
                    <div className="md:col-span-8">
                      <label className="block font-bold text-primary uppercase tracking-wider mb-1 text-[10px]">
                        Intermediate Transit Hub (Optional)
                      </label>
                      <select
                        value={newShipment.intermediate_facility_id || ""}
                        onChange={(e) => setNewShipment({ ...newShipment, intermediate_facility_id: e.target.value })}
                        className="w-full bg-background border border-outline-variant rounded-xl p-2.5 font-semibold focus:outline-none focus:border-digital-mint text-xs"
                      >
                        <option value="">-- Direct Route (No intermediate hub) --</option>
                        {facilities.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.name} ({f.facility_type.replace('_', ' ')} • {f.district})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="md:col-span-4">
                      <label className="block font-bold text-primary uppercase tracking-wider mb-1 text-[10px]">
                        Hub Operation
                      </label>
                      <select
                        value={newShipment.intermediate_operation || "transit_hub"}
                        onChange={(e) => setNewShipment({ ...newShipment, intermediate_operation: e.target.value })}
                        className="w-full bg-background border border-outline-variant rounded-xl p-2.5 font-semibold focus:outline-none focus:border-digital-mint text-xs"
                      >
                        <option value="transit_hub">Transit Holding Hub</option>
                        <option value="pre_cooling">Pre-Cooling</option>
                        <option value="inspection">Quality Inspection</option>
                      </select>
                    </div>
                  </div>

                  {/* Intermediate Suitability Feedback */}
                  {newShipment.intermediate_facility_id && (
                    <div className="text-[11px] p-2 rounded-lg border bg-white flex items-start gap-1.5">
                      <span className="material-symbols-outlined text-xs mt-0.5 shrink-0">
                        {checkingInterSuit ? "hourglass_empty" : interSuitability?.suitable ? "check_circle" : "warning"}
                      </span>
                      <div className="flex-1">
                        {checkingInterSuit ? (
                          <span className="text-slate-500">Checking intermediate hub suitability...</span>
                        ) : interSuitability ? (
                          <div>
                            <span className={`font-bold ${interSuitability.suitable ? "text-purple-800" : "text-amber-800"}`}>
                              {interSuitability.suitable ? "Hub Validated: " : "Hub Caveat: "}
                            </span>
                            <span className="text-slate-700">{interSuitability.reasons?.[0]}</span>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  )}

                  {/* Destination Facility & Operation */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5 pt-2 border-t border-outline-variant/30">
                    <div className="md:col-span-8">
                      <label className="block font-bold text-primary uppercase tracking-wider mb-1 text-[10px]">
                        Destination Facility
                      </label>
                      <select
                        value={newShipment.destination_facility_id || ""}
                        onChange={(e) => {
                          const facId = e.target.value;
                          const fac = facilities.find((f) => f.id === facId);
                          setNewShipment((prev) => ({
                            ...prev,
                            destination_facility_id: facId,
                            destination: fac ? `${fac.name}, ${fac.district}, ${fac.state}` : prev.destination,
                          }));
                        }}
                        className="w-full bg-background border border-outline-variant rounded-xl p-2.5 font-semibold focus:outline-none focus:border-digital-mint text-xs"
                      >
                        <option value="">-- Choose Destination Mandi / Cold Store --</option>
                        {facilities.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.name} ({f.facility_type.replace('_', ' ')} • {f.district})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="md:col-span-4">
                      <label className="block font-bold text-primary uppercase tracking-wider mb-1 text-[10px]">
                        Dest. Operation
                      </label>
                      <select
                        value={newShipment.destination_operation || "market_auction"}
                        onChange={(e) => setNewShipment({ ...newShipment, destination_operation: e.target.value })}
                        className="w-full bg-background border border-outline-variant rounded-xl p-2.5 font-semibold focus:outline-none focus:border-digital-mint text-xs"
                      >
                        <option value="market_auction">Market Auction</option>
                        <option value="cold_storage">Cold Storage</option>
                        <option value="packhouse_cooling">Packhouse</option>
                      </select>
                    </div>
                  </div>

                  {/* Destination Suitability Feedback */}
                  {newShipment.destination_facility_id && (
                    <div className="text-[11px] p-2 rounded-lg border bg-white flex items-start gap-1.5">
                      <span className="material-symbols-outlined text-xs mt-0.5 shrink-0">
                        {checkingDestSuit ? "hourglass_empty" : destSuitability?.suitable ? "check_circle" : "warning"}
                      </span>
                      <div className="flex-1">
                        {checkingDestSuit ? (
                          <span className="text-slate-500">Checking destination suitability...</span>
                        ) : destSuitability ? (
                          <div>
                            <span className={`font-bold ${destSuitability.suitable ? "text-sky-800" : "text-amber-800"}`}>
                              {destSuitability.suitable ? "Guava Suitable: " : "Suitability Caveat: "}
                            </span>
                            <span className="text-slate-700">{destSuitability.reasons?.[0]}</span>
                            {destSuitability.warnings?.length > 0 && (
                              <p className="text-[10px] text-amber-700 mt-0.5">{destSuitability.warnings[0]}</p>
                            )}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Origin Address / Landmark</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Abohar Research Station, Punjab"
                    value={newShipment.origin}
                    onChange={(e) => setNewShipment({ ...newShipment, origin: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Destination Address / Landmark</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Chandigarh APMC Mandi"
                    value={newShipment.destination}
                    onChange={(e) => setNewShipment({ ...newShipment, destination: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
              </div>

              {/* Planned Timestamps */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Planned Departure</label>
                  <input
                    type="datetime-local"
                    value={newShipment.planned_departure}
                    onChange={(e) => setNewShipment({ ...newShipment, planned_departure: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-2.5 font-mono text-xs focus:outline-none focus:border-digital-mint"
                  />
                </div>
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Planned Arrival</label>
                  <input
                    type="datetime-local"
                    value={newShipment.planned_arrival}
                    onChange={(e) => setNewShipment({ ...newShipment, planned_arrival: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-2.5 font-mono text-xs focus:outline-none focus:border-digital-mint"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Quantity (kg)</label>
                  <input
                    type="number"
                    step="any"
                    required
                    placeholder="e.g. 350.0"
                    value={newShipment.quantity}
                    onChange={(e) => setNewShipment({ ...newShipment, quantity: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-mono font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Initial Status</label>
                  <select
                    value={newShipment.status}
                    onChange={(e) => setNewShipment({ ...newShipment, status: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                  >
                    <option value="in_transit">In Transit</option>
                    <option value="created">Created</option>
                    <option value="delivered">Delivered</option>
                    <option value="delayed">Delayed</option>
                  </select>
                </div>
              </div>

              <div className="mt-4 flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2.5 border border-outline-variant rounded-xl font-bold uppercase tracking-wider text-outline hover:bg-surface-container-high transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingShipment}
                  className="px-5 py-2.5 bg-emerald-forest hover:bg-primary text-white rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {creatingShipment ? "Registering..." : "Create Shipment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Phase 13 Modal: Record Custody Event */}
      {showAddEvent && selectedShipment && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto p-6 md:p-8 border border-outline-variant shadow-2xl relative">
            <button
              onClick={() => setShowAddEvent(false)}
              className="absolute top-5 right-5 text-outline hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>

            <h3 className="text-lg font-bold text-emerald-forest mb-1 flex items-center gap-2">
              <span className="material-symbols-outlined text-digital-mint">post_add</span>
              Record Custody Event
            </h3>
            <p className="text-xs text-on-surface-variant mb-6">
              Append verifiable custody event to Shipment <strong className="font-mono text-primary">#{selectedShipment.id}</strong>.
            </p>

            {eventFormError && (
              <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-xl text-xs text-error font-medium">
                {eventFormError}
              </div>
            )}

            <form onSubmit={handleAddEvent} className="flex flex-col gap-4 text-xs">
              <div>
                <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Event Type</label>
                <select
                  value={newEvent.event_type}
                  onChange={(e) => setNewEvent({ ...newEvent, event_type: e.target.value })}
                  className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                >
                  <option value="facility_handover">Facility Handover Recorded</option>
                  <option value="arrival_recorded">Arrival at Facility</option>
                  <option value="shipment_dispatched">Shipment Dispatched</option>
                  <option value="in_transit">In Transit Checkpoint</option>
                  <option value="delivery_completed">Delivery Completed</option>
                  <option value="tracking_signal_lost">Tracking Signal Lost</option>
                  <option value="tracking_signal_restored">Tracking Signal Restored</option>
                  <option value="temperature_excursion_alert">Temperature Excursion Alert</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Associated Facility (Optional)</label>
                <select
                  value={newEvent.facility_id}
                  onChange={(e) => setNewEvent({ ...newEvent, facility_id: e.target.value })}
                  className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                >
                  <option value="">-- No specific facility --</option>
                  {selectedShipment.origin_facility && (
                    <option value={selectedShipment.origin_facility.id}>
                      Origin: {selectedShipment.origin_facility.name}
                    </option>
                  )}
                  {selectedShipment.intermediate_facility && (
                    <option value={selectedShipment.intermediate_facility.id}>
                      Transit Hub: {selectedShipment.intermediate_facility.name}
                    </option>
                  )}
                  {selectedShipment.destination_facility && (
                    <option value={selectedShipment.destination_facility.id}>
                      Destination: {selectedShipment.destination_facility.name}
                    </option>
                  )}
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name} ({f.district})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Event Source</label>
                <select
                  value={newEvent.source}
                  onChange={(e) => setNewEvent({ ...newEvent, source: e.target.value })}
                  className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                >
                  <option value="manual_operator">Manual Operator Entry</option>
                  <option value="system_event">Automated System Checkpoint</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Event Description</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Detail the handover condition, seal verification, or inspection notes..."
                  value={newEvent.description}
                  onChange={(e) => setNewEvent({ ...newEvent, description: e.target.value })}
                  className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                />
              </div>

              <div className="mt-4 flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowAddEvent(false)}
                  className="px-4 py-2.5 border border-outline-variant rounded-xl font-bold uppercase tracking-wider text-outline hover:bg-surface-container-high transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loggingEvent}
                  className="px-5 py-2.5 bg-emerald-forest hover:bg-primary text-white rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {loggingEvent ? "Logging Event..." : "Record Event"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Telemetry Reading */}
      {showAddTelemetry && selectedShipment && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto p-6 md:p-8 border border-outline-variant shadow-2xl relative">
            <button
              onClick={() => setShowAddTelemetry(false)}
              className="absolute top-5 right-5 text-outline hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>

            <h3 className="text-lg font-bold text-emerald-forest mb-1 flex items-center gap-2">
              <span className="material-symbols-outlined text-digital-mint">sensors</span>
              Log Telemetry Reading
            </h3>
            <p className="text-xs text-on-surface-variant mb-6">
              Post sensor sample to Shipment <strong className="font-mono text-primary">#{selectedShipment.id}</strong>.
            </p>

            {telemetryFormError && (
              <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-xl text-xs text-error font-medium">
                {telemetryFormError}
              </div>
            )}

            <form onSubmit={handleAddTelemetry} className="flex flex-col gap-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Temperature (°C)</label>
                  <input
                    type="number"
                    step="0.1"
                    required
                    placeholder="e.g. 6.2"
                    value={newTelemetry.temperature}
                    onChange={(e) => setNewTelemetry({ ...newTelemetry, temperature: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-mono font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Humidity (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    required
                    placeholder="e.g. 86.5"
                    value={newTelemetry.humidity}
                    onChange={(e) => setNewTelemetry({ ...newTelemetry, humidity: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-mono font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Sensor ID</label>
                <input
                  type="text"
                  placeholder="e.g. SNS-COLD-01"
                  value={newTelemetry.sensor_id}
                  onChange={(e) => setNewTelemetry({ ...newTelemetry, sensor_id: e.target.value })}
                  className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                />
              </div>

              <div>
                <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Location Description</label>
                <input
                  type="text"
                  placeholder="e.g. Malout Bypass Corridor, NH-7"
                  value={newTelemetry.location}
                  onChange={(e) => setNewTelemetry({ ...newTelemetry, location: e.target.value })}
                  className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                />
              </div>

              <div className="mt-4 flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowAddTelemetry(false)}
                  className="px-4 py-2.5 border border-outline-variant rounded-xl font-bold uppercase tracking-wider text-outline hover:bg-surface-container-high transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loggingTelemetry}
                  className="px-5 py-2.5 bg-digital-mint hover:bg-emerald-forest text-white rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {loggingTelemetry ? "Recording..." : "Save Reading"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Record PostGIS GPS Waypoint */}
      {showAddWaypoint && selectedShipment && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto p-6 md:p-8 border border-outline-variant shadow-2xl relative">
            <button
              onClick={() => setShowAddWaypoint(false)}
              className="absolute top-5 right-5 text-outline hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>

            <h3 className="text-lg font-bold text-emerald-forest mb-1 flex items-center gap-2">
              <span className="material-symbols-outlined text-digital-mint">add_location_alt</span>
              Record PostGIS Waypoint
            </h3>
            <p className="text-xs text-on-surface-variant mb-4">
              Add spatial GPS coordinates (WGS84 EPSG:4326) to Shipment <strong className="font-mono text-primary">#{selectedShipment.id}</strong>.
            </p>

            {/* Fast Presets for Punjab Belt */}
            <div className="mb-4 p-3 bg-surface-container-low rounded-xl border border-outline-variant/40">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                Quick Preset Locations:
              </span>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setNewWaypoint({
                    ...newWaypoint,
                    latitude: "30.1453",
                    longitude: "74.1994",
                    checkpoint: "Abohar Packhouse Hub",
                  })}
                  className="px-2 py-1 bg-white hover:bg-slate-100 rounded text-[10px] font-semibold text-emerald-800 border border-slate-200"
                >
                  Abohar Hub (30.15°, 74.20°)
                </button>
                <button
                  type="button"
                  onClick={() => setNewWaypoint({
                    ...newWaypoint,
                    latitude: "30.1915",
                    longitude: "74.4989",
                    checkpoint: "Malout Corridor Toll",
                  })}
                  className="px-2 py-1 bg-white hover:bg-slate-100 rounded text-[10px] font-semibold text-emerald-800 border border-slate-200"
                >
                  Malout Toll (30.19°, 74.50°)
                </button>
                <button
                  type="button"
                  onClick={() => setNewWaypoint({
                    ...newWaypoint,
                    latitude: "30.2110",
                    longitude: "74.9455",
                    checkpoint: "Bathinda Cold Storage Hub",
                  })}
                  className="px-2 py-1 bg-white hover:bg-slate-100 rounded text-[10px] font-semibold text-emerald-800 border border-slate-200"
                >
                  Bathinda Hub (30.21°, 74.95°)
                </button>
                <button
                  type="button"
                  onClick={() => setNewWaypoint({
                    ...newWaypoint,
                    latitude: "30.9010",
                    longitude: "75.8573",
                    checkpoint: "Ludhiana Central Godown",
                  })}
                  className="px-2 py-1 bg-white hover:bg-slate-100 rounded text-[10px] font-semibold text-emerald-800 border border-slate-200"
                >
                  Ludhiana Godown (30.90°, 75.86°)
                </button>
                <button
                  type="button"
                  onClick={() => setNewWaypoint({
                    ...newWaypoint,
                    latitude: "28.7161",
                    longitude: "77.1706",
                    checkpoint: "Azadpur APMC Mandi, Delhi",
                  })}
                  className="px-2 py-1 bg-white hover:bg-slate-100 rounded text-[10px] font-semibold text-emerald-800 border border-slate-200"
                >
                  Azadpur APMC (28.72°, 77.17°)
                </button>
              </div>
            </div>

            {waypointFormError && (
              <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-xl text-xs text-error font-medium">
                {waypointFormError}
              </div>
            )}

            <form onSubmit={handleAddWaypoint} className="flex flex-col gap-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Latitude (-90 to 90)</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    placeholder="e.g. 30.1915"
                    value={newWaypoint.latitude}
                    onChange={(e) => setNewWaypoint({ ...newWaypoint, latitude: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-mono font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Longitude (-180 to 180)</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    placeholder="e.g. 74.4989"
                    value={newWaypoint.longitude}
                    onChange={(e) => setNewWaypoint({ ...newWaypoint, longitude: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-mono font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Speed (km/h)</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="e.g. 58.0"
                    value={newWaypoint.speed_kmh}
                    onChange={(e) => setNewWaypoint({ ...newWaypoint, speed_kmh: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-mono font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
                <div>
                  <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Heading (0–360°)</label>
                  <input
                    type="number"
                    step="1"
                    placeholder="e.g. 78"
                    value={newWaypoint.heading_deg}
                    onChange={(e) => setNewWaypoint({ ...newWaypoint, heading_deg: e.target.value })}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 font-mono font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-primary uppercase tracking-wider mb-1.5">Checkpoint / Landmark</label>
                <input
                  type="text"
                  placeholder="e.g. NH-7 Corridor near Malout"
                  value={newWaypoint.checkpoint}
                  onChange={(e) => setNewWaypoint({ ...newWaypoint, checkpoint: e.target.value })}
                  className="w-full bg-background border border-outline-variant rounded-xl p-3 font-semibold focus:outline-none focus:border-digital-mint"
                />
              </div>

              <div className="mt-4 flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowAddWaypoint(false)}
                  className="px-4 py-2.5 border border-outline-variant rounded-xl font-bold uppercase tracking-wider text-outline hover:bg-surface-container-high transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loggingWaypoint}
                  className="px-5 py-2.5 bg-emerald-forest hover:bg-primary text-white rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {loggingWaypoint ? "Saving to PostGIS..." : "Record Waypoint"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
