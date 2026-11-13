"use client";
import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { isValidCoordinate, isWithinIndia, normalizeShipmentCoordinates } from "../lib/api";

/**
 * Creates custom SVG Leaflet DivIcon for a shipment vehicle marker.
 */
function createShipmentIcon(shipment, isSelected) {
  const isAlert = (shipment.risk_index ?? 0) > 40 || shipment.status === "quarantined";
  const isInTransit = shipment.status === "in_transit";

  let pinColor = "#15803d"; // Emerald green
  if (isAlert) {
    pinColor = "#dc2626"; // Red
  } else if (isInTransit) {
    pinColor = "#0284c7"; // Blue
  }

  const pulseRing = isSelected
    ? `<span style="position:absolute; width:44px; height:44px; top:-8px; left:-8px; border-radius:50%; background:${pinColor}; opacity:0.35; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></span>`
    : "";

  const html = `
    <div style="position:relative; width:30px; height:30px; display:flex; align-items:center; justify-content:center;">
      ${pulseRing}
      <div style="
        width: 30px;
        height: 30px;
        border-radius: 50% 50% 50% 0;
        background: ${pinColor};
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        border: 2px solid #ffffff;
      ">
        <span style="
          transform: rotate(45deg);
          color: white;
          font-size: 11px;
          font-weight: bold;
          font-family: ui-monospace, monospace;
        ">
          ${isAlert ? "!" : "🚚"}
        </span>
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: "custom-shipment-marker",
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });
}

/**
 * Creates custom SVG Leaflet DivIcon for an agricultural storage facility or godown.
 */
function createFacilityIcon(facility, isHighlighted, role = null) {
  const typeColors = {
    packhouse: "#065f46", // Emerald
    cold_storage: "#0284c7", // Sky blue
    godown: "#4338ca", // Indigo
    warehouse: "#7c3aed", // Violet
    mandi: "#d97706", // Amber
  };

  const typeIcons = {
    packhouse: "🌱",
    cold_storage: "❄️",
    godown: "🏛️",
    warehouse: "📦",
    mandi: "🛒",
  };

  const bg = typeColors[facility.facility_type] || "#475569";
  const iconSymbol = typeIcons[facility.facility_type] || "📍";

  const ringColor =
    role === "origin"
      ? "#10b981"
      : role === "destination"
      ? "#f59e0b"
      : role === "intermediate"
      ? "#8b5cf6"
      : bg;

  const roleText =
    role === "origin"
      ? "ORIGIN"
      : role === "destination"
      ? "DEST"
      : role === "intermediate"
      ? "TRANSIT"
      : "";

  const pulseRing = isHighlighted
    ? `<span style="position:absolute; width:48px; height:48px; top:-9px; left:-9px; border-radius:50%; background:${ringColor}; opacity:0.4; animation: ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;"></span>`
    : "";

  const roleBadge = role
    ? `<span style="position:absolute; top:-6px; right:-6px; background:${ringColor}; color:white; font-size:9px; font-weight:800; padding:1px 4px; border-radius:4px; border:1px solid white; z-index:10;">${roleText}</span>`
    : "";

  const html = `
    <div style="position:relative; width:30px; height:30px; display:flex; align-items:center; justify-content:center;">
      ${pulseRing}
      ${roleBadge}
      <div style="
        width: 30px;
        height: 30px;
        border-radius: 8px;
        background: ${bg};
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        border: 2px solid #ffffff;
      ">
        <span style="font-size: 14px; line-height: 1;">
          ${iconSymbol}
        </span>
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: "custom-facility-marker",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15],
  });
}

/**
 * Creates small waypoint dot icon for route breadcrumb history.
 */
