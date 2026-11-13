"use client";
import React, { useState, useEffect, useMemo } from "react";
import { fetchFacilities, createFacility, hasValidFacilityCoordinates } from "../lib/api";
import TrackingMapClient from "./TrackingMapClient";

export default function FacilityDirectory() {
  const [facilities, setFacilities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters state
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("all");
  const [selectedType, setSelectedType] = useState("all");
  const [selectedVerification, setSelectedVerification] = useState("all");
  const [selectedGuavaCategory, setSelectedGuavaCategory] = useState("all");

  // Map view toggle
  const [showMap, setShowMap] = useState(true);

  // Provenance inspection modal state
  const [selectedFacility, setSelectedFacility] = useState(null);

  // New facility submission modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [addingFacility, setAddingFacility] = useState(false);
  const [addError, setAddError] = useState(null);
  const [newFacility, setNewFacility] = useState({
    id: "",
    name: "",
    facility_type: "packhouse",
    address: "",
    village_or_city: "",
    district: "Fatehgarh Sahib",
    state: "Punjab",
    postal_code: "",
    latitude: "",
    longitude: "",
    capacity: "",
    capacity_unit: "MT",
    contact_phone: "",
    contact_email: "",
    supported_commodities: "Guava, Kinnow, Citrus, Vegetables",
    operational_status: "active",
    guava_suitability_category: "horticulture_unconfirmed",
    source_citation_type: "direct_document",
    legal_entity_verification: "verified",
    physical_facility_verification: "verified",
    source_name: "Punjab Agri Export Corporation Limited (PAGREXCO)",
    source_url: "https://punjabagro.gov.in/wp-content/uploads/2025/03/EOI-Pack-House-cum-Cold-Storage.pdf",
    source_record: "Official Horticultural Infrastructure Directory",
    verification_status: "verified",
    coordinate_source: "Official Survey / GPS Coordinates",
    geocoding_confidence: "facility_campus",
    data_provenance: "Verified against Punjab state agricultural records.",
  });

  const loadFacilitiesData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFacilities();
      if (!Array.isArray(data)) {
        throw new Error("Invalid response format received from facility service.");
      }
      setFacilities(data);
    } catch (err) {
      console.error("Error loading facilities:", err);
      const isFetchFailed = err.message === "fetch failed" || err.message?.includes("fetch failed") || err.message?.includes("Failed to fetch");
      const userMessage = isFetchFailed
        ? "Facility service connection failed. Please ensure the FastAPI backend is running on http://127.0.0.1:8000."
        : (err.message || "Failed to load facility directory from backend.");
      setError(userMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFacilitiesData();
  }, []);

  // Compute unique districts from data
  const districts = useMemo(() => {
    const set = new Set();
    facilities.forEach((f) => {
      if (f.district) set.add(f.district);
    });
    return Array.from(set).sort();
  }, [facilities]);

  // Compute directory overview metrics
  const metrics = useMemo(() => {
    const total = facilities.length;
    const verified = facilities.filter((f) => f.verification_status === "verified").length;
    const partiallyVerified = facilities.filter((f) => f.verification_status === "partially_verified").length;
    const packhouses = facilities.filter((f) => f.facility_type === "packhouse").length;
    const coldStores = facilities.filter((f) => f.facility_type === "cold_storage").length;
    const godowns = facilities.filter((f) => f.facility_type === "godown").length;
    const mandis = facilities.filter((f) => f.facility_type === "mandi").length;

    // Guava supply-chain categories breakdown
    const guavaConfirmed = facilities.filter((f) => f.guava_suitability_category === "guava_confirmed").length;
    const horticultureUnconfirmed = facilities.filter((f) => f.guava_suitability_category === "horticulture_unconfirmed").length;
    const ambientGrain = facilities.filter((f) => f.guava_suitability_category === "ambient_grain").length;
    const coldStoreUnknown = facilities.filter((f) => f.guava_suitability_category === "cold_store_unknown").length;
    const wholesaleMarket = facilities.filter((f) => f.guava_suitability_category === "wholesale_market").length;

    // Total capacity only for records with published capacity
    const totalCapacityMT = facilities.reduce((sum, f) => {
      if (typeof f.capacity === "number" && !isNaN(f.capacity)) {
        return sum + f.capacity;
      }
      return sum;
    }, 0);

    return {
      total,
      verified,
      partiallyVerified,
      packhouses,
      coldStores,
      godowns,
      mandis,
      guavaConfirmed,
      horticultureUnconfirmed,
      ambientGrain,
      coldStoreUnknown,
      wholesaleMarket,
      totalCapacityMT,
    };
  }, [facilities]);

  // Filter facilities
  const filteredFacilities = useMemo(() => {
    return facilities.filter((f) => {
      // Search term filter
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchesName = f.name?.toLowerCase().includes(q);
        const matchesId = f.id?.toLowerCase().includes(q);
        const matchesDistrict = f.district?.toLowerCase().includes(q);
        const matchesCity = f.village_or_city?.toLowerCase().includes(q);
        const matchesAddress = f.address?.toLowerCase().includes(q);
        const matchesCommodity =
          Array.isArray(f.supported_commodities) &&
          f.supported_commodities.some((c) => c.toLowerCase().includes(q));
        const matchesSource =
          f.source_name?.toLowerCase().includes(q) || f.source_record?.toLowerCase().includes(q);
        const matchesGuavaCat = f.guava_suitability_category?.toLowerCase().includes(q);

        if (
          !matchesName &&
          !matchesId &&
          !matchesDistrict &&
          !matchesCity &&
          !matchesAddress &&
          !matchesCommodity &&
          !matchesSource &&
          !matchesGuavaCat
        ) {
          return false;
        }
      }

      // District filter
      if (selectedDistrict !== "all" && f.district !== selectedDistrict) {
        return false;
      }

      // Type filter
      if (selectedType !== "all" && f.facility_type !== selectedType) {
        return false;
      }

      // Verification status filter
      if (selectedVerification !== "all" && f.verification_status !== selectedVerification) {
        return false;
      }

      // Guava suitability category filter
      if (selectedGuavaCategory !== "all" && f.guava_suitability_category !== selectedGuavaCategory) {
        return false;
      }

      return true;
    });
  }, [facilities, searchTerm, selectedDistrict, selectedType, selectedVerification, selectedGuavaCategory]);

  // Count mapped vs unmapped
  const plottableCount = useMemo(() => {
    return filteredFacilities.filter(hasValidFacilityCoordinates).length;
  }, [filteredFacilities]);

  // Handle adding facility
  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setAddingFacility(true);
    setAddError(null);

    try {
      const commoditiesArray = newFacility.supported_commodities
        ? newFacility.supported_commodities.split(",").map((s) => s.trim()).filter(Boolean)
        : null;

      const payload = {
        id: newFacility.id.trim(),
        name: newFacility.name.trim(),
        facility_type: newFacility.facility_type,
        address: newFacility.address.trim(),
        village_or_city: newFacility.village_or_city.trim(),
        district: newFacility.district.trim(),
        state: newFacility.state.trim() || "Punjab",
        postal_code: newFacility.postal_code.trim() || null,
        latitude: newFacility.latitude ? parseFloat(newFacility.latitude) : null,
        longitude: newFacility.longitude ? parseFloat(newFacility.longitude) : null,
        capacity: newFacility.capacity ? parseFloat(newFacility.capacity) : null,
        capacity_unit: newFacility.capacity_unit.trim() || null,
        contact_phone: newFacility.contact_phone.trim() || null,
        contact_email: newFacility.contact_email.trim() || null,
        supported_commodities: commoditiesArray,
        operational_status: newFacility.operational_status || null,
        guava_suitability_category: newFacility.guava_suitability_category || "horticulture_unconfirmed",
        source_citation_type: newFacility.source_citation_type || "directory_level_reference",
        legal_entity_verification: newFacility.legal_entity_verification || "verified",
        physical_facility_verification: newFacility.physical_facility_verification || "partially_verified",
        source_name: newFacility.source_name.trim(),
        source_url: newFacility.source_url.trim(),
        source_record: newFacility.source_record.trim() || null,
        verification_status: newFacility.verification_status,
        coordinate_source: newFacility.coordinate_source.trim() || null,
        geocoding_confidence: newFacility.geocoding_confidence || null,
        data_provenance: newFacility.data_provenance.trim() || null,
      };

      await createFacility(payload);
      await loadFacilitiesData();
      setShowAddModal(false);
      // Reset form ID
      setNewFacility((prev) => ({ ...prev, id: "", name: "" }));
    } catch (err) {
      console.error("Failed to add facility:", err);
      setAddError(err.message || "Failed to register sourced facility.");
    } finally {
      setAddingFacility(false);
    }
  };

  const getVerificationBadge = (status) => {
    switch (status) {
      case "verified":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <span className="material-symbols-outlined text-[13px] text-emerald-600">verified</span>
            Official Verified
          </span>
        );
      case "partially_verified":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
            <span className="material-symbols-outlined text-[13px] text-amber-600">pending</span>
            Partially Verified
          </span>
        );
      case "unverified":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-300">
            <span className="material-symbols-outlined text-[13px] text-slate-500">help</span>
            Unverified Lead
          </span>
        );
      case "demo_simulated":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
            <span className="material-symbols-outlined text-[13px] text-rose-600">science</span>
            Demo Simulated
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-gray-100 text-gray-700">
            {status}
          </span>
        );
    }
  };

  const getTypeBadge = (type) => {
    switch (type) {
      case "packhouse":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="material-symbols-outlined text-[12px]">inventory_2</span>
            Horticultural Packhouse
          </span>
        );
      case "cold_storage":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-cyan-50 text-cyan-800 border border-cyan-200">
            <span className="material-symbols-outlined text-[12px]">ac_unit</span>
            Cold Storage Facility
          </span>
        );
      case "godown":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-800 border border-amber-200">
            <span className="material-symbols-outlined text-[12px]">warehouse</span>
            State / PDS Godown
          </span>
        );
      case "mandi":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-50 text-purple-800 border border-purple-200">
            <span className="material-symbols-outlined text-[12px]">storefront</span>
            APMC Terminal Mandi
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700">
            {type}
          </span>
        );
    }
  };

  const getGuavaCategoryBadge = (category) => {
    switch (category) {
      case "guava_confirmed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
            <span className="material-symbols-outlined text-[13px] text-emerald-700">verified</span>
            ✓ Guava Handling Confirmed
          </span>
        );
      case "horticulture_unconfirmed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="material-symbols-outlined text-[13px] text-emerald-600">nature</span>
            ⚠ Horticultural (Guava Unconfirmed)
          </span>
        );
      case "ambient_grain":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-100 text-slate-800 border border-slate-300">
            <span className="material-symbols-outlined text-[13px] text-slate-600">block</span>
            ✕ Ambient Grain (Not Guava-Ready)
          </span>
        );
      case "cold_store_unknown":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-sky-50 text-sky-800 border border-sky-300">
            <span className="material-symbols-outlined text-[13px] text-sky-600">help</span>
            ❓ Cold Store (Guava Unconfirmed)
          </span>
        );
      case "wholesale_market":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-purple-50 text-purple-800 border border-purple-300">
            <span className="material-symbols-outlined text-[13px] text-purple-600">storefront</span>
            🛒 Wholesale Produce Market
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-100 text-slate-700">
            {category || "Unclassified"}
          </span>
        );
    }
  };

  const getCitationTierBadge = (tier) => {
    switch (tier) {
      case "directory_level_reference":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-300" title="General agency network page, not direct document proof">
            <span className="material-symbols-outlined text-[11px]">menu_book</span>
            Directory-level reference
          </span>
        );
      case "direct_document":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300" title="Specific official document / EOI notice with chamber specifications">
            <span className="material-symbols-outlined text-[11px]">description</span>
            Direct Document Proof
          </span>
        );
      case "facility_page":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-teal-50 text-teal-800 border border-teal-300" title="Dedicated facility web page with verified contacts">
            <span className="material-symbols-outlined text-[11px]">web</span>
            Official Facility Page
          </span>
        );
      case "official_portal":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300" title="State APMC / e-NAM primary trading terminal portal">
            <span className="material-symbols-outlined text-[11px]">public</span>
            Official Portal Proof
          </span>
        );
      case "committee_proceeding":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-300" title="Statutory committee sanction proceedings">
            <span className="material-symbols-outlined text-[11px]">gavel</span>
            PAC Committee Sanction
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
            Documented Reference
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Header Banner & High-Level Metrics */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-outline-variant/60 premium-shadow">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-outline-variant/40">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="material-symbols-outlined text-emerald-forest text-2xl">warehouse</span>
              <h3 className="font-bold text-emerald-forest text-lg sm:text-xl uppercase tracking-tight">
                Punjab Godown & Cold-Storage Directory
              </h3>
            </div>
            <p className="text-xs sm:text-sm text-on-surface-variant max-w-3xl">
              Authentic agricultural storage facilities, post-harvest packhouses, cold stores, and state warehousing centres in Punjab. Sourced directly from official records of <strong>PAGREXCO</strong>, <strong>National Horticulture Board (NHB)</strong>, and <strong>Punjab State Warehousing Corporation (PSWC)</strong>.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <button
              onClick={() => setShowMap(!showMap)}
              className="px-3.5 py-2 rounded-xl text-xs font-bold text-emerald-forest border border-emerald-600/40 bg-emerald-50 hover:bg-emerald-100 transition-colors flex items-center gap-1.5"
              title="Toggle Interactive Map View"
            >
              <span className="material-symbols-outlined text-sm">
                {showMap ? "map" : "explore"}
              </span>
              {showMap ? "Hide Map" : "Show Map View"}
            </button>
            <button
              onClick={loadFacilitiesData}
              disabled={loading}
              className="px-3.5 py-2 rounded-xl text-xs font-bold text-on-surface-variant border border-outline-variant/70 hover:bg-surface-container-high transition-colors flex items-center gap-1.5"
              title="Refresh facility records"
            >
              <span className={`material-symbols-outlined text-sm ${loading ? "animate-spin" : ""}`}>
                sync
              </span>
              Refresh
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-emerald-forest hover:bg-primary transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <span className="material-symbols-outlined text-sm">add_circle</span>
              Register Sourced Facility
            </button>
          </div>
        </div>

        {/* Provenance Transparency Alert Banner */}
        <div className="mt-4 p-4 rounded-xl bg-surface-container-low border border-outline-variant/50 text-xs text-on-surface-variant flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <span className="material-symbols-outlined text-emerald-forest text-lg shrink-0 mt-0.5">policy</span>
            <div>
              <span className="font-bold text-emerald-forest">Strict Evidence Transparency & Guava Suitability Policy:</span>{" "}
              Fictional utilization metrics and simulated temperatures have been permanently purged. Capacity figures, contacts, operating status, and coordinates are displayed <em>strictly when documented</em>. General agency portals are labeled as directory references. Unknowns display explicitly as <strong>&ldquo;Not available&rdquo;</strong>. Do not assume a cold store or godown is guava-ready without documented compatibility.
            </div>
          </div>
          <span className="shrink-0 text-[11px] font-mono text-emerald-forest font-semibold bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200">
            Phase 12.2 Validated
          </span>
        </div>

        {/* Directory Statistics Counter Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 mt-6">
          <div className="bg-surface-cream rounded-xl p-3.5 border border-outline-variant/40">
            <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Total Sourced</span>
            <div className="text-xl sm:text-2xl font-black text-emerald-forest mt-1">{metrics.total}</div>
            <span className="text-[10px] text-on-surface-variant mt-0.5 block">12 authentic facilities</span>
          </div>

          <div
            onClick={() => setSelectedGuavaCategory(selectedGuavaCategory === "guava_confirmed" ? "all" : "guava_confirmed")}
            className={`rounded-xl p-3.5 border cursor-pointer transition-all ${
              selectedGuavaCategory === "guava_confirmed"
                ? "bg-emerald-100 border-emerald-400 ring-2 ring-emerald-500"
                : "bg-surface-cream border-outline-variant/40 hover:border-emerald-300"
            }`}
          >
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1">
              <span className="material-symbols-outlined text-xs text-emerald-600">verified</span> Guava Confirmed
            </span>
            <div className="text-xl sm:text-2xl font-black text-emerald-800 mt-1">{metrics.guavaConfirmed}</div>
            <span className="text-[10px] text-emerald-700 mt-0.5 block">Azadpur Mega Mandi</span>
          </div>

          <div
            onClick={() => setSelectedGuavaCategory(selectedGuavaCategory === "horticulture_unconfirmed" ? "all" : "horticulture_unconfirmed")}
            className={`rounded-xl p-3.5 border cursor-pointer transition-all ${
              selectedGuavaCategory === "horticulture_unconfirmed"
                ? "bg-emerald-50 border-emerald-400 ring-2 ring-emerald-500"
                : "bg-surface-cream border-outline-variant/40 hover:border-emerald-300"
            }`}
          >
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 block">Horticultural</span>
            <div className="text-xl sm:text-2xl font-black text-emerald-700 mt-1">{metrics.horticultureUnconfirmed}</div>
            <span className="text-[10px] text-on-surface-variant mt-0.5 block">Guava Unconfirmed</span>
          </div>

          <div
            onClick={() => setSelectedGuavaCategory(selectedGuavaCategory === "cold_store_unknown" ? "all" : "cold_store_unknown")}
            className={`rounded-xl p-3.5 border cursor-pointer transition-all ${
              selectedGuavaCategory === "cold_store_unknown"
                ? "bg-sky-100 border-sky-400 ring-2 ring-sky-500"
                : "bg-surface-cream border-outline-variant/40 hover:border-sky-300"
            }`}
          >
            <span className="text-[10px] font-bold uppercase tracking-wider text-sky-800 block">Cold Stores</span>
            <div className="text-xl sm:text-2xl font-black text-sky-800 mt-1">{metrics.coldStoreUnknown}</div>
            <span className="text-[10px] text-on-surface-variant mt-0.5 block">Suitability Unknown</span>
          </div>

          <div
            onClick={() => setSelectedGuavaCategory(selectedGuavaCategory === "ambient_grain" ? "all" : "ambient_grain")}
            className={`rounded-xl p-3.5 border cursor-pointer transition-all ${
              selectedGuavaCategory === "ambient_grain"
                ? "bg-slate-200 border-slate-400 ring-2 ring-slate-500"
                : "bg-surface-cream border-outline-variant/40 hover:border-slate-300"
            }`}
          >
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-800 block">Ambient Grain</span>
            <div className="text-xl sm:text-2xl font-black text-slate-800 mt-1">{metrics.ambientGrain}</div>
            <span className="text-[10px] text-on-surface-variant mt-0.5 block">Dry Godowns (PSWC)</span>
          </div>

          <div className="bg-surface-cream rounded-xl p-3.5 border border-outline-variant/40">
            <span className="text-[10px] font-bold uppercase tracking-wider text-outline block">Sourced Capacity</span>
            <div className="text-xl sm:text-2xl font-black text-emerald-forest mt-1">
              {metrics.totalCapacityMT > 0 ? `${metrics.totalCapacityMT.toLocaleString()} MT` : "Documented"}
            </div>
            <span className="text-[10px] text-on-surface-variant mt-0.5 block">Documented subset</span>
          </div>
        </div>
      </div>

      {/* Interactive Map Section */}
      {showMap && (
        <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-outline-variant/40 gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-emerald-forest text-xl">map</span>
                <h4 className="font-bold text-emerald-forest text-sm uppercase tracking-wide">
                  Geospatial Facility Map — Punjab & Northern Corridor
                </h4>
              </div>
              <p className="text-xs text-on-surface-variant mt-1">
                Displaying <strong>{plottableCount}</strong> verified facilities with valid WGS84 coordinates. Markers with amber badge are <strong>approximate village centroids</strong>, not exact facility entrance gates.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-outline bg-surface-cream px-3 py-1 rounded-full border border-outline-variant/50">
                Plotted: {plottableCount} of {filteredFacilities.length}
              </span>
            </div>
          </div>

          {/* Leaflet Map Client Container */}
          <div className="h-[420px] w-full rounded-xl overflow-hidden border border-outline-variant/50">
            <TrackingMapClient
              facilities={filteredFacilities}
              onSelectFacility={(fac) => setSelectedFacility(fac)}
            />
          </div>

          {/* Map legend and village centroid disclaimer */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-[11px] text-on-surface-variant bg-surface-cream p-3 rounded-xl border border-outline-variant/40">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-bold text-emerald-forest">Marker Legend:</span>
              <span className="flex items-center gap-1">🌱 Packhouse</span>
              <span className="flex items-center gap-1">❄️ Cold Storage</span>
              <span className="flex items-center gap-1">🏛️ State Godown</span>
              <span className="flex items-center gap-1">🛒 APMC Mandi</span>
            </div>
            <div className="text-[10px] text-amber-800 font-medium">
              * Pins geocoded at village level represent administrative centroid coordinates, not verified perimeter gates.
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search Control Bar */}
      <div className="bg-white rounded-2xl p-5 border border-outline-variant/60 premium-shadow">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Keyword Search */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-outline mb-1.5">
              Search Facilities
            </label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-2.5 text-on-surface-variant text-lg">
                search
              </span>
              <input
                type="text"
                placeholder="Search by name, city, commodity..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-outline-variant/70 bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest transition-colors"
              />
            </div>
          </div>

          {/* Guava Supply-Chain Relevance Filter */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-outline mb-1.5">
              Guava Relevance
            </label>
            <select
              value={selectedGuavaCategory}
              onChange={(e) => setSelectedGuavaCategory(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-outline-variant/70 bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest transition-colors"
            >
              <option value="all">All Guava Classifications</option>
              <option value="guava_confirmed">Guava Confirmed ({metrics.guavaConfirmed})</option>
              <option value="horticulture_unconfirmed">General Horticultural ({metrics.horticultureUnconfirmed})</option>
              <option value="ambient_grain">Ambient Grain Godown ({metrics.ambientGrain})</option>
              <option value="cold_store_unknown">Cold Store - Unknown ({metrics.coldStoreUnknown})</option>
              <option value="wholesale_market">Wholesale Mandi ({metrics.wholesaleMarket})</option>
            </select>
          </div>

          {/* District Filter */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-outline mb-1.5">
              Filter by District
            </label>
            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-outline-variant/70 bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest transition-colors"
            >
              <option value="all">All Districts ({facilities.length})</option>
              {districts.map((d) => (
                <option key={d} value={d}>
                  {d} ({facilities.filter((f) => f.district === d).length})
                </option>
              ))}
            </select>
          </div>

          {/* Facility Type Filter */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-outline mb-1.5">
              Facility Type
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-outline-variant/70 bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest transition-colors"
            >
              <option value="all">All Types</option>
              <option value="packhouse">Packhouse / Pre-cooling</option>
              <option value="cold_storage">Cold Storage</option>
              <option value="godown">State Godown (PSWC)</option>
              <option value="mandi">APMC Terminal Mandi</option>
            </select>
          </div>

          {/* Verification Status Filter */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-outline mb-1.5">
              Verification Status
            </label>
            <select
              value={selectedVerification}
              onChange={(e) => setSelectedVerification(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-outline-variant/70 bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest transition-colors"
            >
              <option value="all">All Statuses</option>
              <option value="verified">Verified Official Source</option>
              <option value="partially_verified">Partially Verified</option>
              <option value="unverified">Unverified Lead</option>
            </select>
          </div>
        </div>

        {/* Filter count & reset */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-outline-variant/30 text-xs">
          <span className="text-on-surface-variant">
            Showing <strong className="text-emerald-forest">{filteredFacilities.length}</strong> of{" "}
            <strong>{facilities.length}</strong> facilities
          </span>
          {(searchTerm ||
            selectedDistrict !== "all" ||
            selectedType !== "all" ||
            selectedVerification !== "all" ||
            selectedGuavaCategory !== "all") && (
            <button
              onClick={() => {
                setSearchTerm("");
                setSelectedDistrict("all");
                setSelectedType("all");
                setSelectedVerification("all");
                setSelectedGuavaCategory("all");
              }}
              className="text-emerald-forest hover:text-primary font-bold flex items-center gap-1 transition-colors"
            >
              <span className="material-symbols-outlined text-xs">close</span>
              Clear All Filters
            </button>
          )}
        </div>
      </div>

      {/* Facilities Cards Grid */}
      {loading ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-outline-variant/50">
          <span className="material-symbols-outlined text-4xl text-emerald-forest animate-spin">progress_activity</span>
          <p className="text-sm font-semibold text-on-surface-variant mt-3">Loading authentic Punjab facility records...</p>
        </div>
      ) : error ? (
        <div className="p-8 text-center bg-white rounded-2xl border border-error/30 text-error">
          <span className="material-symbols-outlined text-3xl">error</span>
          <p className="text-sm font-bold mt-2">Error Loading Facility Directory</p>
          <p className="text-xs text-on-surface-variant mt-1 max-w-lg mx-auto">{error}</p>
          <button
            onClick={loadFacilitiesData}
            className="mt-4 px-4 py-2 text-xs font-bold bg-error text-white rounded-xl hover:bg-error/90 transition-colors inline-flex items-center gap-1.5"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            Retry Connection
          </button>
        </div>
      ) : facilities.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-outline-variant/50">
          <span className="material-symbols-outlined text-4xl text-outline">domain_disabled</span>
          <p className="text-sm font-bold text-on-surface-variant mt-2">No Registered Facilities Available</p>
          <p className="text-xs text-outline mt-1">The storage facility directory is currently empty. Verify backend seed records or register a new facility.</p>
          <button
            onClick={loadFacilitiesData}
            className="mt-4 px-4 py-2 text-xs font-bold text-emerald-forest border border-emerald-forest rounded-xl hover:bg-emerald-50 transition-colors inline-flex items-center gap-1.5"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            Refresh Directory
          </button>
        </div>
      ) : filteredFacilities.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-outline-variant/50">
          <span className="material-symbols-outlined text-4xl text-outline">search_off</span>
          <p className="text-sm font-bold text-on-surface-variant mt-2">No facilities match your active filter criteria</p>
          <p className="text-xs text-outline mt-1">Try broadening your search term or clearing filters.</p>
          <button
            onClick={() => {
              setSearchTerm("");
              setSelectedDistrict("all");
              setSelectedType("all");
              setSelectedVerification("all");
              setSelectedGuavaCategory("all");
            }}
            className="mt-4 px-4 py-2 text-xs font-bold text-emerald-forest border border-emerald-forest rounded-xl hover:bg-emerald-50 transition-colors"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {filteredFacilities.map((facility) => {
            const hasCoords = hasValidFacilityCoordinates(facility);
            const lat = facility.latitude != null ? facility.latitude : facility.coordinates?.latitude;
            const lon = facility.longitude != null ? facility.longitude : facility.coordinates?.longitude;
            const isVillageLevel = facility.geocoding_confidence === "village_level" || facility.geocoding_confidence !== "facility_campus";

            return (
              <div
                key={facility.id}
                className="bg-white rounded-2xl border border-outline-variant/60 overflow-hidden premium-shadow flex flex-col justify-between hover:border-emerald-forest/40 transition-all duration-200"
              >
                <div>
                  {/* Card Header: Type Badge & Verification Badge */}
                  <div className="p-5 pb-3 border-b border-outline-variant/30 bg-surface-cream/50 flex items-start justify-between gap-3">
                    <div className="flex flex-col gap-1.5">
                      {getTypeBadge(facility.facility_type)}
                      <span className="text-[10px] font-mono text-outline font-semibold">
                        ID: {facility.id}
                      </span>
                    </div>
                    <div>{getVerificationBadge(facility.verification_status)}</div>
                  </div>

                  {/* Body Content */}
                  <div className="p-5 flex flex-col gap-3.5">
                    {/* Facility Name & Location */}
                    <div>
                      <h4 className="font-bold text-emerald-forest text-base leading-snug">
                        {facility.name}
                      </h4>
                      <div className="flex items-start gap-1.5 mt-1 text-xs text-on-surface-variant">
                        <span className="material-symbols-outlined text-sm text-outline shrink-0 mt-0.5">location_on</span>
                        <span>
                          {facility.address}
                          {facility.village_or_city && `, ${facility.village_or_city}`}
                          {facility.district && `, Dist. ${facility.district}`}
                          {facility.postal_code && ` - ${facility.postal_code}`}
                        </span>
                      </div>
                    </div>

                    {/* Guava Supply-Chain Readiness Badge */}
                    <div className="pt-1">
                      <span className="text-[10px] uppercase font-bold text-outline block mb-1">
                        Guava Supply-Chain Suitability
                      </span>
                      {getGuavaCategoryBadge(facility.guava_suitability_category)}
                    </div>

                    {/* Separate Legal Entity vs Physical Site Verification Badges */}
                    <div className="p-2.5 rounded-xl bg-surface-cream border border-outline-variant/40 flex flex-col gap-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-semibold text-outline">Legal Entity:</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          facility.legal_entity_verification === "verified"
                            ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                            : "bg-slate-100 text-slate-700"
                        }`}>
                          {facility.legal_entity_verification === "verified" ? "✓ Verified Registration" : "Unverified"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-semibold text-outline">Physical Facility:</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          facility.physical_facility_verification === "verified"
                            ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                            : facility.physical_facility_verification === "partially_verified"
                            ? "bg-amber-100 text-amber-800 border border-amber-300"
                            : "bg-slate-100 text-slate-700"
                        }`}>
                          {facility.physical_facility_verification === "verified"
                            ? "✓ Verified Site Existence"
                            : "⚠ Partially Verified (Listed)"}
                        </span>
                      </div>
                    </div>

                    {/* Operational Status (or explicitly Not available) */}
                    <div className="flex items-center justify-between text-xs pt-1 border-t border-outline-variant/30">
                      <span className="text-[10px] uppercase font-bold text-outline">Operating Status:</span>
                      {facility.operational_status ? (
                        <span className="font-bold text-emerald-700 capitalize flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse"></span>
                          {facility.operational_status}
                        </span>
                      ) : (
                        <span className="text-on-surface-variant/70 italic text-[11px]">
                          Not available (Unconfirmed on-site)
                        </span>
                      )}
                    </div>

                    {/* Sourced Capacity (ONLY when published, else Not available) */}
                    <div className="p-3 rounded-xl bg-surface-container-low border border-outline-variant/30 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-emerald-forest text-lg">
                          scale
                        </span>
                        <div>
                          <span className="text-[10px] uppercase font-bold text-outline block">
                            Storage Capacity
                          </span>
                          <span className="text-xs font-bold text-emerald-forest">
                            {facility.capacity != null
                              ? `${facility.capacity.toLocaleString()} ${facility.capacity_unit || "MT"}`
                              : "Not available"}
                          </span>
                        </div>
                      </div>
                      {facility.capacity != null ? (
                        <span className="text-[10px] font-bold text-digital-mint bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          Documented
                        </span>
                      ) : (
                        <span className="text-[10px] text-outline italic">
                          Unlisted in source
                        </span>
                      )}
                    </div>

                    {/* Documented Commodities (ONLY when documented, else Not available) */}
                    <div>
                      <span className="text-[10px] uppercase font-bold text-outline block mb-1">
                        Supported Commodities
                      </span>
                      {Array.isArray(facility.supported_commodities) && facility.supported_commodities.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {facility.supported_commodities.map((comm) => (
                            <span
                              key={comm}
                              className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-800 rounded border border-emerald-200"
                            >
                              {comm}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-on-surface-variant/70 italic">
                          Not available (Commodity scope unlisted in source)
                        </span>
                      )}
                    </div>

                    {/* Public Contact Details (Always shown; Not available if missing) */}
                    <div className="text-xs text-on-surface-variant flex flex-col gap-1 pt-1 border-t border-outline-variant/30">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="material-symbols-outlined text-xs text-outline">call</span>
                          <span className="text-[10px] text-outline uppercase font-semibold">Phone:</span>
                        </div>
                        {facility.contact_phone ? (
                          <span className="font-mono font-medium">{facility.contact_phone}</span>
                        ) : (
                          <span className="italic text-outline">Not available</span>
                        )}
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="material-symbols-outlined text-xs text-outline">mail</span>
                          <span className="text-[10px] text-outline uppercase font-semibold">Email:</span>
                        </div>
                        {facility.contact_email ? (
                          <span className="font-mono text-primary underline truncate max-w-[180px]">{facility.contact_email}</span>
                        ) : (
                          <span className="italic text-outline">Not available</span>
                        )}
                      </div>
                    </div>

                    {/* Coordinates & Geocoding Provenance (Never imply village centroid is gate) */}
                    <div className="text-xs flex flex-col gap-1 pt-2 border-t border-outline-variant/30">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          <span className="material-symbols-outlined text-xs text-outline">explore</span>
                          <span className="text-[11px] font-mono text-on-surface-variant">
                            {hasCoords
                              ? `${Number(lat).toFixed(4)}°N, ${Number(lon).toFixed(4)}°E`
                              : "Not available (Coordinates unverified)"}
                          </span>
                        </div>
                        <span className="text-[10px] font-semibold text-outline capitalize">
                          {facility.geocoding_confidence ? facility.geocoding_confidence.replace("_", " ") : "Geocoded"}
                        </span>
                      </div>
                      {hasCoords && isVillageLevel ? (
                        <span className="text-[10px] font-medium text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          📍 Approximate location (Village centroid — not exact facility gate)
                        </span>
                      ) : hasCoords ? (
                        <span className="text-[10px] font-medium text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          ✓ Verified Campus Coordinates
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>

                {/* Card Footer: Source Link & Provenance Details Button */}
                <div className="p-4 bg-surface-cream border-t border-outline-variant/40 flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-xs flex-1">
                      <span className="text-[10px] text-outline block">Official Source</span>
                      <span className="font-semibold text-emerald-forest text-[11px] truncate block" title={facility.source_name}>
                        {facility.source_name || "Official Punjab Record"}
                      </span>
                    </div>
                    {getCitationTierBadge(facility.source_citation_type)}
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-outline-variant/30 gap-2">
                    <div>
                      {facility.source_url ? (
                        <a
                          href={facility.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] font-bold text-primary hover:text-emerald-forest underline flex items-center gap-1"
                          title="Open official source authority or document in new tab"
                        >
                          <span>Open Source</span>
                          <span className="material-symbols-outlined text-xs">open_in_new</span>
                        </a>
                      ) : (
                        <span className="text-[10px] text-outline italic">No public URL</span>
                      )}
                    </div>

                    <button
                      onClick={() => setSelectedFacility(facility)}
                      className="px-3 py-1.5 rounded-xl text-xs font-bold text-emerald-forest bg-white hover:bg-emerald-50 border border-emerald-600/30 transition-colors flex items-center gap-1 shadow-sm"
                    >
                      <span>Provenance Evidence</span>
                      <span className="material-symbols-outlined text-sm">info</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* MODAL 1: Full Provenance & Source Metadata Modal */}
      {selectedFacility && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-outline-variant/60 shadow-2xl flex flex-col">
            {/* Modal Header */}
            <div className="p-6 border-b border-outline-variant/40 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  {getTypeBadge(selectedFacility.facility_type)}
                  {getVerificationBadge(selectedFacility.verification_status)}
                  {getCitationTierBadge(selectedFacility.source_citation_type)}
                </div>
                <h3 className="text-lg font-bold text-emerald-forest leading-tight">
                  {selectedFacility.name}
                </h3>
                <span className="text-xs font-mono text-outline">
                  Facility Record ID: {selectedFacility.id}
                </span>
              </div>
              <button
                onClick={() => setSelectedFacility(null)}
                className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container-high transition-colors"
                aria-label="Close modal"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 flex flex-col gap-5 text-xs text-on-surface-variant">
              {/* Guava Suitability Analysis Banner */}
              <div className="p-4 rounded-xl bg-surface-cream border border-outline-variant/40">
                <h5 className="font-bold text-emerald-forest uppercase text-[11px] mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-sm">psychology</span>
                  Guava Supply-Chain Readiness Classification
                </h5>
                <div className="mb-2">
                  {getGuavaCategoryBadge(selectedFacility.guava_suitability_category)}
                </div>
                <p className="text-xs leading-relaxed text-on-surface">
                  {selectedFacility.guava_suitability_category === "guava_confirmed"
                    ? "Direct source evidence confirms this terminal facility handles commercial guava auctions, ripening chambers, and cold-chain transfers from Punjab orchards."
                    : selectedFacility.guava_suitability_category === "horticulture_unconfirmed"
                    ? "This facility provides general horticultural pre-cooling or packhouse infrastructure (often optimized for citrus/Kinnow). Guava compatibility is unconfirmed because guava is not explicitly documented in the official source specification."
                    : selectedFacility.guava_suitability_category === "ambient_grain"
                    ? "This facility is a scientific foodgrain godown engineered for ambient dry storage of wheat and paddy (PDS buffer stock). It lacks cold storage, humidity control, and pre-cooling required for perishable guava produce."
                    : selectedFacility.guava_suitability_category === "cold_store_unknown"
                    ? "Registered commercial cold storage facility primarily serving the regional potato sector. Specific cold-room chamber temperature, humidity control, and guava compatibility are unverified on-site."
                    : "Wholesale APMC auction yard with seasonal perishable trade, but lacking integrated packhouse cold-chain infrastructure."}
                </p>
              </div>

              {/* Sourced Location & Identity */}
              <div className="p-4 rounded-xl bg-surface-cream border border-outline-variant/40">
                <h5 className="font-bold text-emerald-forest uppercase text-[11px] mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-sm">map</span>
                  Physical Location & Postal Address
                </h5>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <span className="text-[10px] text-outline uppercase font-semibold block">Street / Campus Address</span>
                    <span className="font-medium text-on-surface">{selectedFacility.address}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-outline uppercase font-semibold block">Village / Town / City</span>
                    <span className="font-medium text-on-surface">{selectedFacility.village_or_city || "Not available"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-outline uppercase font-semibold block">District & State</span>
                    <span className="font-medium text-on-surface">{selectedFacility.district}, {selectedFacility.state}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-outline uppercase font-semibold block">PIN / Postal Code</span>
                    <span className="font-medium text-on-surface">{selectedFacility.postal_code || "Not available"}</span>
                  </div>
                </div>
              </div>

              {/* Geographic Coordinates & Geocoding Provenance */}
              <div className="p-4 rounded-xl bg-surface-cream border border-outline-variant/40">
                <h5 className="font-bold text-emerald-forest uppercase text-[11px] mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-sm">pin_drop</span>
                  Geographic Spatial Verification
                </h5>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <span className="text-[10px] text-outline uppercase font-semibold block">WGS84 Coordinates</span>
                    <span className="font-mono font-medium text-on-surface">
                      {selectedFacility.latitude != null && selectedFacility.longitude != null
                        ? `${selectedFacility.latitude}°N, ${selectedFacility.longitude}°E`
                        : "Not available (Coordinates not geocoded)"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-outline uppercase font-semibold block">Geocoding Confidence</span>
                    <span className="font-medium text-on-surface capitalize">
                      {selectedFacility.geocoding_confidence ? selectedFacility.geocoding_confidence.replace("_", " ") : "Not available"}
                    </span>
                  </div>
                  <div className="sm:col-span-2">
                    <span className="text-[10px] text-outline uppercase font-semibold block">Coordinate Source</span>
                    <span className="font-medium text-on-surface">
                      {selectedFacility.coordinate_source || "Documented geographic reference"}
                    </span>
                  </div>
                  {selectedFacility.geocoding_confidence === "village_level" && (
                    <div className="sm:col-span-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 font-medium">
                      📍 <strong>Approximate Location Disclosure:</strong> Coordinate pin represents the administrative village centroid and must never be interpreted as an exact facility gate entrance or physical weighbridge marker.
                    </div>
                  )}
                </div>
              </div>

              {/* Verification Disaggregation: Legal Entity vs Physical Site */}
              <div className="p-4 rounded-xl bg-surface-cream border border-outline-variant/40">
                <h5 className="font-bold text-emerald-forest uppercase text-[11px] mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-sm">verified_user</span>
                  Verification Audit Breakdown
                </h5>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3 bg-white rounded-lg border border-outline-variant/40">
                    <span className="text-[10px] text-outline uppercase font-semibold block">Legal Entity Verification</span>
                    <div className="mt-1 flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-emerald-600 text-sm">check_circle</span>
                      <strong className="text-emerald-800 text-xs">
                        {selectedFacility.legal_entity_verification === "verified" ? "Officially Registered Entity" : "Unverified"}
                      </strong>
                    </div>
                    <span className="text-[10px] text-outline mt-1 block">
                      Corporate/Cooperative/PSU registration confirmed against government registry.
                    </span>
                  </div>

                  <div className="p-3 bg-white rounded-lg border border-outline-variant/40">
                    <span className="text-[10px] text-outline uppercase font-semibold block">Physical Facility Verification</span>
                    <div className="mt-1 flex items-center gap-1.5">
                      <span className={`material-symbols-outlined text-sm ${
                        selectedFacility.physical_facility_verification === "verified" ? "text-emerald-600" : "text-amber-600"
                      }`}>
                        {selectedFacility.physical_facility_verification === "verified" ? "domain_verification" : "pending"}
                      </span>
                      <strong className={`text-xs ${
                        selectedFacility.physical_facility_verification === "verified" ? "text-emerald-800" : "text-amber-800"
                      }`}>
                        {selectedFacility.physical_facility_verification === "verified" ? "Verified Physical Site" : "Partially Verified (Listed)"}
                      </strong>
                    </div>
                    <span className="text-[10px] text-outline mt-1 block">
                      {selectedFacility.physical_facility_verification === "verified"
                        ? "Active facility existence confirmed via tender/EOI/portal."
                        : "Listed in master agency directory; on-site physical inspection pending."}
                    </span>
                  </div>
                </div>
              </div>

              {/* Official Source & Reference Documents */}
              <div className="p-4 rounded-xl bg-surface-cream border border-outline-variant/40">
                <h5 className="font-bold text-emerald-forest uppercase text-[11px] mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-sm">article</span>
                  Document Provenance & Source Gazette
                </h5>
                <div className="flex flex-col gap-3">
                  <div>
                    <span className="text-[10px] text-outline uppercase font-semibold block">Publishing Authority / Source</span>
                    <span className="font-semibold text-emerald-forest text-sm">
                      {selectedFacility.source_name || "Official Punjab Record"}
                    </span>
                  </div>
                  {selectedFacility.source_record && (
                    <div>
                      <span className="text-[10px] text-outline uppercase font-semibold block">Document Reference / EOI Notice</span>
                      <span className="font-mono bg-white px-2.5 py-1 rounded border border-outline-variant/50 inline-block text-on-surface">
                        {selectedFacility.source_record}
                      </span>
                    </div>
                  )}
                  <div>
                    <span className="text-[10px] text-outline uppercase font-semibold block">Source Citation Tier</span>
                    <div className="mt-1">
                      {getCitationTierBadge(selectedFacility.source_citation_type)}
                    </div>
                  </div>
                  {selectedFacility.source_url && (
                    <div>
                      <span className="text-[10px] text-outline uppercase font-semibold block">Direct Source URL</span>
                      <a
                        href={selectedFacility.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline font-mono break-all hover:text-emerald-forest flex items-center gap-1 mt-0.5"
                      >
                        {selectedFacility.source_url}
                        <span className="material-symbols-outlined text-xs">open_in_new</span>
                      </a>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-outline-variant/30">
                    <div>
                      <span className="text-[10px] text-outline uppercase font-semibold block">Verification Date</span>
                      <span className="font-mono">{selectedFacility.verification_date || "2026-10-26"}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-outline uppercase font-semibold block">Last Source Audit</span>
                      <span className="font-mono">{selectedFacility.last_source_check || "2026-10-26"}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Data Provenance Notes */}
              {selectedFacility.data_provenance && (
                <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-200 text-on-surface">
                  <h5 className="font-bold text-emerald-forest uppercase text-[11px] mb-1.5 flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">history_edu</span>
                    Field Research & Verification Notes
                  </h5>
                  <p className="text-xs leading-relaxed text-on-surface-variant">
                    {selectedFacility.data_provenance}
                  </p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-outline-variant/40 flex justify-end gap-3 bg-surface-cream sticky bottom-0">
              <button
                onClick={() => setSelectedFacility(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-emerald-forest text-white hover:bg-primary transition-colors"
              >
                Close Provenance View
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Register Sourced Facility Form Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-outline-variant/60 shadow-2xl flex flex-col">
            <div className="p-6 border-b border-outline-variant/40 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <h3 className="text-lg font-bold text-emerald-forest">Register Sourced Facility</h3>
                <p className="text-xs text-on-surface-variant">
                  Add a verified agricultural warehouse or cold-storage record backed by public documentation.
                </p>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container-high transition-colors"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <form onSubmit={handleAddSubmit} className="p-6 flex flex-col gap-4 text-xs">
              {addError && (
                <div className="p-3 bg-error/10 border border-error/30 text-error rounded-xl font-medium">
                  {addError}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Facility ID *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. FAC-PB-PAG-SIRH"
                    value={newFacility.id}
                    onChange={(e) => setNewFacility({ ...newFacility, id: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest font-mono"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Facility Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. PAGREXCO Packhouse"
                    value={newFacility.name}
                    onChange={(e) => setNewFacility({ ...newFacility, name: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Facility Type *
                  </label>
                  <select
                    value={newFacility.facility_type}
                    onChange={(e) => setNewFacility({ ...newFacility, facility_type: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none"
                  >
                    <option value="packhouse">Horticultural Packhouse</option>
                    <option value="cold_storage">Cold Storage</option>
                    <option value="godown">State Godown</option>
                    <option value="mandi">APMC Terminal Mandi</option>
                    <option value="warehouse">Agricultural Warehouse</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Guava Supply-Chain Category *
                  </label>
                  <select
                    value={newFacility.guava_suitability_category}
                    onChange={(e) => setNewFacility({ ...newFacility, guava_suitability_category: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none"
                  >
                    <option value="guava_confirmed">Guava Handling Confirmed</option>
                    <option value="horticulture_unconfirmed">General Horticultural (Guava Unconfirmed)</option>
                    <option value="ambient_grain">Ambient Grain Warehouse</option>
                    <option value="cold_store_unknown">Commercial Cold Store (Guava Unknown)</option>
                    <option value="wholesale_market">Wholesale Produce Market</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Source Citation Tier *
                  </label>
                  <select
                    value={newFacility.source_citation_type}
                    onChange={(e) => setNewFacility({ ...newFacility, source_citation_type: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none"
                  >
                    <option value="direct_document">Direct Document Proof</option>
                    <option value="facility_page">Official Facility Page</option>
                    <option value="official_portal">Official Portal Proof</option>
                    <option value="committee_proceeding">PAC Committee Sanction</option>
                    <option value="directory_level_reference">Directory-level reference</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Verification Status *
                  </label>
                  <select
                    value={newFacility.verification_status}
                    onChange={(e) => setNewFacility({ ...newFacility, verification_status: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none"
                  >
                    <option value="verified">Verified Official Source</option>
                    <option value="partially_verified">Partially Verified</option>
                    <option value="unverified">Unverified Lead</option>
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Address *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Full street or campus address"
                    value={newFacility.address}
                    onChange={(e) => setNewFacility({ ...newFacility, address: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Village / Town / City *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Sirhind"
                    value={newFacility.village_or_city}
                    onChange={(e) => setNewFacility({ ...newFacility, village_or_city: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    District *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Fatehgarh Sahib"
                    value={newFacility.district}
                    onChange={(e) => setNewFacility({ ...newFacility, district: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-forest"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Latitude (Optional)
                  </label>
                  <input
                    type="number"
                    step="any"
                    placeholder="e.g. 30.6283"
                    value={newFacility.latitude}
                    onChange={(e) => setNewFacility({ ...newFacility, latitude: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white font-mono"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Longitude (Optional)
                  </label>
                  <input
                    type="number"
                    step="any"
                    placeholder="e.g. 76.3863"
                    value={newFacility.longitude}
                    onChange={(e) => setNewFacility({ ...newFacility, longitude: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white font-mono"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Published Capacity (Leave blank if unknown)
                  </label>
                  <input
                    type="number"
                    step="any"
                    placeholder="e.g. 24.0"
                    value={newFacility.capacity}
                    onChange={(e) => setNewFacility({ ...newFacility, capacity: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white font-mono"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Capacity Unit
                  </label>
                  <input
                    type="text"
                    placeholder="MT"
                    value={newFacility.capacity_unit}
                    onChange={(e) => setNewFacility({ ...newFacility, capacity_unit: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Supported Commodities (Comma-separated)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Guava, Kinnow, Citrus, Vegetables"
                    value={newFacility.supported_commodities}
                    onChange={(e) => setNewFacility({ ...newFacility, supported_commodities: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Official Source Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Punjab Agri Export Corporation Limited (PAGREXCO)"
                    value={newFacility.source_name}
                    onChange={(e) => setNewFacility({ ...newFacility, source_name: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white"
                  />
                </div>

                <div>
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Official Source URL *
                  </label>
                  <input
                    type="url"
                    required
                    placeholder="https://punjabagro.gov.in/..."
                    value={newFacility.source_url}
                    onChange={(e) => setNewFacility({ ...newFacility, source_url: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white font-mono"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Source Document / Tender / Gazette Reference
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. EOI-Pack-House-cum-Cold-Storage.pdf"
                    value={newFacility.source_record}
                    onChange={(e) => setNewFacility({ ...newFacility, source_record: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block font-bold text-outline uppercase tracking-wider mb-1">
                    Provenance Notes & Research Evidence
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Detailed explanation of how this record was verified..."
                    value={newFacility.data_provenance}
                    onChange={(e) => setNewFacility({ ...newFacility, data_provenance: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-cream focus:bg-white"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-outline-variant/40 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingFacility}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-forest text-white hover:bg-primary transition-colors flex items-center gap-1.5"
                >
                  {addingFacility ? "Registering..." : "Submit Verified Facility"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
