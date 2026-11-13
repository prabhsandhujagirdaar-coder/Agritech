"use client";
import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Sidebar from "../../components/Sidebar";
import ShipmentsTracking from "../../components/ShipmentsTracking";
import FacilityDirectory from "../../components/FacilityDirectory";
import RoleSelectionModal, { SUPPORTED_ROLES, ROLE_DEFAULT_TABS } from "../../components/RoleSelectionModal";
import OrderPurchaseModal from "../../components/OrderPurchaseModal";
import FarmerInventoryManager from "../../components/FarmerInventoryManager";
import {
  CLASS_LABELS,
  GUAVA_CLASS_LABELS,
  BANANA_CLASS_LABELS,
  SUPPORTED_FRUITS,
  getClassIndex,
  getRipenessLabel,
  formatConfidence,
  UNCERTAINTY_THRESHOLDS,
  checkPredictionUncertainty,
} from "../../lib/constants";
import { fetchMarketplaceListings, fetchDemoOrders, createShipment } from "../../lib/api";
import {
  ROLE_KEYS,
  ROLES_CONFIG,
  normalizeRoleId,
  getRoleConfig,
  isTabAllowedForRole,
} from "../../lib/roleConfig";

function DashboardContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tabParam = searchParams.get("tab") || "analyze";

  const [activeTab, setActiveTab] = useState(tabParam);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [naturalImgDimensions, setNaturalImgDimensions] = useState({ width: 0, height: 0 });
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);
  
  // Multi-Fruit Inspection Mode & Target State
  const [inspectionMode, setInspectionMode] = useState("manual"); // "manual" | "auto"
  const [selectedFruit, setSelectedFruit] = useState("guava"); // "guava" | "banana" | "apple" | "mango"
  
  // Settings Role State & Initial Role Selection Modal
  const [activeRole, setActiveRole] = useState("Farmer");
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [canDismissRoleModal, setCanDismissRoleModal] = useState(true);
  const [hasChosenRole, setHasChosenRole] = useState(false);

  // Active role configuration and permission check
  const roleConfig = getRoleConfig(activeRole);
  const isAllowed = isTabAllowedForRole(activeRole, activeTab);

  // Marketplace Listings & Orders State
  const [marketplaceListings, setMarketplaceListings] = useState([]);
  const [loadingListings, setLoadingListings] = useState(false);
  const [selectedListingForOrder, setSelectedListingForOrder] = useState(null);
  const [demoOrders, setDemoOrders] = useState([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [marketplaceViewMode, setMarketplaceViewMode] = useState("catalog"); // "catalog" | "orders"

  // Shipment Association from Inspection
  const [associatingShipment, setAssociatingShipment] = useState(false);
  const [shipmentAssociateSuccess, setShipmentAssociateSuccess] = useState(null);
  const [shipmentAssociateError, setShipmentAssociateError] = useState(null);

  // Health Status state (ML API + Backend)
  const [healthData, setHealthData] = useState({
    status: "checking",
    api_status: "checking",
    model: "",
    model_version: "2.0.0",
    device: "",
    model_available: false,
    model_status: "checking",
    target_crop: "guava",
    message: "",
    latencyMs: null,
    backend: { status: "checking", api_status: "checking", latencyMs: null },
  });

  // Check saved role on mount, or prompt initial role selector
  useEffect(() => {
    if (typeof window !== "undefined") {
      const currentTab = searchParams.get("tab");
      const roleParam = searchParams.get("role");
      let resolvedRole = null;
      if (roleParam) {
        resolvedRole = normalizeRoleId(roleParam);
        setActiveRole(resolvedRole);
        localStorage.setItem("agrichain_active_role", resolvedRole);
        setShowRoleModal(false);
        setCanDismissRoleModal(true);
        setHasChosenRole(true);
      } else {
        const savedRole = localStorage.getItem("agrichain_active_role");
        if (savedRole) {
          resolvedRole = normalizeRoleId(savedRole);
          setActiveRole(resolvedRole);
          setShowRoleModal(false);
          setCanDismissRoleModal(true);
          setHasChosenRole(true);
        } else {
          setShowRoleModal(true);
          setCanDismissRoleModal(false);
          setHasChosenRole(false);
        }
      }

      if (resolvedRole) {
        const cfg = getRoleConfig(resolvedRole);
        if (!currentTab) {
          setActiveTab(cfg.defaultTab);
        } else {
          setActiveTab(currentTab);
        }
      }
    }
  }, [searchParams]);

  // Update tab in URL when changed
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setMobileMenuOpen(false);
    router.push(`/dashboard?tab=${tabId}`);
  };

  const handleRoleSelect = (newRoleId, defaultTab) => {
    const canonical = normalizeRoleId(newRoleId);
    setActiveRole(canonical);
    if (typeof window !== "undefined") {
      localStorage.setItem("agrichain_active_role", canonical);
    }
    setShowRoleModal(false);
    setCanDismissRoleModal(true);
    setHasChosenRole(true);
    const cfg = getRoleConfig(canonical);
    const targetTab = defaultTab || cfg.defaultTab;
    handleTabChange(targetTab);
  };

  const handleAssociateShipment = async (result) => {
    if (!result) return;
    setAssociatingShipment(true);
    setShipmentAssociateSuccess(null);
    setShipmentAssociateError(null);

    try {
      const fruitName = (result.target_fruit || "Produce").charAt(0).toUpperCase() + (result.target_fruit || "Produce").slice(1);
      let grade = "Standard Verified";
      if (result.prediction?.stage) {
        grade = result.prediction.stage;
      } else if (result.prediction?.predicted_class) {
        grade = result.prediction.predicted_class;
      } else if (result.detection?.instances_detected != null) {
        grade = `${result.detection.instances_detected} Apples Detected (Count Only)`;
      } else if (result.status === "unavailable") {
        grade = "Intake Pending (Model Gated)";
      }

      const payload = {
        produce_type: `${fruitName} (${grade})`,
        origin: "Abohar Regional Packhouse, Punjab",
        destination: "Azadpur Terminal Mandi, Delhi",
        quantity: 1250.0,
        status: "in_transit",
        origin_facility_id: "FAC-PB-ABO-01",
        destination_facility_id: "FAC-DL-AZD-01",
        tracking_mode: "simulated",
        telemetry_mode: "simulated",
        quality_grade: grade,
        inspection_verdict: {
          target_fruit: result.target_fruit,
          task_type: result.task_type,
          confidence: result.prediction?.confidence ?? (result.detection ? 0.9 : 0.0),
          details: result.prediction || result.detection || { status: result.status },
          inspected_at: new Date().toISOString(),
        },
      };

      const newShipment = await createShipment(payload);
      setShipmentAssociateSuccess(`Created & linked shipment ${newShipment.id}! Navigating to live tracking...`);
      setTimeout(() => {
        handleTabChange("tracking");
      }, 1200);
    } catch (err) {
      setShipmentAssociateError(err.message || "Failed to associate shipment");
    } finally {
      setAssociatingShipment(false);
    }
  };

  useEffect(() => {
    if (tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [tabParam, activeTab]);

  // Fetch health data for System Status
  const fetchHealth = async () => {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      setHealthData(data);
    } catch (err) {
      setHealthData({
        status: "offline",
        api_status: "offline",
        model: "N/A",
        model_version: null,
        device: "N/A",
        model_available: false,
        model_status: "unavailable",
        target_crop: "guava",
        latencyMs: null,
        backend: { status: "offline", api_status: "offline", latencyMs: null },
        error: err.message,
      });
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  // Load marketplace produce listings & recorded demo orders
  const loadMarketplaceData = async () => {
    setLoadingListings(true);
    try {
      const listings = await fetchMarketplaceListings();
      setMarketplaceListings(listings);
    } catch {
      // Sourced fallback seed data ensuring marketplace remains demo-interactive
      setMarketplaceListings([
        {
          id: "LST-GUA-001",
          title: "Guava Premium Crate (Ripe)",
          variety: "Allahabad Safeda",
          crop: "guava",
          ripeness_stage: "Ripe",
          ai_verified: true,
          softmax_score: 0.982,
          origin_facility_id: "FAC-PB-ABO-01",
          origin_name: "Farm Gate D (Abohar Cluster)",
          available_crates: 120,
          crate_weight_kg: 20.0,
          price_per_crate_inr: 1200.0,
          image_url: "https://images.unsplash.com/photo-1536511132770-e5058c7e8c46?w=600&auto=format&fit=crop&q=60",
          notes: "Certified harvest maturity evaluated with ResNet18 model v2.0.0. Ready for retail distribution.",
        },
        {
          id: "LST-GUA-002",
          title: "Guava Transit Crate (Mature Green)",
          variety: "Hisar Safeda / Shweta",
          crop: "guava",
          ripeness_stage: "Mature Green",
          ai_verified: true,
          softmax_score: 0.875,
          origin_facility_id: "FAC-PB-PAG-BARA",
          origin_name: "Packhouse Zone E (Bara Farm Hub)",
          available_crates: 160,
          crate_weight_kg: 20.0,
          price_per_crate_inr: 1050.0,
          image_url: "https://images.unsplash.com/photo-1536511132770-e5058c7e8c46?w=600&auto=format&fit=crop&q=60",
          notes: "Mature green firmness optimal for multi-day long-distance cold-chain transport.",
        },
        {
          id: "LST-GUA-003",
          title: "Guava Harvest Crate (Green / Breaker)",
          variety: "Lalit / Regional Sindhi",
          crop: "guava",
          ripeness_stage: "Green",
          ai_verified: true,
          softmax_score: 0.914,
          origin_facility_id: "FAC-PB-FAZ-01",
          origin_name: "Abohar Post-Harvest Center (Fazilka)",
          available_crates: 200,
          crate_weight_kg: 20.0,
          price_per_crate_inr: 950.0,
          image_url: "https://images.unsplash.com/photo-1536511132770-e5058c7e8c46?w=600&auto=format&fit=crop&q=60",
          notes: "Breaker stage fruit for scheduled ripening in controlled atmosphere chambers.",
        },
      ]);
    } finally {
      setLoadingListings(false);
    }

    setLoadingOrders(true);
    try {
      const orders = await fetchDemoOrders();
      setDemoOrders(orders);
    } catch {
      setDemoOrders([]);
    } finally {
      setLoadingOrders(false);
    }
  };

  useEffect(() => {
    if (activeTab === "marketplace") {
      loadMarketplaceData();
    }
  }, [activeTab]);

  // Handle file select
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setAnalysisResult(null);
      setAnalysisError(null);
    }
  };

  // Run AI analysis
  const runAnalysis = async (overrideFruit = null, overrideMode = null) => {
    if (!selectedFile) return;
    setAnalyzing(true);
    setAnalysisError(null);
    setAnalysisResult(null);

    const mode = overrideMode || inspectionMode;
    const fruit = overrideFruit || selectedFruit;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("mode", mode);
    formData.append("fruit", fruit);

    try {
      const res = await fetch(`/api/inspect?mode=${encodeURIComponent(mode)}&fruit=${encodeURIComponent(fruit)}`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Multi-fruit inspection server error");
      }

      const data = await res.json();
      setAnalysisResult(data);
    } catch (err) {
      setAnalysisError(err.message || "Failed to run multi-fruit inspection");
    } finally {
      setAnalyzing(false);
    }
  };

  // Helper for color-coding classes
  const getClassColor = (className) => {
    const idx = getClassIndex(className);
    if (idx === 0) return "bg-blue-500 text-white";
    if (idx === 1) return "bg-amber-500 text-white";
    if (idx === 2) return "bg-digital-mint text-white";
    return "bg-primary text-white";
  };

  // First-time role onboarding backdrop (prevents unauthorized dashboard exposure)
  if (!hasChosenRole) {
    return (
      <div className="min-h-screen w-full bg-surface-container-low flex items-center justify-center p-6 relative overflow-hidden">
        <div className="text-center max-w-lg z-10 animate-fade-in">
          <div className="w-20 h-20 rounded-3xl bg-emerald-forest text-white flex items-center justify-center mx-auto mb-5 shadow-xl shadow-emerald-forest/20 animate-pulse">
            <span className="material-symbols-outlined text-4xl">psychiatry</span>
          </div>
          <span className="inline-block text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-digital-mint/15 text-emerald-forest border border-digital-mint/30 mb-3">
            AgriChain AI • Predictive Multi-Fruit Platform
          </span>
          <h1 className="text-3xl font-black text-primary tracking-tight">
            Welcome to AgriChain AI
          </h1>
          <p className="text-xs text-on-surface-variant mt-2 leading-relaxed max-w-sm mx-auto">
            Select your role to access your personalized workspace. Each stakeholder enters a dedicated environment tailored strictly to their workflows, tools, and telemetry.
          </p>
        </div>

        <RoleSelectionModal
          isOpen={showRoleModal}
          activeRole={activeRole}
          onSelectRole={handleRoleSelect}
          onClose={() => {}}
          canDismiss={false}
        />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen md:h-screen w-full overflow-x-hidden md:overflow-hidden bg-background text-on-background">
      {/* Shared Sidebar Component with Responsive Drawer */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        mobileOpen={mobileMenuOpen}
        setMobileOpen={setMobileMenuOpen}
        activeRole={activeRole}
        onOpenRoleSelector={() => {
          setCanDismissRoleModal(true);
          setShowRoleModal(true);
        }}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 w-full min-h-screen md:min-h-0 md:overflow-y-auto overflow-x-hidden p-4 sm:p-6 md:p-10 relative scrollbar-thin">
        
        {/* Top Header Row with Mobile Menu Button */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 border-b border-outline-variant/50 pb-5">
          <div className="flex items-start gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden mt-0.5 p-2 rounded-xl border border-outline-variant hover:bg-surface-container-high text-emerald-forest transition-colors shrink-0"
              aria-label="Open Navigation Menu"
            >
              <span className="material-symbols-outlined text-xl">menu</span>
            </button>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-md bg-emerald-forest/10 text-emerald-forest">
                  {roleConfig.title} Workspace
                </span>
                <span className="text-[10px] text-outline font-mono">
                  Tab: {activeTab.toUpperCase()}
                </span>
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-emerald-forest tracking-tight">
                {roleConfig.headerTitle}
              </h2>
              <p className="text-xs sm:text-sm text-on-surface-variant mt-0.5 leading-relaxed">
                {roleConfig.headerSubtitle}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2.5 self-end sm:self-auto shrink-0">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-container-low border border-outline-variant/60 text-xs shadow-xs">
              <span className={`w-2 h-2 rounded-full ${healthData.status === "healthy" ? "bg-digital-mint animate-pulse" : "bg-error"}`} />
              <span className="text-[11px] font-bold text-primary">Role: {roleConfig.title}</span>
            </div>

            <button
              onClick={() => {
                setCanDismissRoleModal(true);
                setShowRoleModal(true);
              }}
              className="px-3.5 py-2 rounded-xl bg-emerald-forest hover:bg-forest-shadow text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
              title="Switch stakeholder workspace"
            >
              <span className="material-symbols-outlined text-sm">swap_horiz</span>
              <span>Switch Role</span>
            </button>
          </div>
        </header>

        {/* Role Overview Quick Stats Bar */}
        <div className="mb-6 grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {roleConfig.quickStats.map((stat, idx) => (
            <div
              key={idx}
              className="bg-white rounded-2xl p-4 border border-outline-variant/60 shadow-xs flex items-center gap-3.5"
            >
              <div className={`w-10 h-10 rounded-xl ${roleConfig.iconBg} flex items-center justify-center shrink-0 shadow-xs`}>
                <span className="material-symbols-outlined text-xl">{stat.icon}</span>
              </div>
              <div className="min-w-0">
                <div className="text-[10px] uppercase font-bold tracking-wider text-outline">
                  {stat.label}
                </div>
                <div className="text-sm font-extrabold text-primary truncate">
                  {stat.value}
                </div>
                <div className="text-[10px] text-on-surface-variant truncate">
                  {stat.subtext}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Dynamic View Panels */}
        <div className="flex-1 w-full max-w-container-max mx-auto">

          {/* Access Restricted Safeguard View */}
          {!isAllowed && (
            <div className="bg-white rounded-3xl p-8 sm:p-12 border border-amber-200/80 shadow-md max-w-xl mx-auto text-center my-10 animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-amber-100 text-amber-800 flex items-center justify-center mx-auto mb-4 shadow-xs">
                <span className="material-symbols-outlined text-3xl">lock</span>
              </div>
              <span className="inline-block text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-300 mb-2">
                Restricted Workspace Access
              </span>
              <h3 className="text-xl font-extrabold text-primary">
                Tab &apos;{activeTab}&apos; is Not Accessible for {roleConfig.title}
              </h3>
              <p className="text-xs text-on-surface-variant mt-2 leading-relaxed max-w-md mx-auto">
                AgriChain AI strictly restricts dashboard navigation based on your selected stakeholder identity. The <strong>{activeTab}</strong> view belongs to another role workspace.
              </p>
              <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  onClick={() => handleTabChange(roleConfig.defaultTab)}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-emerald-forest hover:bg-forest-shadow text-white font-bold text-xs shadow-sm transition cursor-pointer"
                >
                  Return to {roleConfig.title} Workspace ({roleConfig.defaultTab})
                </button>
                <button
                  onClick={() => {
                    setCanDismissRoleModal(true);
                    setShowRoleModal(true);
                  }}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-outline-variant hover:bg-surface-container-high text-primary font-bold text-xs transition cursor-pointer"
                >
                  Switch Stakeholder Role
                </button>
              </div>
            </div>
          )}

          {/* TAB 1: AI Produce Analysis (MULTI-FRUIT DUAL-MODE INSPECTION) */}
          {isAllowed && activeTab === "analyze" && (
            <div className="flex flex-col gap-8">
              {/* Top Banner: Multi-Fruit Platform Capabilities */}
              <div className="bg-white rounded-[2rem] p-6 border border-outline-variant/60 premium-shadow flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="material-symbols-outlined text-digital-mint text-2xl">science</span>
                    <h2 className="text-xl font-extrabold text-emerald-forest">
                      Multi-Fruit Quality & Detection Hub
                    </h2>
                    <span className="bg-digital-mint/15 text-emerald-forest border border-digital-mint/30 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                      Phase 17B
                    </span>
                  </div>
                  <p className="text-xs text-on-surface-variant max-w-2xl leading-relaxed">
                    Unified produce inspection engine supporting <strong>Guava</strong>, <strong>Banana</strong>, <strong>Apple</strong>, and <strong>Mango</strong> via dual operating modes: Manual Commodity Selection or Automatic Stage 1 Species Identification with uncertainty gating.
                  </p>
                </div>

                {/* Mode Selector Pill */}
                <div className="flex bg-surface-container-high/80 p-1.5 rounded-2xl border border-outline-variant/40 shrink-0 self-start md:self-auto">
                  <button
                    onClick={() => {
                      setInspectionMode("manual");
                      setAnalysisResult(null);
                      setAnalysisError(null);
                    }}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                      inspectionMode === "manual"
                        ? "bg-emerald-forest text-white shadow-md shadow-emerald-forest/20"
                        : "text-on-surface-variant hover:text-emerald-forest"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">tune</span>
                    Manual Selection
                  </button>
                  <button
                    onClick={() => {
                      setInspectionMode("auto");
                      setAnalysisResult(null);
                      setAnalysisError(null);
                    }}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                      inspectionMode === "auto"
                        ? "bg-digital-mint text-white shadow-md shadow-digital-mint/20"
                        : "text-on-surface-variant hover:text-emerald-forest"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">auto_awesome</span>
                    Auto Identification (Stage 1)
                  </button>
                </div>
              </div>

              {/* Mode Description & Commodity Selection Bar */}
              {inspectionMode === "manual" ? (
                <div>
                  <div className="flex items-center justify-between mb-3 px-1">
                    <div className="text-xs font-bold text-outline uppercase tracking-wider">
                      Step 1: Choose Commodity Specification
                    </div>
                    <span className="text-[11px] text-on-surface-variant">
                      Selected: <strong className="text-emerald-forest uppercase">{selectedFruit}</strong>
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {SUPPORTED_FRUITS.map((fruit) => {
                      const isSelected = selectedFruit === fruit.id;
                      return (
                        <div
                          key={fruit.id}
                          onClick={() => {
                            setSelectedFruit(fruit.id);
                            setAnalysisResult(null);
                            setAnalysisError(null);
                          }}
                          className={`p-4 rounded-2xl cursor-pointer border transition-all ${
                            isSelected
                              ? "bg-white border-digital-mint ring-2 ring-digital-mint/30 premium-shadow shadow-digital-mint/10"
                              : "bg-white/70 border-outline-variant/60 hover:bg-white hover:border-outline-variant"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className={`material-symbols-outlined text-lg ${isSelected ? "text-digital-mint" : "text-outline"}`}>
                                {fruit.icon}
                              </span>
                              <h4 className="font-bold text-sm text-emerald-forest">{fruit.name}</h4>
                            </div>
                            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase border ${fruit.badgeClass}`}>
                              {fruit.statusLabel}
                            </span>
                          </div>
                          <p className="text-[10px] text-outline font-mono italic mb-2">{fruit.scientificName}</p>
                          <p className="text-[11px] text-on-surface-variant leading-relaxed line-clamp-2">{fruit.description}</p>
                          <div className="mt-3 pt-2.5 border-t border-outline-variant/30 flex items-center justify-between text-[10px] font-mono text-outline">
                            <span>{fruit.modelName}</span>
                            <span>{fruit.version}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-2xl bg-digital-mint/10 border border-digital-mint/30 flex items-start gap-3">
                  <span className="material-symbols-outlined text-digital-mint text-xl mt-0.5 shrink-0">psychology</span>
                  <div>
                    <div className="text-xs font-bold text-emerald-forest uppercase tracking-wide flex items-center gap-2">
                      <span>Automatic Stage 1 Fruit Identification Active (MobileNetV3-Large)</span>
                      <span className="bg-digital-mint text-white text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase">
                        Test F1: 0.9981
                      </span>
                    </div>
                    <p className="text-xs text-on-surface-variant mt-1 leading-relaxed">
                      Upload any produce image. Stage 1 model automatically classifies the commodity among <strong>Guava</strong>, <strong>Banana</strong>, <strong>Apple</strong>, <strong>Mango</strong>, or <strong>Canopy Foliage</strong>. If species confidence is below 80% or ambiguous, a manual confirmation prompt is triggered before downstream prediction.
                    </p>
                  </div>
                </div>
              )}

              {/* Main Analysis Workspace (2-Column Grid) */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
                {/* Left Column: Upload & Specimen Inspection Trigger */}
                <div className="bg-white rounded-[2rem] p-8 border border-outline-variant/60 premium-shadow">
                  <h3 className="text-lg font-bold text-emerald-forest mb-2 flex items-center gap-2">
                    <span className="material-symbols-outlined text-digital-mint">cloud_upload</span>
                    Produce Specimen Upload
                  </h3>
                  <p className="text-xs text-on-surface-variant mb-4">
                    {inspectionMode === "manual" ? (
                      <>Targeting <strong>{selectedFruit.toUpperCase()}</strong>. Upload a clear photograph for certified inference.</>
                    ) : (
                      <>Upload a fruit photograph. Stage 1 AI will identify species and invoke the target model.</>
                    )}
                  </p>

                  {/* Manual Mode Fruit-Specific Status Notice */}
                  {inspectionMode === "manual" && selectedFruit === "mango" && (
                    <div className="mb-4 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start gap-3">
                      <span className="material-symbols-outlined text-rose-600 text-lg mt-0.5 shrink-0">info</span>
                      <div>
                        <div className="text-xs font-bold uppercase tracking-wide">
                          Mango Model Gated — Training Data Deficit
                        </div>
                        <p className="text-xs text-rose-800 mt-1 leading-relaxed">
                          In compliance with AgriChain AI zero-fake-prediction standards, synthetic or cross-crop inferences are strictly disabled. Mango maturity evaluation requires a verified multi-stage dataset which is currently awaiting field collection.
                        </p>
                      </div>
                    </div>
                  )}

                  {inspectionMode === "manual" && selectedFruit === "apple" && (
                    <div className="mb-4 p-3.5 rounded-2xl bg-purple-50 border border-purple-200 text-purple-900 flex items-start gap-2.5">
                      <span className="material-symbols-outlined text-purple-600 text-base mt-0.5 shrink-0">visibility</span>
                      <p className="text-xs leading-relaxed">
                        <strong>Apple YOLOv8n Object Detector:</strong> Detects in-orchard apple instances and renders bounding boxes (CC BY-NC 4.0). Does <em>not</em> assess peel maturity or market grade.
                      </p>
                    </div>
                  )}

                  {/* Dropzone with Interactive Visual Overlay */}
                  <label className="border-2 border-dashed border-outline-variant hover:border-digital-mint transition-colors rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer min-h-[220px] relative overflow-hidden bg-surface-container-high/20">
                    <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
                    {previewUrl ? (
                      <div className="relative w-full max-h-[260px] flex justify-center items-center">
                        <img
                          src={previewUrl}
                          alt="Preview"
                          onLoad={(e) => {
                            setNaturalImgDimensions({
                              width: e.target.naturalWidth || 640,
                              height: e.target.naturalHeight || 640,
                            });
                          }}
                          className="rounded-xl object-contain max-h-[260px] max-w-full block"
                        />

                        {/* Apple YOLO Detection Bounding Box Overlay */}
                        {analysisResult?.detection?.boxes?.length > 0 && naturalImgDimensions.width > 0 && (
                          <svg
                            viewBox={`0 0 ${naturalImgDimensions.width} ${naturalImgDimensions.height}`}
                            className="absolute inset-0 w-full h-full pointer-events-none rounded-xl"
                            style={{ objectFit: "contain" }}
                          >
                            {analysisResult.detection.boxes.map((box, idx) => (
                              <g key={idx}>
                                <rect
                                  x={box.x1}
                                  y={box.y1}
                                  width={Math.max(1, box.x2 - box.x1)}
                                  height={Math.max(1, box.y2 - box.y1)}
                                  fill="rgba(168, 85, 247, 0.25)"
                                  stroke="#a855f7"
                                  strokeWidth={Math.max(2, naturalImgDimensions.width / 200)}
                                  rx="4"
                                />
                                <rect
                                  x={box.x1}
                                  y={Math.max(0, box.y1 - (naturalImgDimensions.width / 35))}
                                  width={Math.min(box.x2 - box.x1, naturalImgDimensions.width / 5)}
                                  height={naturalImgDimensions.width / 35}
                                  fill="#a855f7"
                                  rx="2"
                                />
                                <text
                                  x={box.x1 + 4}
                                  y={Math.max(12, box.y1 - 4)}
                                  fill="#ffffff"
                                  fontSize={Math.max(10, naturalImgDimensions.width / 50)}
                                  fontWeight="bold"
                                  fontFamily="monospace"
                                >
                                  Apple {(box.confidence * 100).toFixed(0)}%
                                </text>
                              </g>
                            ))}
                          </svg>
                        )}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center text-center py-4">
                        <span className="material-symbols-outlined text-4xl text-outline mb-2">add_photo_alternate</span>
                        <span className="text-xs font-semibold text-emerald-forest">Click or drag image to browse</span>
                        <span className="text-[10px] text-outline mt-1 font-mono">JPEG, PNG, WEBP (up to 10MB)</span>
                      </div>
                    )}
                  </label>

                  {/* Image Scope Guidance */}
                  <div className="mt-4 p-4 bg-surface-container-high/60 rounded-2xl border border-outline-variant/40 flex flex-col gap-2">
                    <div className="text-xs font-bold text-emerald-forest flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-sm text-digital-mint">lightbulb</span>
                      Produce Specimen Best Practices
                    </div>
                    <ul className="text-[11px] text-on-surface-variant/90 space-y-1 pl-4 list-disc leading-relaxed">
                      <li>Center produce specimen with good natural lighting and minimal occlusion.</li>
                      <li>For Apple detection, full canopy or fruit cluster views are fully supported.</li>
                      <li>For Guava and Banana classification, individual produce close-up is recommended.</li>
                    </ul>
                  </div>

                  {/* Trigger Buttons */}
                  <div className="mt-6 flex gap-4">
                    <button
                      onClick={() => runAnalysis()}
                      disabled={!selectedFile || analyzing}
                      className={`flex-1 py-3 px-6 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all ${
                        !selectedFile || analyzing
                          ? "bg-surface-container-high text-outline cursor-not-allowed"
                          : "bg-emerald-forest text-white hover:bg-primary shadow-lg shadow-emerald-forest/15"
                      }`}
                    >
                      {analyzing ? (
                        <>
                          <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                          Evaluating Specimen...
                        </>
                      ) : inspectionMode === "manual" ? (
                        selectedFruit === "guava" ? "Evaluate Guava Maturity (ResNet18)"
                        : selectedFruit === "banana" ? "Evaluate Banana Ripeness (ResNet18)"
                        : selectedFruit === "apple" ? "Detect Apples (YOLOv8n)"
                        : "Inspect Mango Status (Gated)"
                      ) : (
                        "Identify Species & Inspect Produce"
                      )}
                      <span className="material-symbols-outlined text-sm">settings_suggest</span>
                    </button>

                    {selectedFile && (
                      <button
                        onClick={() => {
                          setSelectedFile(null);
                          setPreviewUrl(null);
                          setAnalysisResult(null);
                          setAnalysisError(null);
                        }}
                        className="border border-outline-variant hover:bg-surface-container-high text-on-surface-variant p-3 rounded-xl transition-colors"
                        title="Clear image"
                      >
                        <span className="material-symbols-outlined text-lg">delete</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Right Column: Prediction Verdict & Visual Analytics */}
                <div className="flex flex-col gap-6">
                  {analyzing && (
                    <div className="bg-white rounded-[2rem] p-10 border border-outline-variant/60 premium-shadow flex flex-col items-center justify-center min-h-[350px] text-center">
                      <div className="w-12 h-12 rounded-full border-4 border-digital-mint/30 border-t-digital-mint animate-spin mb-4" />
                      <h4 className="font-bold text-emerald-forest">Executing Produce Pipeline</h4>
                      <p className="text-xs text-on-surface-variant mt-2 max-w-xs leading-relaxed">
                        {inspectionMode === "auto"
                          ? "Running Stage 1 Fruit Identifier (MobileNetV3-Large) and cascading to verified downstream model..."
                          : `Executing ${selectedFruit.toUpperCase()} inference on active compute runtime...`}
                      </p>
                    </div>
                  )}

                  {analysisError && (
                    <div className="bg-error/5 border border-error/20 rounded-[2rem] p-8 premium-shadow min-h-[300px] flex flex-col justify-center">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-full bg-error/15 text-error flex items-center justify-center shrink-0">
                          <span className="material-symbols-outlined">report</span>
                        </div>
                        <div>
                          <h4 className="font-bold text-error">Inspection Error</h4>
                          <p className="text-[10px] uppercase font-bold tracking-wider text-error/70">
                            Backend Validation / Service Diagnostic
                          </p>
                        </div>
                      </div>
                      <div className="bg-white/80 p-4 rounded-xl border border-error/10 text-xs font-mono text-error-container select-all">
                        {analysisError}
                      </div>
                    </div>
                  )}

                  {analysisResult && (
                    <div className="bg-white rounded-[2rem] p-8 border border-outline-variant/60 premium-shadow flex flex-col gap-6">
                      {/* Top Result Header */}
                      <div className="flex items-center justify-between pb-4 border-b border-outline-variant/30">
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-digital-mint">analytics</span>
                          <h3 className="text-lg font-bold text-emerald-forest">Inspection Analysis Verdict</h3>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-high text-outline uppercase">
                          Mode: {analysisResult.mode || inspectionMode}
                        </span>
                      </div>

                      {/* Stage 1 Identification Card (If Auto Mode or ID present) */}
                      {analysisResult.identification && (
                        <div className="p-4 rounded-2xl bg-surface-container-high/40 border border-outline-variant/50">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] font-bold text-outline uppercase tracking-wider flex items-center gap-1.5">
                              <span className="material-symbols-outlined text-xs text-digital-mint">psychology</span>
                              Stage 1 Species Recognition
                            </span>
                            <span className="text-xs font-mono font-bold text-digital-mint">
                              {(analysisResult.identification.confidence * 100).toFixed(1)}% Confidence
                            </span>
                          </div>

                          <div className="flex items-center justify-between">
                            <div>
                              <span className="text-xs text-on-surface-variant">Predicted Commodity:</span>
                              <div className="text-base font-extrabold text-emerald-forest capitalize">
                                {analysisResult.identification.predicted_fruit?.replace("_", " ")}
                              </div>
                            </div>
                            <span className="text-[10px] font-mono text-outline">
                              Model: {analysisResult.identification.model_name} (v{analysisResult.identification.model_version})
                            </span>
                          </div>

                          {/* Identification Softmax Distribution */}
                          {analysisResult.identification.probabilities && (
                            <div className="mt-3 pt-3 border-t border-outline-variant/30 grid grid-cols-2 sm:grid-cols-5 gap-2">
                              {Object.entries(analysisResult.identification.probabilities).map(([crop, prob]) => (
                                <div key={crop} className="bg-white p-2 rounded-xl border border-outline-variant/30 text-center">
                                  <div className="text-[10px] font-bold uppercase truncate text-outline">{crop.replace("_", " ")}</div>
                                  <div className="text-xs font-extrabold font-mono text-emerald-forest mt-0.5">
                                    {(prob * 100).toFixed(1)}%
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Uncertainty Gate Notice & Manual Override Buttons */}
                          {analysisResult.identification.is_uncertain && (
                            <div className="mt-4 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex flex-col gap-2">
                              <div className="flex items-start gap-2">
                                <span className="material-symbols-outlined text-amber-700 text-lg mt-0.5 shrink-0">warning</span>
                                <div>
                                  <div className="text-xs font-bold text-amber-900">
                                    Species Identification Uncertain
                                  </div>
                                  <p className="text-[11px] text-amber-900/80 mt-0.5 leading-relaxed">
                                    {analysisResult.identification.uncertainty_reason || "Low confidence or foliage detected. Downstream model was not invoked automatically."}
                                  </p>
                                </div>
                              </div>
                              <div className="mt-1 pt-2 border-t border-amber-500/20">
                                <span className="text-[10px] font-bold text-amber-900 uppercase">Confirm commodity manually:</span>
                                <div className="flex flex-wrap gap-2 mt-1.5">
                                  {["guava", "banana", "apple", "mango"].map((fruitKey) => (
                                    <button
                                      key={fruitKey}
                                      onClick={() => {
                                        setSelectedFruit(fruitKey);
                                        runAnalysis(fruitKey, "manual");
                                      }}
                                      className="px-3 py-1 rounded-lg text-xs font-bold bg-white text-emerald-forest border border-amber-500/40 hover:bg-amber-500/20 transition-colors capitalize"
                                    >
                                      Inspect as {fruitKey}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* COMMODITY 1: GUAVA CLASSIFICATION RESULT */}
                      {analysisResult.target_fruit === "guava" && (analysisResult.classification || analysisResult.predicted_class) && (
                        (() => {
                          const cls = analysisResult.classification || analysisResult;
                          return (
                            <div className="flex flex-col gap-4">
                              <div className="bg-background border border-outline-variant/40 rounded-2xl p-5 flex justify-between items-center">
                                <div>
                                  <span className="text-[10px] font-bold text-outline uppercase tracking-wider">Harvest Maturity Stage</span>
                                  <div className="text-2xl font-extrabold text-emerald-forest mt-0.5">
                                    {cls.label || cls.predicted_class}
                                  </div>
                                  <div className="text-[11px] font-mono text-outline mt-0.5">
                                    Guava (<em>Psidium guajava</em>) — Index {cls.class_index ?? getClassIndex(cls) ?? "N/A"}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <span className="text-[10px] font-bold text-outline uppercase tracking-wider">Softmax Score</span>
                                  <div className="text-2xl font-extrabold text-digital-mint mt-0.5">
                                    {formatConfidence(cls.confidence)}
                                  </div>
                                  <div className="text-[10px] text-outline font-mono mt-0.5">Certified v2.0.0</div>
                                </div>
                              </div>

                              {/* Guava 3-Stage Softmax Distribution */}
                              {cls.probabilities && (
                                <div>
                                  <h4 className="text-xs font-bold text-emerald-forest uppercase tracking-wider mb-3">
                                    Harvest Maturity Probabilities (Softmax)
                                  </h4>
                                  <div className="flex flex-col gap-3">
                                    {Object.entries(cls.probabilities).map(([stageName, prob]) => {
                                      const percent = (prob * 100).toFixed(1);
                                      const idx = getClassIndex(stageName);
                                      const barColor = idx === 2 ? "bg-digital-mint" : idx === 1 ? "bg-amber-500" : "bg-blue-500";
                                      return (
                                        <div key={stageName} className="flex flex-col gap-1">
                                          <div className="flex justify-between items-center text-xs font-semibold">
                                            <span className="flex items-center gap-2">
                                              <span className={`w-2 h-2 rounded-full ${barColor}`} />
                                              {stageName}
                                            </span>
                                            <span className="font-mono text-outline">{percent}%</span>
                                          </div>
                                          <div className="w-full bg-surface-container-high h-2.5 rounded-full overflow-hidden">
                                            <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${percent}%` }} />
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              <div className="p-3 bg-surface-container-high/50 rounded-xl border border-outline-variant/30 text-[11px] text-on-surface-variant flex items-start gap-2">
                                <span className="material-symbols-outlined text-sm text-outline mt-0.5 shrink-0">info</span>
                                <span>
                                  <strong>Guava Harvest Scope:</strong> Assesses surface intake maturity stage (Green, Mature Green, Ripe) for packhouse handling and cold-chain routing.
                                </span>
                              </div>
                            </div>
                          );
                        })()
                      )}

                      {/* COMMODITY 2: BANANA CLASSIFICATION RESULT */}
                      {analysisResult.target_fruit === "banana" && (analysisResult.classification || analysisResult.predicted_class) && (
                        (() => {
                          const cls = analysisResult.classification || analysisResult;
                          return (
                            <div className="flex flex-col gap-4">
                              <div className="bg-background border border-outline-variant/40 rounded-2xl p-5 flex justify-between items-center">
                                <div>
                                  <span className="text-[10px] font-bold text-outline uppercase tracking-wider">Peel Ripeness Stage</span>
                                  <div className="text-2xl font-extrabold text-amber-800 mt-0.5">
                                    {cls.label || cls.predicted_class}
                                  </div>
                                  <div className="text-[11px] font-mono text-outline mt-0.5">
                                    Banana (<em>Musa acuminata</em>) — 4-Stage Peel Taxonomy
                                  </div>
                                </div>
                                <div className="text-right">
                                  <span className="text-[10px] font-bold text-outline uppercase tracking-wider">Softmax Score</span>
                                  <div className="text-2xl font-extrabold text-amber-600 mt-0.5">
                                    {formatConfidence(cls.confidence)}
                                  </div>
                                  <div className="text-[10px] text-outline font-mono mt-0.5">Baseline v1.0.0</div>
                                </div>
                              </div>

                              {/* Banana 4-Stage Softmax Distribution */}
                              {cls.probabilities && (
                                <div>
                                  <h4 className="text-xs font-bold text-emerald-forest uppercase tracking-wider mb-3">
                                    Peel Degreening & Ripeness Probabilities
                                  </h4>
                                  <div className="flex flex-col gap-3">
                                    {Object.entries(cls.probabilities).map(([stageName, prob]) => {
                                      const percent = (prob * 100).toFixed(1);
                                      const isRipe = stageName.toLowerCase() === "ripe";
                                      const isHalf = stageName.toLowerCase().includes("half");
                                      const isOver = stageName.toLowerCase().includes("over");
                                      const barColor = isRipe ? "bg-digital-mint" : isHalf ? "bg-amber-500" : isOver ? "bg-amber-800" : "bg-blue-500";
                                      return (
                                        <div key={stageName} className="flex flex-col gap-1">
                                          <div className="flex justify-between items-center text-xs font-semibold">
                                            <span className="flex items-center gap-2">
                                              <span className={`w-2 h-2 rounded-full ${barColor}`} />
                                              {stageName.replace("_", " ")}
                                            </span>
                                            <span className="font-mono text-outline">{percent}%</span>
                                          </div>
                                          <div className="w-full bg-surface-container-high h-2.5 rounded-full overflow-hidden">
                                            <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${percent}%` }} />
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              <div className="p-3 bg-surface-container-high/50 rounded-xl border border-outline-variant/30 text-[11px] text-on-surface-variant flex items-start gap-2">
                                <span className="material-symbols-outlined text-sm text-outline mt-0.5 shrink-0">info</span>
                                <span>
                                  <strong>Banana Ripeness Scope:</strong> High-ethylene climacteric monocot peel degreening taxonomy (Unripe, Half_Ripe, Ripe, Overripe).
                                </span>
                              </div>
                            </div>
                          );
                        })()
                      )}

                      {/* COMMODITY 3: APPLE YOLOv8n OBJECT DETECTION RESULT */}
                      {analysisResult.target_fruit === "apple" && analysisResult.detection && (
                        <div className="flex flex-col gap-4">
                          <div className="bg-background border border-purple-200/60 rounded-2xl p-5 flex justify-between items-center">
                            <div>
                              <span className="text-[10px] font-bold text-outline uppercase tracking-wider">In-Orchard Detection</span>
                              <div className="text-2xl font-extrabold text-purple-900 mt-0.5">
                                {analysisResult.detection.detected_apples_count} {analysisResult.detection.detected_apples_count === 1 ? "Apple" : "Apples"} Detected
                              </div>
                              <div className="text-[11px] font-mono text-outline mt-0.5">
                                Apple (<em>Malus domestica</em>) — YOLOv8n Bounding Boxes
                              </div>
                            </div>
                            <div className="text-right">
                              <span className="text-[10px] font-bold text-outline uppercase tracking-wider">Mean Confidence</span>
                              <div className="text-2xl font-extrabold text-purple-700 mt-0.5">
                                {analysisResult.detection.average_confidence
                                  ? `${(analysisResult.detection.average_confidence * 100).toFixed(1)}%`
                                  : "N/A"}
                              </div>
                              <div className="text-[10px] text-outline font-mono mt-0.5">Detection Only</div>
                            </div>
                          </div>

                          {/* Bounding Boxes Table / Summary */}
                          {analysisResult.detection.boxes?.length > 0 ? (
                            <div>
                              <h4 className="text-xs font-bold text-emerald-forest uppercase tracking-wider mb-2">
                                Detected Produce Instances ({analysisResult.detection.boxes.length})
                              </h4>
                              <div className="max-h-48 overflow-y-auto rounded-xl border border-outline-variant/40 divide-y divide-outline-variant/30 text-xs">
                                {analysisResult.detection.boxes.map((b, idx) => (
                                  <div key={idx} className="p-2.5 flex items-center justify-between bg-white hover:bg-surface-container-high/30">
                                    <div className="flex items-center gap-2">
                                      <span className="w-5 h-5 rounded-full bg-purple-100 text-purple-800 font-bold font-mono text-[10px] flex items-center justify-center">
                                        #{idx + 1}
                                      </span>
                                      <span className="font-semibold text-emerald-forest capitalize">Apple Instance</span>
                                    </div>
                                    <div className="flex items-center gap-3 font-mono text-[11px]">
                                      <span className="text-outline">
                                        [{b.x1}, {b.y1}] - [{b.x2}, {b.y2}]
                                      </span>
                                      <span className="font-bold text-purple-700">
                                        {(b.confidence * 100).toFixed(1)}%
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div className="p-4 rounded-xl bg-surface-container-high/40 text-center text-xs text-on-surface-variant">
                              No apple instances detected above confidence threshold.
                            </div>
                          )}

                          {/* Mandatory Research License & Scope Disclaimer */}
                          <div className="p-4 rounded-2xl bg-purple-50 border border-purple-200 text-purple-900 text-xs flex flex-col gap-2">
                            <div className="font-bold uppercase tracking-wider flex items-center gap-1.5 text-[11px] text-purple-800">
                              <span className="material-symbols-outlined text-sm">balance</span>
                              Research License Notice (CC BY-NC 4.0)
                            </div>
                            <p className="text-[11px] text-purple-900/80 leading-relaxed">
                              {analysisResult.detection.scope_disclaimer || "This experimental YOLOv8n detector performs in-orchard object detection and counting only under CC BY-NC 4.0 non-commercial license. It does NOT evaluate harvest maturity stages, peel color, sweetness, or commercial market grade."}
                            </p>
                          </div>
                        </div>
                      )}

                      {/* COMMODITY 4: MANGO GATED / UNAVAILABLE RESULT */}
                      {(analysisResult.target_fruit === "mango" || analysisResult.task_type === "unavailable" || analysisResult.status === "unavailable") && (
                        <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 flex flex-col gap-4">
                          <div className="flex items-start gap-3">
                            <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center shrink-0">
                              <span className="material-symbols-outlined">block</span>
                            </div>
                            <div>
                              <h4 className="font-bold text-sm text-rose-950">
                                Mango Model Gated — Zero Synthetic Prediction Policy
                              </h4>
                              <p className="text-[11px] text-rose-700 font-mono mt-0.5">
                                Commodity: Mango (<em>Mangifera indica L.</em>)
                              </p>
                            </div>
                          </div>

                          <div className="p-4 rounded-xl bg-white/80 border border-rose-200/60 text-xs text-rose-900 leading-relaxed">
                            {analysisResult.unavailable_reason || "Mango maturity prediction is unavailable due to training dataset deficit. In accordance with AgriChain AI scientific standards, cross-crop proxy models and synthetic predictions are strictly disabled."}
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-rose-800 pt-2 border-t border-rose-200">
                            <span>Status: GATED_DEFICIT</span>
                            <span>Action: Manual Packhouse Intake Advised</span>
                          </div>
                        </div>
                      )}

                      {/* Action: Associate with Shipment */}
                      <div className="pt-2">
                        <button
                          type="button"
                          onClick={() => handleAssociateShipment(analysisResult)}
                          disabled={associatingShipment}
                          className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-bold text-xs bg-emerald-forest text-white hover:bg-forest-shadow disabled:opacity-50 transition shadow-sm"
                        >
                          <span className="material-symbols-outlined text-sm">local_shipping</span>
                          {associatingShipment ? "Associating & Initializing Transit..." : "Associate with Shipment & Track PostGIS Route"}
                        </button>
                        {shipmentAssociateSuccess && (
                          <div className="mt-2 p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-center text-xs text-emerald-800 font-medium">
                            ✓ {shipmentAssociateSuccess}
                          </div>
                        )}
                        {shipmentAssociateError && (
                          <div className="mt-2 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-center text-xs text-rose-800 font-medium">
                            ✗ {shipmentAssociateError}
                          </div>
                        )}
                      </div>

                      {/* Bottom Result Metadata Bar */}
                      <div className="pt-4 border-t border-outline-variant/30 flex flex-wrap justify-between items-center text-[10px] text-outline font-mono gap-2">
                        <span>Device: {analysisResult.device || "CUDA"}</span>
                        <span>Latency: {analysisResult.inference_ms != null ? `${analysisResult.inference_ms} ms` : "N/A"}</span>
                        <span>Target: {analysisResult.target_fruit?.toUpperCase() || "MULTI-FRUIT"}</span>
                      </div>
                    </div>
                  )}

                  {!analyzing && !analysisError && !analysisResult && (
                    <div className="bg-white/60 border border-outline-variant/60 rounded-[2rem] p-10 flex flex-col items-center justify-center min-h-[350px] text-center text-outline">
                      <span className="material-symbols-outlined text-4xl mb-2">dashboard_customize</span>
                      <h4 className="font-semibold text-sm">Produce Verdict Awaiting</h4>
                      <p className="text-xs max-w-xs mt-2 leading-relaxed">
                        Select a commodity or use automatic identification, upload a photo, and run inference to display quality verdicts and object detections.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Farmer Dashboard (DEMO / SIMULATION) */}
          {isAllowed && activeTab === "farmer" && (
            <div className="flex flex-col gap-6">
              {/* Feature 2: Dedicated Farmer Stock & Inventory Management */}
              <FarmerInventoryManager currentFarmerId="FARMER-PB-001" role={activeRole} />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white rounded-2xl p-6 border border-outline-variant/50 premium-shadow">
                  <span className="text-[10px] font-bold text-outline uppercase tracking-wider flex justify-between items-center">
                    Yield Forecast <span>[Simulation]</span>
                  </span>
                  <div className="text-2xl font-bold text-emerald-forest mt-2">1,240 boxes</div>
                  <p className="text-[10px] text-digital-mint mt-1 font-semibold flex items-center gap-1">
                    <span className="material-symbols-outlined text-xs">trending_up</span> +12% over historical avg
                  </p>
                </div>
                <div className="bg-white rounded-2xl p-6 border border-outline-variant/50 premium-shadow">
                  <span className="text-[10px] font-bold text-outline uppercase tracking-wider flex justify-between items-center">
                    Soil Moisture <span>[Demo Data]</span>
                  </span>
                  <div className="text-2xl font-bold text-emerald-forest mt-2">38.2%</div>
                  <p className="text-[10px] text-on-surface-variant mt-1 font-semibold">Optimal saturation levels</p>
                </div>
                <div className="bg-white rounded-2xl p-6 border border-outline-variant/50 premium-shadow">
                  <span className="text-[10px] font-bold text-outline uppercase tracking-wider flex justify-between items-center">
                    Active Storage Cells <span>[Demo Data]</span>
                  </span>
                  <div className="text-2xl font-bold text-emerald-forest mt-2">4 cells active</div>
                  <p className="text-[10px] text-error mt-1 font-semibold">Cell 2 ethylene alert flag</p>
                </div>
              </div>

              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                <h3 className="font-bold text-emerald-forest mb-4 flex justify-between items-center text-sm uppercase">
                  Harvested Batches Checklist <span>[Demo Data]</span>
                </h3>
                <div className="overflow-x-auto min-w-0 w-full scrollbar-thin">
                  <table className="w-full text-left text-xs border-collapse min-w-[500px]">
                    <thead>
                      <tr className="border-b border-outline-variant/60 text-outline">
                        <th className="pb-3 font-semibold">Batch ID</th>
                        <th className="pb-3 font-semibold">Field Node</th>
                        <th className="pb-3 font-semibold">Volume</th>
                        <th className="pb-3 font-semibold">Sensor Status</th>
                        <th className="pb-3 font-semibold">AI Grade status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-outline-variant/30">
                        <td className="py-3 font-bold">BTC-2026-09A</td>
                        <td className="py-3">Zone D (Guava Orchard)</td>
                        <td className="py-3 font-mono">180 crates</td>
                        <td className="py-3"><span className="text-digital-mint font-semibold">Active</span></td>
                        <td className="py-3"><span className="bg-digital-mint/15 text-emerald-forest font-bold px-2 py-0.5 rounded text-[10px]">Ripe (Class 2)</span></td>
                      </tr>
                      <tr className="border-b border-outline-variant/30">
                        <td className="py-3 font-bold">BTC-2026-08F</td>
                        <td className="py-3">Zone E (Ripening Chamber)</td>
                        <td className="py-3 font-mono">240 crates</td>
                        <td className="py-3"><span className="text-digital-mint font-semibold">Active</span></td>
                        <td className="py-3"><span className="bg-amber-500/15 text-amber-800 font-bold px-2 py-0.5 rounded text-[10px]">Mature Green (Class 1)</span></td>
                      </tr>
                      <tr>
                        <td className="py-3 font-bold">BTC-2026-08E</td>
                        <td className="py-3">Zone A (Intake Block)</td>
                        <td className="py-3 font-mono">150 crates</td>
                        <td className="py-3"><span className="text-outline">Offline</span></td>
                        <td className="py-3"><span className="bg-blue-500/15 text-blue-700 font-bold px-2 py-0.5 rounded text-[10px]">Green (Class 0)</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Dealer Dashboard (DEMO / SIMULATION) */}
          {isAllowed && activeTab === "dealer" && (
            <div className="flex flex-col gap-6">
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                <h3 className="font-bold text-emerald-forest mb-4 flex justify-between items-center text-sm uppercase">
                  Pending Shipments Intake <span>[Demo Data]</span>
                </h3>
                <div className="flex flex-col gap-4">
                  <div className="border border-outline-variant/40 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <div className="font-bold text-sm text-primary">Shipment #SHP-2026-042</div>
                      <div className="text-[10px] text-on-surface-variant mt-0.5">Route: Farm Gate D to Warehouse A</div>
                    </div>
                    <div className="flex items-center gap-6 text-xs">
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-outline block">Temp [Demo]</span>
                        <span className="font-bold font-mono">2.8°C</span>
                      </div>
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-outline block">Humidity [Demo]</span>
                        <span className="font-bold font-mono">82%</span>
                      </div>
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-outline block">Est Spoilage Risk [Sim]</span>
                        <span className="font-bold text-digital-mint font-mono">Low (4.2%)</span>
                      </div>
                    </div>
                    <button className="bg-digital-mint text-white font-bold text-xs px-4 py-2 rounded-lg hover:bg-emerald-forest transition-colors">
                      Accept Batch
                    </button>
                  </div>

                  <div className="border border-outline-variant/40 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <div className="font-bold text-sm text-primary">Shipment #SHP-2026-043</div>
                      <div className="text-[10px] text-on-surface-variant mt-0.5">Route: Greenhouse Zone E to Cold Storage C</div>
                    </div>
                    <div className="flex items-center gap-6 text-xs">
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-outline block">Temp [Demo]</span>
                        <span className="font-bold text-error font-mono">8.4°C (Warm)</span>
                      </div>
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-outline block">Humidity [Demo]</span>
                        <span className="font-bold font-mono">92%</span>
                      </div>
                      <div>
                        <span className="text-[9px] uppercase tracking-wider text-outline block">Est Spoilage Risk [Sim]</span>
                        <span className="font-bold text-error font-mono">High (62.8%)</span>
                      </div>
                    </div>
                    <button className="bg-error text-white font-bold text-xs px-4 py-2 rounded-lg hover:bg-error/80 transition-colors">
                      Quarantine
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Logistics Tracking (REAL BACKEND INTEGRATION) */}
          {isAllowed && activeTab === "tracking" && (
            <ShipmentsTracking backendHealth={healthData.backend} onRetryHealth={fetchHealth} />
          )}

          {/* TAB 5: Buyer Marketplace (FUNCTIONAL DEMO TRANSACTIONS) */}
          {isAllowed && activeTab === "marketplace" && (
            <div className="flex flex-col gap-6">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-6 rounded-2xl border border-outline-variant/50 premium-shadow gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-emerald-forest text-sm uppercase">B2B Verified Produce Marketplace</h3>
                    <span className="bg-digital-mint/15 text-emerald-forest border border-digital-mint/30 text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
                      Demo Workflow Active
                    </span>
                  </div>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Browse and purchase audited guava lots evaluated by the ResNet18 harvest maturity classifier.
                  </p>
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <button
                    onClick={() => setMarketplaceViewMode("catalog")}
                    className={`flex-1 sm:flex-none px-3.5 py-2 rounded-xl text-xs font-bold transition-colors flex items-center justify-center gap-1.5 ${
                      marketplaceViewMode === "catalog"
                        ? "bg-emerald-forest text-white shadow-sm"
                        : "border border-outline-variant/60 text-primary hover:bg-surface-container-high"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">storefront</span>
                    Produce Lots ({marketplaceListings.length})
                  </button>
                  <button
                    onClick={() => setMarketplaceViewMode("orders")}
                    className={`flex-1 sm:flex-none px-3.5 py-2 rounded-xl text-xs font-bold transition-colors flex items-center justify-center gap-1.5 ${
                      marketplaceViewMode === "orders"
                        ? "bg-emerald-forest text-white shadow-sm"
                        : "border border-outline-variant/60 text-primary hover:bg-surface-container-high"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">receipt_long</span>
                    My Orders ({demoOrders.length})
                  </button>
                </div>
              </div>

              {marketplaceViewMode === "catalog" ? (
                /* Produce Lots Catalog */
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {marketplaceListings.map((item) => (
                    <div key={item.id} className="bg-white rounded-2xl border border-outline-variant/50 overflow-hidden premium-shadow flex flex-col justify-between">
                      <div>
                        <div className="h-44 bg-surface-container-high relative overflow-hidden">
                          <div className={`absolute top-3 left-3 text-white text-[9px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full shadow-sm ${
                            item.ripeness_stage === "Ripe" ? "bg-digital-mint" : item.ripeness_stage === "Mature Green" ? "bg-amber-500" : "bg-blue-600"
                          }`}>
                            AI Verified: {item.ripeness_stage}
                          </div>
                          <img 
                            src={item.image_url} 
                            alt={item.title} 
                            className="w-full h-full object-cover transition-transform duration-500 hover:scale-105" 
                          />
                        </div>
                        <div className="p-5 flex flex-col gap-3">
                          <div>
                            <h4 className="font-bold text-emerald-forest text-sm leading-tight">{item.title}</h4>
                            <p className="text-[11px] text-on-surface-variant mt-0.5">
                              {item.origin_name} · <span className="font-semibold text-primary">{item.available_crates} Crates</span> available
                            </p>
                          </div>
                          <div className="flex justify-between items-center text-xs bg-surface-container-low p-3 rounded-xl border border-outline-variant/30">
                            <div>
                              <span className="text-[9px] uppercase font-bold text-outline block">Softmax Score</span>
                              <span className="font-bold font-mono text-emerald-forest">{(item.softmax_score * 100).toFixed(1)}%</span>
                            </div>
                            <div className="text-right">
                              <span className="text-[9px] uppercase font-bold text-outline block">Wholesale Price</span>
                              <span className="font-bold font-mono text-primary text-sm">₹{item.price_per_crate_inr?.toLocaleString("en-IN")}</span>
                              <span className="text-[9px] text-outline block">/ 20kg crate</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="p-5 pt-0">
                        <button 
                          onClick={() => setSelectedListingForOrder(item)}
                          disabled={item.available_crates <= 0}
                          className="w-full bg-emerald-forest text-white py-2.5 rounded-xl text-xs font-bold hover:bg-primary transition-colors flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
                        >
                          <span className="material-symbols-outlined text-sm">shopping_cart_checkout</span>
                          {item.available_crates > 0 ? "Purchase Batch" : "Sold Out"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                /* Recorded Demo Orders */
                <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h4 className="font-bold text-emerald-forest text-sm uppercase">Recorded Demo Purchase Orders</h4>
                      <p className="text-xs text-on-surface-variant mt-0.5">Orders recorded and validated in the backend persistence ledger.</p>
                    </div>
                    <button
                      onClick={loadMarketplaceData}
                      className="border border-outline-variant/60 hover:bg-surface-container-high text-primary px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-xs">refresh</span>
                      Refresh Orders
                    </button>
                  </div>

                  {loadingOrders ? (
                    <div className="py-12 text-center text-xs text-outline">Loading recorded orders...</div>
                  ) : demoOrders.length === 0 ? (
                    <div className="py-12 text-center text-xs text-outline">
                      <span className="material-symbols-outlined text-3xl mb-2 text-outline/50 block">receipt</span>
                      No demo orders placed yet. Choose a produce batch from the catalog to place an order.
                    </div>
                  ) : (
                    <div className="overflow-x-auto min-w-0 w-full scrollbar-thin">
                      <table className="w-full text-left text-xs border-collapse min-w-[550px]">
                        <thead>
                          <tr className="border-b border-outline-variant/60 text-outline">
                            <th className="pb-3 font-semibold">Order Reference</th>
                            <th className="pb-3 font-semibold">Produce Lot</th>
                            <th className="pb-3 font-semibold">Crates</th>
                            <th className="pb-3 font-semibold">Total Price</th>
                            <th className="pb-3 font-semibold">Buyer Firm</th>
                            <th className="pb-3 font-semibold">Status</th>
                            <th className="pb-3 font-semibold">Created At</th>
                          </tr>
                        </thead>
                        <tbody>
                          {demoOrders.map((order) => (
                            <tr key={order.id} className="border-b border-outline-variant/30 hover:bg-surface-container-low/50">
                              <td className="py-3 font-mono font-bold text-primary">{order.id}</td>
                              <td className="py-3 font-semibold text-emerald-forest">{order.produce_title}</td>
                              <td className="py-3 font-mono">{order.quantity_crates} crates</td>
                              <td className="py-3 font-mono font-bold text-primary">₹{order.total_price_inr?.toLocaleString("en-IN")}</td>
                              <td className="py-3 text-on-surface-variant">{order.buyer_organization || order.buyer_name}</td>
                              <td className="py-3">
                                <span className="bg-digital-mint/15 text-emerald-forest font-bold px-2 py-0.5 rounded text-[10px] uppercase">
                                  {order.status}
                                </span>
                              </td>
                              <td className="py-3 font-mono text-[10px] text-outline">
                                {order.created_at ? new Date(order.created_at).toLocaleString() : "N/A"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 6: Godown & Cold-Storage Directory (SOURCED REAL DATA) */}
          {isAllowed && activeTab === "warehouse" && (
            <FacilityDirectory />
          )}

          {/* TAB 7: Analytics (SIMULATION) */}
          {isAllowed && activeTab === "analytics" && (
            <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
              <div className="flex justify-between items-start mb-6">
                <h3 className="font-bold text-emerald-forest text-sm uppercase">CNN Classifier Performance Benchmarks</h3>
                <span className="bg-amber-500/10 text-amber-800 text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded">Evaluation Simulation</span>
              </div>
              <p className="text-xs text-on-surface-variant mb-6">
                Below are the frozen validation parameters retrieved from the selected model checkpoint (ResNet18 Guava Classifier v2.0.0).
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="border border-outline-variant/40 rounded-xl p-4 text-center">
                  <div className="text-[10px] uppercase font-bold tracking-wider text-outline">Accuracy (Validation)</div>
                  <div className="text-2xl font-extrabold text-emerald-forest mt-1">91.04%</div>
                </div>
                <div className="border border-outline-variant/40 rounded-xl p-4 text-center">
                  <div className="text-[10px] uppercase font-bold tracking-wider text-outline">Macro F1 Score</div>
                  <div className="text-2xl font-extrabold text-emerald-forest mt-1">91.85%</div>
                </div>
                <div className="border border-outline-variant/40 rounded-xl p-4 text-center">
                  <div className="text-[10px] uppercase font-bold tracking-wider text-outline">Weighted F1 Score</div>
                  <div className="text-2xl font-extrabold text-emerald-forest mt-1">91.12%</div>
                </div>
                <div className="border border-outline-variant/40 rounded-xl p-4 text-center">
                  <div className="text-[10px] uppercase font-bold tracking-wider text-outline">Classification Target</div>
                  <div className="text-lg font-extrabold text-emerald-forest mt-1">Guava (3-Stage)</div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 8: System Status (REAL INTEGRATION) */}
          {isAllowed && activeTab === "status" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                <div className="text-[10px] uppercase font-bold tracking-wider text-outline">ML API Service (Guava CNN)</div>
                <div className={`text-2xl font-bold mt-2 ${healthData.status === "healthy" ? "text-digital-mint" : "text-error"}`}>
                  {healthData.status === "healthy" ? "ONLINE" : "OFFLINE"}
                </div>
                <p className="text-[10px] text-on-surface-variant mt-1 font-mono">
                  {healthData.latencyMs !== null ? `${healthData.latencyMs}ms ping` : "127.0.0.1:8000"}
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                <div className="text-[10px] uppercase font-bold tracking-wider text-outline">Backend Service (FastAPI)</div>
                <div className={`text-2xl font-bold mt-2 ${healthData.backend?.status === "healthy" ? "text-digital-mint" : "text-error"}`}>
                  {healthData.backend?.status === "healthy" ? "ONLINE" : "OFFLINE"}
                </div>
                <p className="text-[10px] text-on-surface-variant mt-1 font-mono">
                  {healthData.backend?.latencyMs !== null ? `${healthData.backend.latencyMs}ms ping` : "127.0.0.1:8000"}
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                <div className="text-[10px] uppercase font-bold tracking-wider text-outline">Loaded Model Checkpoint</div>
                <div className="text-base font-bold text-emerald-forest mt-3 font-mono break-all">
                  {healthData.model || "best_guava_resnet18.pth"} (v{healthData.model_version || "2.0.0"})
                </div>
                <p className="text-[10px] text-on-surface-variant mt-1">Guava ResNet18 Frozen Weights</p>
              </div>

              <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow">
                <div className="text-[10px] uppercase font-bold tracking-wider text-outline">Execution Device / Network Ping</div>
                <div className="text-2xl font-bold text-emerald-forest mt-2 font-mono">
                  {healthData.device ? `${healthData.device.toUpperCase()}` : "N/A"}
                  {healthData.latencyMs !== null && ` / ${healthData.latencyMs}ms`}
                </div>
                <p className="text-[10px] text-on-surface-variant mt-1">round-trip ping time</p>
              </div>
            </div>
          )}

          {/* TAB 9: Profile / Settings (ROLE SWITCHER) */}
          {isAllowed && activeTab === "settings" && (
            <div className="bg-white rounded-[2rem] p-8 border border-outline-variant/60 premium-shadow max-w-2xl">
              <h3 className="text-lg font-bold text-emerald-forest mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-digital-mint">manage_accounts</span>
                Stakeholder Profile Roles Selector
              </h3>
              <p className="text-xs text-on-surface-variant mb-6">
                Choose your active identity to simulate workflows across different layers of the supply chain dashboard.
              </p>

              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-primary uppercase tracking-wider">Active Role</label>
                  <select 
                    value={activeRole} 
                    onChange={(e) => handleRoleSelect(e.target.value)}
                    className="w-full bg-background border border-outline-variant rounded-xl p-3 text-xs font-semibold focus:outline-none focus:border-digital-mint"
                  >
                    {SUPPORTED_ROLES.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.title} — {r.subtitle}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setCanDismissRoleModal(true);
                    setShowRoleModal(true);
                  }}
                  className="mt-2 bg-emerald-forest hover:bg-primary text-white py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-colors w-max shadow-sm"
                >
                  <span className="material-symbols-outlined text-sm">view_carousel</span>
                  Open Role Selection Gallery
                </button>

                <div className="border border-outline-variant/40 rounded-xl p-4 mt-4 bg-surface-container-low/50">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-digital-mint text-sm">info</span>
                    <span className="text-[10px] uppercase font-bold tracking-wider text-outline">Dynamic Environment Role Switcher</span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant leading-relaxed">
                    Selecting a role simulates stakeholder workflows. In a production setup, this would be tied to user authentication and credentials.
                  </p>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>

      {/* Initial / On-Demand Role Selection Modal */}
      <RoleSelectionModal
        isOpen={showRoleModal}
        activeRole={activeRole}
        onSelectRole={handleRoleSelect}
        onClose={() => setShowRoleModal(false)}
        canDismiss={canDismissRoleModal}
      />

      {/* Buyer Demo Order Purchase Modal */}
      {selectedListingForOrder && (
        <OrderPurchaseModal
          isOpen={!!selectedListingForOrder}
          listing={selectedListingForOrder}
          onClose={() => setSelectedListingForOrder(null)}
          onOrderSuccess={() => {
            loadMarketplaceData();
          }}
          defaultBuyerName={activeRole === "Buyer" ? "B2B Agro Buyer" : "Demo Buyer"}
        />
      )}
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div className="flex h-screen w-screen items-center justify-center bg-background text-emerald-forest font-bold">Loading dashboard shell...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