function createWaypointDotIcon(idx, isLatest) {
  const bg = isLatest ? "#059669" : "#64748b";
  const html = `
    <div style="
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: ${bg};
      border: 2px solid #ffffff;
      box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    "></div>
  `;
  return L.divIcon({
    html,
    className: "waypoint-dot-marker",
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

// Default Punjab Agricultural Center (Abohar / Bathinda / Ludhiana corridor)
const PUNJAB_DEFAULT_CENTER = [30.5000, 74.8000];

export default function TrackingMap({
  shipments = [],
  selectedShipment = null,
  selectedRoute = null,
  loadingRoute = false,
  waypoints = [],
  facilities = [],
  simulationSession = null,
  simulationRoute = null,
  mapPickMode = null,
  onMapPick = null,
  onSelectShipment = () => {},
  onSelectFacility = () => {},
  className = "",
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const facilitiesLayerRef = useRef(null);
  const markersLayerRef = useRef(null);
  const routeLayerRef = useRef(null);
  const simulationLayerRef = useRef(null);

  const [showFacilities, setShowFacilities] = useState(true);
  const [selectedFacilityType, setSelectedFacilityType] = useState("all");

  // Initialize Leaflet map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: PUNJAB_DEFAULT_CENTER,
      zoom: 8,
      zoomControl: false,
    });

    // Add zoom control to top-right
    L.control.zoom({ position: "topright" }).addTo(map);

    // OpenStreetMap Free Tile Provider
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | AgriChain India',
      maxZoom: 18,
    }).addTo(map);

    facilitiesLayerRef.current = L.layerGroup().addTo(map);
    routeLayerRef.current = L.layerGroup().addTo(map);
    markersLayerRef.current = L.layerGroup().addTo(map);
    simulationLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    // Responsive size invalidation when container resizes
    let resizeObserver = null;
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => {
        map.invalidateSize();
      });
      resizeObserver.observe(mapContainerRef.current);
    }

    const handleWindowResize = () => {
      map.invalidateSize();
    };
    window.addEventListener("resize", handleWindowResize);

    return () => {
      if (resizeObserver) resizeObserver.disconnect();
      window.removeEventListener("resize", handleWindowResize);
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Trigger size invalidation when parent dimensions or className changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.invalidateSize();
      }
    }, 120);
    return () => clearTimeout(timer);
  }, [className]);

  // Render Storage Facilities & Godowns
  useEffect(() => {
    const map = mapInstanceRef.current;
    const facilitiesLayer = facilitiesLayerRef.current;
    if (!map || !facilitiesLayer) return;

    facilitiesLayer.clearLayers();

    // FEATURE 1: If dynamic simulation is active (RUNNING or PAUSED), hide all unrelated storage/godown markers
    const isSimActive = Boolean(
      simulationSession &&
      (simulationSession.status === "RUNNING" || simulationSession.status === "PAUSED")
    );
    if (isSimActive) {
      return;
    }

    // TASK 2 / MODE B: When a registered shipment is selected, hide all unrelated storage facilities
    if (selectedShipment) {
      return;
    }

    if (!showFacilities || !facilities || facilities.length === 0) return;

    const filtered = facilities.filter((f) => {
      if (selectedFacilityType !== "all" && f.facility_type !== selectedFacilityType) {
        return false;
      }
      return isValidCoordinate(f.latitude, f.longitude) && isWithinIndia(f.latitude, f.longitude);
    });

    filtered.forEach((fac) => {
      const isOrigin = selectedShipment?.origin_facility_id === fac.id;
      const isDest = selectedShipment?.destination_facility_id === fac.id;
      const isInter = selectedShipment?.intermediate_facility_id === fac.id;
      const isHighlighted = isOrigin || isDest || isInter;
      const role = isOrigin ? "origin" : isDest ? "destination" : isInter ? "intermediate" : null;

      const marker = L.marker([fac.latitude, fac.longitude], {
        icon: createFacilityIcon(fac, isHighlighted, role),
        zIndexOffset: isHighlighted ? 600 : 200,
      });

      const verifStatus = fac.verification_status || fac.location_verification_status || "verified";
      const isVerified = verifStatus === "verified";
      const isPartiallyVerified = verifStatus === "partially_verified";
      const isDemo = verifStatus === "demo_simulated";

      const badgeBg = isVerified ? "#dcfce7" : isPartiallyVerified ? "#fef3c7" : isDemo ? "#fee2e2" : "#f1f5f9";
      const badgeColor = isVerified ? "#15803d" : isPartiallyVerified ? "#b45309" : isDemo ? "#b91c1c" : "#475569";
      const badgeLabel = isVerified ? "✓ Sourced & Verified" : isPartiallyVerified ? "⚠ Partially Verified" : isDemo ? "[DEMO DATA]" : "Unverified Lead";

      const isVillageLevel = fac.geocoding_confidence === "village_level" || fac.geocoding_confidence !== "facility_campus";

      const guavaBadges = {
        guava_confirmed: {
          bg: "#ecfdf5",
          color: "#065f46",
          border: "#a7f3d0",
          label: "✓ Guava Handling Confirmed",
        },
        horticulture_unconfirmed: {
          bg: "#f0fdf4",
          color: "#166534",
          border: "#bbf7d0",
          label: "⚠ Horticultural (Guava Unconfirmed)",
        },
        ambient_grain: {
          bg: "#f1f5f9",
          color: "#475569",
          border: "#cbd5e1",
          label: "✕ Ambient Grain (Not Guava-Ready)",
        },
        cold_store_unknown: {
          bg: "#f0f9ff",
          color: "#0369a1",
          border: "#bae6fd",
          label: "❓ Cold Store (Guava Unconfirmed)",
        },
        wholesale_market: {
          bg: "#faf5ff",
          color: "#7e22ce",
          border: "#e9d5ff",
          label: "🛒 Wholesale Market Yard",
        },
      };

      const gBadge = guavaBadges[fac.guava_suitability_category];

      const commoditiesHtml = fac.supported_commodities && fac.supported_commodities.length > 0
        ? `<div style="margin-top: 4px; font-size: 10px; color: #065f46;"><strong>Commodities:</strong> ${fac.supported_commodities.join(", ")}</div>`
        : `<div style="margin-top: 4px; font-size: 10px; color: #64748b; font-style: italic;"><strong>Commodities:</strong> Not available (Unspecified)</div>`;

      const contactHtml = (fac.contact_phone || fac.contact_email)
        ? `<div style="font-size: 10px; color: #334155; display: flex; flex-direction: column; gap: 1px;">
             ${fac.contact_phone ? `<div><strong>Phone:</strong> ${fac.contact_phone}</div>` : `<div><strong>Phone:</strong> <span style="color:#64748b; font-style:italic;">Not available</span></div>`}
             ${fac.contact_email ? `<div><strong>Email:</strong> ${fac.contact_email}</div>` : `<div><strong>Email:</strong> <span style="color:#64748b; font-style:italic;">Not available</span></div>`}
           </div>`
        : `<div style="font-size: 10px; color: #64748b; font-style: italic;"><strong>Contact:</strong> Not available</div>`;

      let sourceTierLabel = "";
      if (fac.source_citation_type === "directory_level_reference") {
        sourceTierLabel = `<span style="font-size: 9px; background: #f8fafc; color: #475569; padding: 1px 5px; border-radius: 4px; border: 1px solid #cbd5e1; font-weight: 600;">Directory-level reference</span>`;
      } else if (fac.source_citation_type === "direct_document") {
        sourceTierLabel = `<span style="font-size: 9px; background: #ecfdf5; color: #065f46; padding: 1px 5px; border-radius: 4px; border: 1px solid #a7f3d0; font-weight: 600;">Direct Document Proof</span>`;
      } else if (fac.source_citation_type === "facility_page") {
        sourceTierLabel = `<span style="font-size: 9px; background: #f0fdf4; color: #166534; padding: 1px 5px; border-radius: 4px; border: 1px solid #bbf7d0; font-weight: 600;">Official Facility Page</span>`;
      } else if (fac.source_citation_type === "official_portal") {
        sourceTierLabel = `<span style="font-size: 9px; background: #ecfdf5; color: #065f46; padding: 1px 5px; border-radius: 4px; border: 1px solid #a7f3d0; font-weight: 600;">Official Portal Proof</span>`;
      } else if (fac.source_citation_type === "committee_proceeding") {
        sourceTierLabel = `<span style="font-size: 9px; background: #fef3c7; color: #92400e; padding: 1px 5px; border-radius: 4px; border: 1px solid #fde68a; font-weight: 600;">PAC Committee Sanction</span>`;
      }

      const sourceLinkHtml = fac.source_url
        ? `<div style="margin-top: 6px; font-size: 10px; display: flex; flex-direction: column; gap: 2px;">
             <div style="display: flex; align-items: center; gap: 4px;">
               ${sourceTierLabel}
             </div>
             <a href="${fac.source_url}" target="_blank" rel="noopener noreferrer" style="color: #0284c7; text-decoration: underline; font-weight: 600; margin-top: 2px;">
               Source: ${fac.source_name || "Official Document"} &nearr;
             </a>
           </div>`
        : fac.source_name
        ? `<div style="margin-top: 5px; font-size: 10px; color: #64748b;">Source: ${fac.source_name}</div>`
        : "";

      const approximateBanner = isVillageLevel
        ? `<div style="background: #fef3c7; color: #92400e; font-size: 10px; font-weight: 700; padding: 3px 6px; border-radius: 4px; margin-bottom: 4px; border: 1px solid #fde68a;">
             📍 Approximate location (Village/Town centroid)
           </div>
           <div style="font-size: 9px; color: #b45309; margin-top: -2px; margin-bottom: 6px; font-style: italic;">
             * Pin marks administrative centroid — not exact facility gate.
           </div>`
        : `<div style="background: #ecfdf5; color: #065f46; font-size: 10px; font-weight: 700; padding: 3px 6px; border-radius: 4px; margin-bottom: 6px; border: 1px solid #a7f3d0;">
             ✓ Campus-verified entrance coordinates
           </div>`;

      const guavaBadgeHtml = gBadge
        ? `<div style="margin-bottom: 6px;">
             <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: ${gBadge.bg}; color: ${gBadge.color}; border: 1px solid ${gBadge.border};">
               ${gBadge.label}
             </span>
           </div>`
        : "";

      const statusHtml = fac.operational_status
        ? `<div>Status: <strong style="text-transform: capitalize; color: #15803d;">${fac.operational_status}</strong></div>`
        : `<div>Status: <span style="color: #64748b; font-style: italic;">Not available (Operating status unconfirmed)</span></div>`;

      const legalVerifBadge = `<span style="font-size: 9px; font-weight: 600; padding: 1px 5px; border-radius: 3px; background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0;">Legal Entity: ${fac.legal_entity_verification === "verified" ? "Verified" : "Unverified"}</span>`;
      const physicalVerifBadge = `<span style="font-size: 9px; font-weight: 600; padding: 1px 5px; border-radius: 3px; background: ${fac.physical_facility_verification === "verified" ? "#ecfdf5" : "#fef3c7"}; color: ${fac.physical_facility_verification === "verified" ? "#065f46" : "#92400e"}; border: 1px solid ${fac.physical_facility_verification === "verified" ? "#a7f3d0" : "#fde68a"};">Physical Site: ${fac.physical_facility_verification === "verified" ? "Verified" : "Partially Verified"}</span>`;

      const popupContent = `
        <div style="font-family: inherit; font-size: 12px; min-width: 250px; max-width: 280px; padding: 2px;">
          ${approximateBanner}
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <strong style="color: #064e3b; font-size: 13px;">${fac.name}</strong>
          </div>
          ${guavaBadgeHtml}
          <div style="display: flex; gap: 4px; margin-bottom: 4px; flex-wrap: wrap;">
            <span style="font-size: 10px; text-transform: uppercase; font-weight: bold; padding: 2px 6px; border-radius: 4px; background: #e0f2fe; color: #0369a1;">
              ${fac.facility_type.replace("_", " ")}
            </span>
            <span style="font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor};">
              ${badgeLabel}
            </span>
          </div>
          <div style="display: flex; gap: 3px; margin-bottom: 6px; flex-wrap: wrap;">
            ${legalVerifBadge}
            ${physicalVerifBadge}
          </div>
          <div style="color: #475569; font-size: 11px; margin-bottom: 4px;">
            📍 ${fac.address}, ${fac.village_or_city}, ${fac.district}, ${fac.state} ${fac.postal_code || ""}
          </div>
          <div style="font-size: 11px; color: #334155; margin-top: 4px; padding-top: 4px; border-top: 1px solid #e2e8f0; display: flex; flex-direction: column; gap: 2px;">
            ${fac.capacity != null ? `<div>Published Capacity: <strong>${fac.capacity} ${fac.capacity_unit || "MT"}</strong></div>` : `<div style="color: #64748b; font-style: italic;">Capacity: Not available (Unlisted in source)</div>`}
            ${fac.current_utilization != null ? `<div>Occupancy: <strong>${fac.current_utilization}%</strong></div>` : ""}
            ${fac.storage_temperature_min_c != null ? `<div>Temp Range: <strong>${fac.storage_temperature_min_c}°C – ${fac.storage_temperature_max_c}°C</strong></div>` : ""}
            ${statusHtml}
            ${contactHtml}
            ${commoditiesHtml}
            ${sourceLinkHtml}
          </div>
          <div style="color: #64748b; font-size: 10px; margin-top: 6px; font-family: monospace; padding-top: 4px; border-top: 1px dashed #e2e8f0;">
            ${isVillageLevel ? "Approximate Coordinates" : "Campus Coordinates"}: ${fac.latitude.toFixed(4)}° N, ${fac.longitude.toFixed(4)}° E
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on("click", () => {
        onSelectFacility(fac);
      });

      facilitiesLayer.addLayer(marker);
    });
  }, [facilities, showFacilities, selectedFacilityType, selectedShipment, onSelectFacility, simulationSession?.status]);

  // Update shipment markers & bounds
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;
    if (!map || !markersLayer) return;

    markersLayer.clearLayers();

    // FEATURE 1: If dynamic simulation is active (RUNNING or PAUSED), hide all unrelated shipment markers
    const isSimActive = Boolean(
      simulationSession &&
      (simulationSession.status === "RUNNING" || simulationSession.status === "PAUSED")
    );
    if (isSimActive) {
      return;
    }

    // TASK 2 / MODE B: When a shipment is selected, only render this specific shipment's vehicle marker (if it has valid GPS)
    if (selectedShipment) {
      const coords = normalizeShipmentCoordinates(selectedShipment);
      if (coords) {
        const [lat, lng] = coords;
        if (isWithinIndia(lat, lng)) {
          const marker = L.marker([lat, lng], {
            icon: createShipmentIcon(selectedShipment, true),
            zIndexOffset: 1500,
          });
          const popupContent = `
            <div style="font-family: inherit; font-size: 12px; min-width: 220px; padding: 2px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <strong style="color: #064e3b; font-family: monospace; font-size: 13px;">#${selectedShipment.id}</strong>
                <span style="font-size: 10px; text-transform: uppercase; font-weight: bold; padding: 2px 6px; border-radius: 4px; background: #e0f2fe; color: #0369a1;">
                  ${selectedShipment.status}
                </span>
              </div>
              <div style="font-weight: 600; color: #1e293b; margin-bottom: 4px;">
                🚚 Active Vehicle Position
              </div>
              <div style="color: #475569; font-size: 11px; margin-bottom: 4px;">
                ${selectedShipment.origin || "Origin"} &rarr; ${selectedShipment.destination || "Destination"}
              </div>
              <div style="color: #64748b; font-size: 10px; margin-top: 4px; font-family: monospace;">
                GPS: ${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E
              </div>
            </div>
          `;
          marker.bindPopup(popupContent);
          markersLayer.addLayer(marker);
        }
      }
      return;
    }

    const validPoints = [];

    shipments.forEach((s) => {
      const coords = normalizeShipmentCoordinates(s);
      if (!coords) return;

      const [lat, lng] = coords;
      // Filter out invalid or foreign points outside India
      if (!isWithinIndia(lat, lng)) return;

      validPoints.push([lat, lng]);

      const isSelected = selectedShipment?.id === s.id;
      const marker = L.marker([lat, lng], {
        icon: createShipmentIcon(s, isSelected),
        zIndexOffset: isSelected ? 1000 : 300,
      });

      const popupContent = `
        <div style="font-family: inherit; font-size: 12px; min-width: 220px; padding: 2px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: #064e3b; font-family: monospace; font-size: 13px;">#${s.id}</strong>
            <span style="font-size: 10px; text-transform: uppercase; font-weight: bold; padding: 2px 6px; border-radius: 4px; background: #e0f2fe; color: #0369a1;">
              ${s.status}
            </span>
          </div>
          <div style="font-weight: 600; color: #1e293b; margin-bottom: 4px;">
            🥭 ${s.produce_type || "Guava"} • ${s.quantity || 0} kg
          </div>
          <div style="color: #475569; font-size: 11px; margin-bottom: 4px;">
            ${s.origin || "Origin"} &rarr; ${s.destination || "Destination"}
          </div>
          ${s.origin_facility ? `<div style="font-size: 10px; color: #065f46;">🌱 Origin Godown: ${s.origin_facility.name}</div>` : ""}
          ${s.destination_facility ? `<div style="font-size: 10px; color: #0369a1;">📦 Destination Godown: ${s.destination_facility.name}</div>` : ""}
          <div style="display: flex; justify-content: space-between; font-size: 11px; color: #334155; margin-top: 6px; padding-top: 6px; border-top: 1px solid #e2e8f0;">
            <span>Temp: <strong>${s.temperature_c != null ? `${s.temperature_c}°C` : "N/A"}</strong></span>
            <span>Risk: <strong>${s.risk_index != null ? `${s.risk_index}%` : "0%"}</strong></span>
          </div>
          <div style="color: #64748b; font-size: 10px; margin-top: 4px; font-family: monospace;">
            Vehicle GPS: ${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E (India)
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on("click", () => {
        onSelectShipment(s);
      });

      markersLayer.addLayer(marker);
    });

    // Auto-fit map to show all valid Indian shipment locations on first load
    if (validPoints.length > 0 && !selectedShipment) {
      const bounds = L.latLngBounds(validPoints);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 11 });
    }
  }, [shipments, selectedShipment, onSelectShipment, simulationSession?.status]);

  // Update dynamic road route or location history route for selected shipment
  useEffect(() => {
    const map = mapInstanceRef.current;
    const routeLayer = routeLayerRef.current;
    if (!map || !routeLayer) return;

    routeLayer.clearLayers();

    // FEATURE 1: If dynamic simulation is active (RUNNING or PAUSED) for this shipment, hide static shipment route lines
    const isSimActive = Boolean(
      simulationSession &&
      (simulationSession.status === "RUNNING" || simulationSession.status === "PAUSED") &&
      (!selectedShipment || !simulationSession.shipment_id || simulationSession.shipment_id === selectedShipment.id)
    );
    if (isSimActive) {
      return;
    }

    if (!selectedShipment) return;

    // Filter valid waypoints in chronological order, strictly inside India
    const validWaypoints = (waypoints || [])
      .filter((w) => isValidCoordinate(w.latitude, w.longitude) && isWithinIndia(w.latitude, w.longitude))
      .sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime());

    // 1. If an authoritative dynamic road route is available for this shipment, render highway polyline & Point A / B
    if (
      selectedRoute &&
      selectedRoute.shipment_id === selectedShipment.id &&
      selectedRoute.geometry &&
      Array.isArray(selectedRoute.geometry.coordinates) &&
      selectedRoute.geometry.coordinates.length > 1
    ) {
      // GeoJSON [lon, lat] -> Leaflet [lat, lon]
      const routeLatLngs = selectedRoute.geometry.coordinates.map((c) => [c[1], c[0]]);

      const highwayPolyline = L.polyline(routeLatLngs, {
        color: "#2563eb", // Royal blue road highway color
        weight: 5,
        opacity: 0.9,
        lineJoin: "round",
      });
      routeLayer.addLayer(highwayPolyline);

      // Start Pin (Point A)
      const startPt = routeLatLngs[0];
      const startName = selectedRoute.origin_name || selectedShipment.origin || "Origin";
      const startMarker = L.marker(startPt, {
        icon: L.divIcon({
          html: `<div style="background:#10b981; color:white; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:14px; border:2.5px solid white; box-shadow:0 3px 8px rgba(0,0,0,0.35);">A</div>`,
          className: "shipment-start-marker",
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        }),
        zIndexOffset: 1200,
      });
      startMarker.bindPopup(`
        <div style="font-size:12px; font-family:inherit; padding:2px;">
          <div style="color:#059669; font-weight:700; font-size:13px; margin-bottom:2px;">Point A: Origin</div>
          <div style="font-weight:600; color:#1e293b;">${startName}</div>
          <div style="color:#64748b; font-size:10px; font-family:monospace; margin-top:4px;">
            Coordinates: ${startPt[0].toFixed(4)}° N, ${startPt[1].toFixed(4)}° E
          </div>
        </div>
      `);
      startMarker.bindTooltip(`Point A: ${startName}`, { direction: "top", offset: [0, -12] });
      routeLayer.addLayer(startMarker);

      // End Pin (Point B)
      const endPt = routeLatLngs[routeLatLngs.length - 1];
      const endName = selectedRoute.destination_name || selectedShipment.destination || "Destination";
      const endMarker = L.marker(endPt, {
        icon: L.divIcon({
          html: `<div style="background:#ef4444; color:white; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:14px; border:2.5px solid white; box-shadow:0 3px 8px rgba(0,0,0,0.35);">B</div>`,
          className: "shipment-end-marker",
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        }),
        zIndexOffset: 1200,
      });
      endMarker.bindPopup(`
        <div style="font-size:12px; font-family:inherit; padding:2px;">
          <div style="color:#dc2626; font-weight:700; font-size:13px; margin-bottom:2px;">Point B: Destination</div>
          <div style="font-weight:600; color:#1e293b;">${endName}</div>
          <div style="color:#64748b; font-size:10px; font-family:monospace; margin-top:4px;">
            Coordinates: ${endPt[0].toFixed(4)}° N, ${endPt[1].toFixed(4)}° E
          </div>
          <div style="margin-top:6px; font-size:11px; color:#2563eb; font-weight:700;">
            Total Road Distance: ${selectedRoute.distance_km} km
          </div>
        </div>
      `);
      endMarker.bindTooltip(`Point B: ${endName}`, { direction: "top", offset: [0, -12] });
      routeLayer.addLayer(endMarker);

      // Add intermediate waypoint dots if any recorded
      validWaypoints.forEach((w, idx) => {
        const isLatest = idx === validWaypoints.length - 1;
        const dot = L.marker([w.latitude, w.longitude], {
          icon: createWaypointDotIcon(idx + 1, isLatest),
        });
        dot.bindPopup(`
          <div style="font-size: 11px; font-family: inherit;">
            <strong style="color: #064e3b;">Waypoint #${idx + 1}</strong> (${w.id})<br/>
            <span>Time: ${w.recorded_at ? new Date(w.recorded_at).toLocaleTimeString() : "N/A"}</span><br/>
            ${w.speed_kmh != null ? `Speed: <strong>${w.speed_kmh} km/h</strong><br/>` : ""}
            <span style="font-family: monospace; font-size: 10px; color: #64748b;">
              ${w.latitude.toFixed(4)}° N, ${w.longitude.toFixed(4)}° E
            </span>
          </div>
        `);
        routeLayer.addLayer(dot);
      });

      // Fit bounds tightly around the actual road route
      const bounds = L.latLngBounds(routeLatLngs);
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 12 });
      return;
    }

    // Fallback: If route is not yet loaded, draw waypoints and facility corridor
    const latLngs = validWaypoints.map((w) => [w.latitude, w.longitude]);
    if (latLngs.length > 1) {
      const routeLine = L.polyline(latLngs, {
        color: "#059669",
        weight: 3.5,
        opacity: 0.85,
        dashArray: "6, 8",
        lineJoin: "round",
      });
      routeLayer.addLayer(routeLine);
    }

    const corridorPoints = [];
    if (selectedShipment.origin_facility && isWithinIndia(selectedShipment.origin_facility.latitude, selectedShipment.origin_facility.longitude)) {
      corridorPoints.push([selectedShipment.origin_facility.latitude, selectedShipment.origin_facility.longitude]);
    }
    if (selectedShipment.intermediate_facility && isWithinIndia(selectedShipment.intermediate_facility.latitude, selectedShipment.intermediate_facility.longitude)) {
      corridorPoints.push([selectedShipment.intermediate_facility.latitude, selectedShipment.intermediate_facility.longitude]);
    }
    corridorPoints.push(...latLngs);
    if (selectedShipment.destination_facility && isWithinIndia(selectedShipment.destination_facility.latitude, selectedShipment.destination_facility.longitude)) {
      corridorPoints.push([selectedShipment.destination_facility.latitude, selectedShipment.destination_facility.longitude]);
    }

    if (corridorPoints.length > 1) {
      const corridorLine = L.polyline(corridorPoints, {
        color: "#f59e0b",
        weight: 2,
        opacity: 0.6,
        dashArray: "4, 6",
      });
      routeLayer.addLayer(corridorLine);
      map.fitBounds(L.latLngBounds(corridorPoints), { padding: [60, 60], maxZoom: 11 });
    } else if (latLngs.length === 1) {
      map.flyTo(latLngs[0], 11, { duration: 0.8 });
    }
  }, [selectedShipment, selectedRoute, waypoints, simulationSession?.status]);

  // Handle map click for coordinate picking mode
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const handleMapClick = (e) => {
      if (mapPickMode && onMapPick) {
        onMapPick([e.latlng.lat, e.latlng.lng]);
      }
    };

    map.on("click", handleMapClick);
    return () => {
      map.off("click", handleMapClick);
    };
  }, [mapPickMode, onMapPick]);

  // Render Real-Road Dynamic Simulation Polyline & Animated Virtual Vehicle
  useEffect(() => {
    const map = mapInstanceRef.current;
    const simLayer = simulationLayerRef.current;
    if (!map || !simLayer) return;

    simLayer.clearLayers();

    const isSimActive = Boolean(
      simulationSession &&
      (simulationSession.status === "RUNNING" || simulationSession.status === "PAUSED") &&
      (!selectedShipment || !simulationSession.shipment_id || simulationSession.shipment_id === selectedShipment.id)
    );

    // If a specific shipment is selected, ensure we never render simulation elements from another shipment
    if (selectedShipment && simulationSession?.shipment_id && simulationSession.shipment_id !== selectedShipment.id) {
      return;
    }

    // Only draw simulation elements if simulation is active or if explicit route preview is active in simulation studio
    if (!isSimActive && !simulationRoute) {
      return;
    }

    // 1. Draw highway route polyline if available
    const routeGeo = simulationRoute || simulationSession?.route_geojson;
    if (routeGeo && routeGeo.coordinates && routeGeo.coordinates.length > 1) {
      const latLngs = routeGeo.coordinates.map((c) => [c[1], c[0]]);

      const roadPolyline = L.polyline(latLngs, {
        color: "#2563eb", // Royal blue road color
        weight: 5,
        opacity: 0.9,
        lineJoin: "round",
      });
      simLayer.addLayer(roadPolyline);

      // Start Pin (Point A)
      const startPt = latLngs[0];
      const startName = simulationSession?.origin_name || "Simulation Starting Point";
      const startMarker = L.marker(startPt, {
        icon: L.divIcon({
          html: `<div style="background:#10b981; color:white; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:14px; border:2.5px solid white; box-shadow:0 3px 8px rgba(0,0,0,0.35);">A</div>`,
          className: "sim-start-marker",
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        }),
        zIndexOffset: 1200,
      });
      startMarker.bindPopup(`
        <div style="font-size:12px; font-family:inherit; padding:2px;">
          <div style="color:#059669; font-weight:700; font-size:13px; margin-bottom:2px;">Point A: Starting Point</div>
          <div style="font-weight:600; color:#1e293b;">${startName}</div>
          <div style="color:#64748b; font-size:10px; font-family:monospace; margin-top:4px;">
            Coordinates: ${startPt[0].toFixed(4)}° N, ${startPt[1].toFixed(4)}° E
          </div>
        </div>
      `);
      startMarker.bindTooltip(`Point A: ${startName}`, { direction: "top", offset: [0, -12] });
      simLayer.addLayer(startMarker);

      // End Pin (Point B)
      const endPt = latLngs[latLngs.length - 1];
      const endName = simulationSession?.destination_name || "Simulation Destination";
      const endMarker = L.marker(endPt, {
        icon: L.divIcon({
          html: `<div style="background:#ef4444; color:white; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:14px; border:2.5px solid white; box-shadow:0 3px 8px rgba(0,0,0,0.35);">B</div>`,
          className: "sim-end-marker",
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        }),
        zIndexOffset: 1200,
      });
      endMarker.bindPopup(`
        <div style="font-size:12px; font-family:inherit; padding:2px;">
          <div style="color:#dc2626; font-weight:700; font-size:13px; margin-bottom:2px;">Point B: Destination</div>
          <div style="font-weight:600; color:#1e293b;">${endName}</div>
          <div style="color:#64748b; font-size:10px; font-family:monospace; margin-top:4px;">
            Coordinates: ${endPt[0].toFixed(4)}° N, ${endPt[1].toFixed(4)}° E
          </div>
        </div>
      `);
      endMarker.bindTooltip(`Point B: ${endName}`, { direction: "top", offset: [0, -12] });
      simLayer.addLayer(endMarker);

      // Fit bounds if initially loaded and not running yet
      if (!simulationSession || simulationSession.status === "READY" || simulationSession.status === "CREATED") {
        map.fitBounds(L.latLngBounds(latLngs), { padding: [50, 50], maxZoom: 11 });
      }
    } else if (
      simulationSession &&
      typeof simulationSession.origin_lat === "number" &&
      typeof simulationSession.destination_lat === "number"
    ) {
      const startPt = [simulationSession.origin_lat, simulationSession.origin_lon];
      const endPt = [simulationSession.destination_lat, simulationSession.destination_lon];
      const startName = simulationSession.origin_name || "Simulation Starting Point";
      const endName = simulationSession.destination_name || "Simulation Destination";

      const startMarker = L.marker(startPt, {
        icon: L.divIcon({
          html: `<div style="background:#10b981; color:white; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:14px; border:2.5px solid white; box-shadow:0 3px 8px rgba(0,0,0,0.35);">A</div>`,
          className: "sim-start-marker",
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        }),
      }).bindPopup(`<strong>Point A: Starting Point</strong><br/>${startName}`);
      startMarker.bindTooltip(`Point A: ${startName}`, { direction: "top", offset: [0, -12] });
      simLayer.addLayer(startMarker);

      const endMarker = L.marker(endPt, {
        icon: L.divIcon({
          html: `<div style="background:#ef4444; color:white; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:14px; border:2.5px solid white; box-shadow:0 3px 8px rgba(0,0,0,0.35);">B</div>`,
          className: "sim-end-marker",
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        }),
      }).bindPopup(`<strong>Point B: Destination</strong><br/>${endName}`);
      endMarker.bindTooltip(`Point B: ${endName}`, { direction: "top", offset: [0, -12] });
      simLayer.addLayer(endMarker);
    }

    // 2. Render Virtual Vehicle Marker with Dynamic Heading
    if (
      simulationSession &&
      typeof simulationSession.current_lat === "number" &&
      typeof simulationSession.current_lon === "number"
    ) {
      const lat = simulationSession.current_lat;
      const lon = simulationSession.current_lon;
      const heading = simulationSession.current_heading_deg || 0;
      const speed = simulationSession.current_speed_kmh || 0;
      const status = simulationSession.status || "READY";
      const tel = simulationSession.latest_telemetry || {};
      const temp = tel.temperature_c ?? 5.5;
      const risk = tel.predicted_arrival_risk ?? 10.0;
      const isExcursion = temp > 8.0 || risk > 50.0;

      const vehicleColor = isExcursion ? "#dc2626" : status === "RUNNING" ? "#2563eb" : "#059669";

      const vehicleHtml = `
        <div style="position:relative; width:44px; height:44px; display:flex; align-items:center; justify-content:center;">
          <span style="position:absolute; width:44px; height:44px; border-radius:50%; background:${vehicleColor}; opacity:0.35; animation: ping 1.2s cubic-bezier(0, 0, 0.2, 1) infinite;"></span>
          <div style="
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: ${vehicleColor};
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            border: 2px solid #ffffff;
            transform: rotate(${heading}deg);
            transition: transform 0.4s ease;
          ">
            <span style="color:white; font-size:16px; transform: rotate(-45deg);">🚛</span>
          </div>
        </div>
      `;

      const vehicleIcon = L.divIcon({
        html: vehicleHtml,
        className: "sim-vehicle-marker",
        iconSize: [44, 44],
        iconAnchor: [22, 22],
      });

      const vehicleMarker = L.marker([lat, lon], {
        icon: vehicleIcon,
        zIndexOffset: 2500,
      });

      const popupHtml = `
        <div style="font-family: inherit; font-size: 12px; min-width: 240px; padding: 4px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; border-bottom:1px solid #e2e8f0; padding-bottom:4px;">
            <strong style="color: #1e3a8a; font-family: monospace; font-size: 12px;">${simulationSession.id}</strong>
            <span style="font-size: 9px; font-weight: bold; background: ${isExcursion ? '#fee2e2; color:#991b1b;' : '#dbeafe; color:#1e40af;'} padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">
              ${status} (${simulationSession.scenario || "normal"})
            </span>
          </div>
          <div style="font-weight: 600; color: #1e293b; margin-bottom: 4px;">
            🛣️ Traversal: ${simulationSession.current_distance_km.toFixed(1)} / ${simulationSession.total_distance_km.toFixed(1)} km
          </div>
          <div style="font-size: 11px; color: #475569; margin-bottom: 4px;">
            Speed: <strong>${speed.toFixed(1)} km/h</strong> • Heading: <strong>${heading.toFixed(0)}°</strong>
          </div>
          <div style="display:flex; justify-content:space-between; font-size: 11px; color: #334155; margin-top: 6px; padding-top: 6px; border-top: 1px solid #e2e8f0;">
            <span>Cold Temp: <strong style="color:${temp > 8.0 ? '#dc2626' : '#059669'}">${temp.toFixed(1)}°C</strong></span>
            <span>Arrival Risk: <strong style="color:${risk > 50.0 ? '#dc2626' : '#059669'}">${risk.toFixed(1)}%</strong></span>
          </div>
          <div style="margin-top: 6px; padding: 2px 4px; background: #f8fafc; border-radius: 4px; font-size: 9px; color: #64748b; font-family: monospace; text-align: center;">
            SNS-SIM-DEMO • data_source: simulation
          </div>
        </div>
      `;

      vehicleMarker.bindPopup(popupHtml);
      simLayer.addLayer(vehicleMarker);

      if (status === "RUNNING") {
        map.panTo([lat, lon], { animate: true, duration: 0.5 });
      }
    }
  }, [simulationSession, simulationRoute]);

  // Handler to manually fit all shipments inside India
  const handleFitAll = () => {
    const map = mapInstanceRef.current;
    if (!map) return;
    const validPoints = shipments
      .map(normalizeShipmentCoordinates)
      .filter((c) => c !== null && isWithinIndia(c[0], c[1]));

    if (validPoints.length > 0) {
      const bounds = L.latLngBounds(validPoints);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 11 });
    } else {
      map.flyTo(PUNJAB_DEFAULT_CENTER, 8);
    }
  };

  const handleFitPunjab = () => {
    const map = mapInstanceRef.current;
    if (!map) return;
    map.flyTo(PUNJAB_DEFAULT_CENTER, 8, { duration: 0.8 });
  };

  const geolocatedCount = shipments
    .map(normalizeShipmentCoordinates)
    .filter((c) => c !== null && isWithinIndia(c[0], c[1])).length;

  return (
    <div
      className={`relative isolate z-0 w-full h-full rounded-2xl overflow-hidden border border-outline-variant/60 shadow-inner bg-slate-100 ${className}`}
      style={{ width: "100%", height: "100%", minHeight: "100%" }}
    >
      {/* Map DOM target */}
      <div
        ref={mapContainerRef}
        className="w-full h-full"
        style={{ width: "100%", height: "100%", minHeight: "100%" }}
      />

      {/* Floating Header Controls */}
      <div className="absolute top-3 left-3 z-20 flex flex-wrap items-center gap-2 pointer-events-none">
        {selectedShipment ? (
          <div className="bg-slate-900/90 backdrop-blur-md rounded-xl px-3 py-2 shadow-lg border border-slate-700 flex items-center gap-2.5 text-xs text-white pointer-events-auto">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-400 animate-pulse"></span>
            <span className="font-bold font-mono text-[11px] text-blue-300">
              Focused: #{selectedShipment.id}
            </span>
            <span className="text-slate-200 text-[11px] hidden sm:inline">
              {selectedShipment.origin || "Origin"} &rarr; {selectedShipment.destination || "Destination"}
            </span>
            <button
              onClick={() => onSelectShipment(null)}
              className="ml-1 bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold px-2.5 py-1 rounded-lg transition-colors shadow-sm flex items-center gap-1"
              title="Return to Global Overview"
            >
              <span className="material-symbols-outlined text-xs">public</span>
              Show All Shipments
            </button>
          </div>
        ) : (
          <div className="bg-white/95 backdrop-blur-sm rounded-xl px-3 py-2 shadow-md border border-outline-variant/50 flex items-center gap-2 text-xs pointer-events-auto">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 animate-pulse"></span>
            <span className="font-bold text-emerald-900 font-mono text-[11px]">Punjab PostGIS Map (Global Overview)</span>
            <span className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded text-[10px] font-semibold">
              {geolocatedCount} of {shipments.length} Active Vehicles
            </span>
            <span className="bg-emerald-50 text-emerald-800 px-1.5 py-0.5 rounded text-[10px] font-semibold">
              {facilities.length} Godowns &amp; Hubs
            </span>
          </div>
        )}

        {/* Facility Visibility Toggle (Only in Global Overview) */}
        {!selectedShipment && (
          <button
            onClick={() => setShowFacilities(!showFacilities)}
            className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold shadow-md border flex items-center gap-1.5 transition-colors pointer-events-auto ${
              showFacilities
                ? "bg-emerald-700 text-white border-emerald-800"
                : "bg-white text-slate-700 border-outline-variant/60 hover:bg-slate-50"
            }`}
            title="Toggle godowns and facilities on map"
          >
            <span className="material-symbols-outlined text-xs">warehouse</span>
            {showFacilities ? "Godowns On" : "Godowns Off"}
          </button>
        )}

        {/* Facility Filter Pills (Only in Global Overview) */}
        {!selectedShipment && showFacilities && (
          <div className="hidden md:flex items-center gap-1 bg-white/95 backdrop-blur-sm p-1 rounded-xl shadow-md border border-outline-variant/50 text-[10px] pointer-events-auto">
            {["all", "packhouse", "cold_storage", "godown", "mandi"].map((t) => (
              <button
                key={t}
                onClick={() => setSelectedFacilityType(t)}
                className={`px-2 py-0.5 rounded-lg capitalize font-medium transition-colors ${
                  selectedFacilityType === t
                    ? "bg-slate-800 text-white font-bold"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {t.replace("_", " ")}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Shipment Route Transparency Overlay */}
      {selectedShipment && (
        <div className="absolute top-14 left-3 z-20 flex flex-col gap-1 max-w-[calc(100%-120px)] pointer-events-none">
          {selectedShipment.tracking_mode === "simulated" || (waypoints && waypoints.some((w) => w.location_metadata?.simulated || w.location_metadata?.source === "demo_simulated")) ? (
            <div className="bg-amber-500/95 backdrop-blur-md text-amber-950 border border-amber-300 px-3 py-1.5 rounded-xl shadow-md text-xs font-bold flex items-center gap-2 pointer-events-auto">
              <span className="w-2 h-2 rounded-full bg-amber-900 animate-pulse shrink-0" />
              <span>DEMO / SIMULATED ROUTE — Generated corridors; not real vehicle GPS transponder</span>
            </div>
          ) : selectedShipment.tracking_mode === "live_gps" ? (
            <div className="bg-emerald-600/95 backdrop-blur-md text-white border border-emerald-400 px-3 py-1.5 rounded-xl shadow-md text-xs font-bold flex items-center gap-2 pointer-events-auto">
              <span className="w-2 h-2 rounded-full bg-white animate-ping shrink-0" />
              <span>LIVE GPS ACTIVE — Verified hardware location stream</span>
            </div>
          ) : (
            <div className="bg-slate-700/95 backdrop-blur-md text-white border border-slate-500 px-3 py-1.5 rounded-xl shadow-md text-xs font-bold flex items-center gap-2 pointer-events-auto">
              <span className="w-2 h-2 rounded-full bg-slate-400 shrink-0" />
              <span>LAST KNOWN LOCATION — Live connection offline; showing latest recorded position</span>
            </div>
          )}
          <div className="bg-slate-900/80 backdrop-blur-sm text-slate-200 px-2.5 py-0.5 rounded-lg text-[10px] w-fit font-mono pointer-events-auto">
            Direct waypoint trajectory shown (Road routing API not configured)
          </div>
        </div>
      )}

      {/* Map Legend */}
      <div className="absolute bottom-3 left-3 z-20 hidden sm:flex flex-wrap items-center gap-2 bg-white/95 backdrop-blur-sm px-3 py-2 rounded-xl border border-outline-variant/40 shadow-sm text-[10px] pointer-events-auto">
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-700"></span> Packhouse (🌱)
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-sky-600"></span> Cold Storage (❄️)
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-700"></span> Godown (🏛️)
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-600"></span> APMC Mandi (🛒)
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-600"></span> Active Vehicle (🚚)
        </div>
        <div className="flex items-center gap-1 text-slate-500">
          <span className="border-b-2 border-dashed border-amber-500 w-3"></span> Corridor Link
        </div>
      </div>

      {/* Action Buttons Top-Right */}
      <div className="absolute top-3 right-12 z-20 flex items-center gap-1.5 pointer-events-auto">
        <button
          onClick={handleFitPunjab}
          className="bg-white hover:bg-slate-50 text-slate-800 text-xs font-semibold px-2.5 py-1.5 rounded-lg shadow-md border border-outline-variant/60 flex items-center gap-1 transition-colors"
          title="Center on Punjab Agricultural Corridor"
        >
          <span className="material-symbols-outlined text-sm">my_location</span>
          Punjab
        </button>
        <button
          onClick={handleFitAll}
          className="bg-white hover:bg-slate-50 text-slate-800 text-xs font-semibold px-2.5 py-1.5 rounded-lg shadow-md border border-outline-variant/60 flex items-center gap-1 transition-colors"
          title="Fit map to show all Indian shipments and hubs"
        >
          <span className="material-symbols-outlined text-sm">fit_screen</span>
          Fit All
        </button>
      </div>

      {/* Empty State Banner if no shipments have GPS waypoints */}
      {geolocatedCount === 0 && shipments.length > 0 && (
        <div className="absolute inset-0 z-30 bg-slate-900/40 backdrop-blur-[2px] flex items-center justify-center p-6 pointer-events-none">
          <div className="bg-white rounded-2xl p-6 max-w-sm text-center shadow-xl border border-outline-variant/60 pointer-events-auto">
            <span className="material-symbols-outlined text-3xl text-amber-600 mb-2">satellite_alt</span>
            <h4 className="font-bold text-sm text-slate-800">No Geolocatable Vehicles</h4>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              No shipments currently have verified GPS fixes inside India. Storage facilities remain visible on the map.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
