"use client";
import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import RoleSelectionModal, { SUPPORTED_ROLES, ROLE_DEFAULT_TABS } from "../components/RoleSelectionModal";

export default function Home() {
  const router = useRouter();
  const [activeRole, setActiveRole] = useState(null);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [canDismissRoleModal, setCanDismissRoleModal] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedRole = localStorage.getItem("agrichain_active_role");
      const validRoles = SUPPORTED_ROLES.map((r) => r.id);
      if (savedRole && validRoles.includes(savedRole)) {
        setActiveRole(savedRole);
      } else {
        // Initial entry to website: show role selection screen
        setShowRoleModal(true);
        setCanDismissRoleModal(false);
      }
    }
  }, []);

  const handleRoleSelect = (roleId, defaultTab) => {
    setActiveRole(roleId);
    if (typeof window !== "undefined") {
      localStorage.setItem("agrichain_active_role", roleId);
    }
    setShowRoleModal(false);
    setCanDismissRoleModal(true);
    const target = defaultTab || ROLE_DEFAULT_TABS[roleId] || "analyze";
    router.push(`/dashboard?tab=${target}`);
  };

  return (
    <div className="flex flex-col min-h-screen relative overflow-x-hidden">
      {/* TopNavBar */}
      <header className="w-full sticky top-0 glass-panel z-50 transition-all duration-300">
        <div className="flex justify-between items-center w-full px-margin-mobile md:px-margin-desktop py-4 max-w-container-max mx-auto">
          <div className="flex items-center gap-2">
            <span 
              className="material-symbols-outlined text-digital-mint filled" 
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              agriculture
            </span>
            <span className="text-2xl font-bold text-emerald-forest">AgriChain AI</span>
          </div>
          <nav className="hidden md:flex gap-8">
            <a className="text-emerald-forest border-b-2 border-digital-mint pb-1 font-semibold text-sm transition-transform duration-150 active:scale-95" href="#ecosystem">
              Ecosystem
            </a>
            <a className="text-on-surface-variant pb-1 hover:text-emerald-forest transition-colors font-semibold text-sm" href="#solutions">
              Solutions
            </a>
            <a className="text-on-surface-variant pb-1 hover:text-emerald-forest transition-colors font-semibold text-sm" href="#technology">
              Technology
            </a>
          </nav>
          <div className="hidden lg:flex items-center gap-4">
            {activeRole ? (
              <button 
                onClick={() => {
                  setCanDismissRoleModal(true);
                  setShowRoleModal(true);
                }} 
                className="text-xs bg-emerald-forest/15 hover:bg-emerald-forest/25 text-emerald-forest font-bold px-3 py-1.5 rounded-full border border-digital-mint/30 shadow-sm flex items-center gap-1.5 transition-colors cursor-pointer group"
                title="Switch stakeholder identity"
              >
                <span className="w-2 h-2 rounded-full bg-digital-mint" />
                Role: {activeRole}
                <span className="material-symbols-outlined text-[13px] text-outline group-hover:text-primary transition-colors">swap_horiz</span>
              </button>
            ) : (
              <button 
                onClick={() => {
                  setCanDismissRoleModal(true);
                  setShowRoleModal(true);
                }} 
                className="text-emerald-forest hover:text-digital-mint transition-colors font-semibold text-sm px-4 py-2"
              >
                Select Role
              </button>
            )}
            <button 
              onClick={() => {
                if (activeRole) {
                  router.push(`/dashboard?tab=${ROLE_DEFAULT_TABS[activeRole] || "analyze"}`);
                } else {
                  setCanDismissRoleModal(false);
                  setShowRoleModal(true);
                }
              }}
              className="bg-digital-mint text-white hover:bg-emerald-forest transition-all font-semibold text-sm px-6 py-3 rounded-full flex items-center gap-2 shadow-lg shadow-digital-mint/20 cursor-pointer"
            >
              Get Started
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </button>
          </div>
        </div>
      </header>

      <main className="flex-grow flex flex-col items-center w-full">
        {/* Hero Section */}
        <section className="w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-16 md:py-24 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="flex flex-col gap-6 max-w-2xl">
            <div className="inline-flex items-center gap-2 bg-digital-mint/10 text-emerald-forest px-4 py-1.5 rounded-full w-max border border-digital-mint/30 shadow-sm">
              <span className="material-symbols-outlined text-sm text-digital-mint">sensors</span>
              <span className="text-[11px] font-bold uppercase tracking-wider">Live Data Pipeline Active</span>
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-emerald-forest leading-tight tracking-tight">
              AI-Powered Intelligence for Modern Agriculture
            </h1>
            <p className="text-lg text-on-surface-variant leading-relaxed">
              Helping farmers and businesses make smarter decisions with precision produce analysis and global supply-chain intelligence.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 mt-4">
              <Link 
                href="/dashboard?tab=analyze" 
                className="bg-emerald-forest text-white hover:bg-primary transition-colors font-bold text-sm px-8 py-4 rounded-full flex items-center justify-center gap-2 shadow-xl shadow-emerald-forest/20"
              >
                Analyze Produce
                <span className="material-symbols-outlined text-sm">insights</span>
              </Link>
              <Link 
                href="/dashboard?tab=farmer" 
                className="glass-panel text-emerald-forest hover:bg-surface-container-high transition-colors font-bold text-sm px-8 py-4 rounded-full flex items-center justify-center"
              >
                Explore Platform
              </Link>
            </div>
          </div>
          <div className="relative w-full h-[400px] md:h-[520px] rounded-[2rem] overflow-hidden premium-shadow">
            <div 
              className="absolute inset-0 bg-cover bg-center w-full h-full transform transition-transform hover:scale-105 duration-1000" 
              style={{ 
                backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCo4BCdI7T9xSaERR16rL4vFfQHzNLxwZ0sBvMUzlEDu-dhlu4S6HAsxtBW4A1MSLgLvDVnSqJ-cXZ1c5F3WtF3Ysi0z-O_02oMC-PpntJiD6fgbKkH6JUV_M5XGzt7ojrC1vvxMtJAjEAecNZVOZQEDVoCN9CCOl09lT4qCp-DqP2d3Nwr_w5BRSh_N9QfgV5qHuEuR-cQ-RVYkJ_f7QdkGT8Zgv04m-sDB-MVUgXdofip7iVseBtk')" 
              }}
            ></div>
            <div className="absolute bottom-0 left-0 w-full h-2/3 bg-gradient-to-t from-emerald-forest/90 via-emerald-forest/20 to-transparent"></div>
            
            {/* Logistics Chip Overlay */}
            <div className="absolute bottom-8 left-8 glass-panel px-5 py-4 rounded-2xl flex items-center gap-5 shadow-2xl">
              <div className="w-12 h-12 rounded-full bg-digital-mint/20 flex items-center justify-center border border-digital-mint/30">
                <span className="material-symbols-outlined text-digital-mint">psychology</span>
              </div>
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-forest/80 mb-0.5">Model Accuracy</div>
                <div className="text-xl font-bold text-emerald-forest">97.18%</div>
              </div>
            </div>
          </div>
        </section>

        {/* Ecosystem Section */}
        <section className="w-full bg-surface-container-low py-24 relative overflow-hidden" id="ecosystem">
          <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-digital-mint/5 via-transparent to-transparent"></div>
          <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop relative z-10">
            <div className="text-center max-w-3xl mx-auto mb-20">
              <h2 className="text-3xl md:text-4xl font-bold text-emerald-forest mb-4">The AgriChain Ecosystem</h2>
              <p className="text-on-surface-variant text-base">An unbroken chain of intelligence from the field to the final destination, powered by decentralized data nodes.</p>
            </div>
            
            <div className="flex flex-col lg:flex-row items-center justify-between gap-6 lg:gap-2 relative">
              {/* Connecting line for desktop */}
              <div className="hidden lg:block absolute top-1/2 left-0 w-full h-0.5 bg-gradient-to-r from-outline-variant/30 via-digital-mint/40 to-outline-variant/30 -z-10 -translate-y-1/2"></div>
              
              {/* Flow Nodes */}
              <div className="flex flex-col items-center gap-4 glass-panel p-6 rounded-[1.5rem] premium-shadow w-full lg:w-44 z-10 transition-transform hover:-translate-y-1 duration-300">
                <div className="w-14 h-14 rounded-full bg-emerald-forest/10 text-emerald-forest flex items-center justify-center">
                  <span className="material-symbols-outlined">local_florist</span>
                </div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-center text-emerald-forest">Farmer</span>
              </div>
              
              <span className="material-symbols-outlined text-digital-mint/50 lg:rotate-0 rotate-90">arrow_forward</span>
              
              <div className="flex flex-col items-center gap-4 bg-digital-mint p-6 rounded-[1.5rem] shadow-xl shadow-digital-mint/20 w-full lg:w-48 z-10 scale-105 border border-digital-mint/50">
                <div className="w-14 h-14 rounded-full glass-panel text-white flex items-center justify-center">
                  <span className="material-symbols-outlined">memory</span>
                </div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-center text-white">AI Analysis</span>
              </div>
              
              <span className="material-symbols-outlined text-digital-mint/50 lg:rotate-0 rotate-90">arrow_forward</span>
              
              <div className="flex flex-col items-center gap-4 glass-panel p-6 rounded-[1.5rem] premium-shadow w-full lg:w-44 z-10 transition-transform hover:-translate-y-1 duration-300">
                <div className="w-14 h-14 rounded-full bg-emerald-forest/10 text-emerald-forest flex items-center justify-center">
                  <span className="material-symbols-outlined">storefront</span>
                </div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-center text-emerald-forest">Dealer / Trader</span>
              </div>
              
              <span className="material-symbols-outlined text-digital-mint/50 lg:rotate-0 rotate-90">arrow_forward</span>
              
              <div className="flex flex-col items-center gap-4 glass-panel p-6 rounded-[1.5rem] premium-shadow w-full lg:w-44 z-10 transition-transform hover:-translate-y-1 duration-300">
                <div className="w-14 h-14 rounded-full bg-emerald-forest/10 text-emerald-forest flex items-center justify-center">
                  <span className="material-symbols-outlined">warehouse</span>
                </div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-center text-emerald-forest">Warehouse</span>
              </div>
              
              <span className="material-symbols-outlined text-digital-mint/50 lg:rotate-0 rotate-90">arrow_forward</span>
              
              <div className="flex flex-col items-center gap-4 glass-panel p-6 rounded-[1.5rem] premium-shadow w-full lg:w-44 z-10 transition-transform hover:-translate-y-1 duration-300">
                <div className="w-14 h-14 rounded-full bg-error/10 text-error flex items-center justify-center">
                  <span className="material-symbols-outlined">local_shipping</span>
                </div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-center text-emerald-forest">Transport</span>
              </div>
              
              <span className="material-symbols-outlined text-digital-mint/50 lg:rotate-0 rotate-90">arrow_forward</span>
              
              <div className="flex flex-col items-center gap-4 glass-panel p-6 rounded-[1.5rem] premium-shadow w-full lg:w-44 z-10 transition-transform hover:-translate-y-1 duration-300">
                <div className="w-14 h-14 rounded-full bg-emerald-forest/10 text-emerald-forest flex items-center justify-center">
                  <span className="material-symbols-outlined">shopping_basket</span>
                </div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-center text-emerald-forest">Buyer</span>
              </div>
            </div>
          </div>
        </section>

        {/* Features Bento Grid */}
        <section className="w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-24" id="solutions">
          <h2 className="text-3xl md:text-4xl font-bold text-emerald-forest mb-12 text-center md:text-left">Platform Capabilities</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 auto-rows-[420px]">
            {/* AI Quality Analysis (Large) */}
            <div className="lg:col-span-2 relative rounded-[2rem] overflow-hidden premium-shadow group">
              <div 
                className="absolute inset-0 bg-cover bg-center transition-transform duration-1000 group-hover:scale-105" 
                style={{ 
                  backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBeNRh32MZi4bYVRZ3ynV97fF-c_O_EP6XXusoW4u9ZqCAPe9vQsvbA9tNZA_5GqLsmaFmdIz28E6Ieea1XmgU0ETo7Vz1K0AzsjOZEwIZozpMhHfBMEo1BL9DLksD7WHs-NSPaBojDezaigXnQjTYYRXcCRaFZaJNcmI6mZ2au2Ziqr9TXiNnZ8jBpdLWX2LGF43SxkHiOqaeEhUrBcybxTj4yviLF2B8QexavQ3r7U2aBfxF4h3ww')" 
                }}
              ></div>
              <div className="absolute inset-0 bg-gradient-to-t from-emerald-forest/95 via-emerald-forest/40 to-transparent"></div>
              <div className="absolute bottom-0 left-0 p-10">
                <div className="glass-panel rounded-xl p-3 w-max mb-5">
                  <span className="material-symbols-outlined text-digital-mint">document_scanner</span>
                </div>
                <h3 className="text-2xl font-bold text-white mb-2">AI Maturity Analysis</h3>
                <p className="text-surface-container-high text-sm max-w-lg">
                  Transfer learning models evaluate guava harvest maturity stages with high precision, assisting packhouse intake using our validated ResNet18 baseline model.
                </p>
              </div>
            </div>

            {/* Produce Intelligence */}
            <div className="glass-panel rounded-[2rem] p-10 premium-shadow flex flex-col justify-between">
              <div>
                <div className="bg-emerald-forest/10 rounded-xl p-3 w-max mb-6">
                  <span className="material-symbols-outlined text-emerald-forest">monitoring</span>
                </div>
                <div className="flex justify-between items-start">
                  <h3 className="text-xl font-bold text-emerald-forest mb-2">Produce Intelligence</h3>
                  <span className="bg-emerald-forest/10 text-emerald-forest text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded">Future Integration</span>
                </div>
                <p className="text-on-surface-variant text-sm">Historical benchmarking and predictive trend lines for yield optimization.</p>
              </div>
              {/* Abstract Chart representation */}
              <div className="w-full h-36 flex items-end gap-3 mt-4">
                <div className="w-1/5 bg-surface-variant rounded-t-lg h-[40%]"></div>
                <div className="w-1/5 bg-surface-variant rounded-t-lg h-[60%]"></div>
                <div className="w-1/5 bg-digital-mint rounded-t-lg h-[85%] relative shadow-lg shadow-digital-mint/30">
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-white text-emerald-forest text-[10px] font-bold px-2 py-1 rounded shadow-sm border border-outline-variant/30">+24%</div>
                </div>
                <div className="w-1/5 bg-surface-variant rounded-t-lg h-[50%]"></div>
                <div className="w-1/5 bg-surface-variant rounded-t-lg h-[70%]"></div>
              </div>
            </div>

            {/* Supply Chain Visibility */}
            <div className="glass-panel rounded-[2rem] p-10 premium-shadow flex flex-col justify-between relative overflow-hidden">
              <div className="z-10 relative">
                <div className="bg-emerald-forest/10 rounded-xl p-3 w-max mb-6">
                  <span className="material-symbols-outlined text-emerald-forest">share_location</span>
                </div>
                <div className="flex justify-between items-start">
                  <h3 className="text-xl font-bold text-emerald-forest mb-2">Logistics Visibility</h3>
                  <span className="bg-amber-500/10 text-amber-800 text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded">Simulation</span>
                </div>
                <p className="text-on-surface-variant text-sm">Geospatial shipment tracking and cold chain logistics maps in transit.</p>
              </div>
              {/* Abstract Map background */}
              <div 
                className="absolute bottom-0 right-0 w-[120%] h-[60%] bg-cover opacity-50" 
                style={{ 
                  backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBqI91gdHrUTYgnQ6F2t-hZpsxFOTjSANpVNidMGsAhb7EJItdJt5FPHsxKzrr0KQoD-8QSjWCkPmUzdHTarSLBoXTYPX-2artDWqcuQCG-R3A04rWuMGCBBgQVbL6LRhodFdZLj0FE2T5nYV6oEWtBjDBbKKB_Oy3_eoqqnXKA06uxGcbAungdLHQbW8I5bH1Xe4evGEwOBc5YzOvEUVgrJvpCFIT7Ez7BEFEHOk8vIE9eMnkEeJ8x')" 
                }}
              ></div>
            </div>

            {/* Future Cold Chain Monitoring */}
            <div className="lg:col-span-2 glass-panel bg-surface-container-low/50 rounded-[2rem] p-10 premium-shadow flex flex-col md:flex-row items-center gap-10">
              <div className="flex-1">
                <div className="bg-white rounded-xl p-3 w-max mb-6 shadow-sm border border-outline-variant/20">
                  <span className="material-symbols-outlined text-digital-mint">ac_unit</span>
                </div>
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-bold text-emerald-forest">Future Cold Chain Monitoring</h3>
                  <span className="bg-emerald-forest/10 text-emerald-forest text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded">Future Integration</span>
                </div>
                <p className="text-on-surface-variant text-sm mb-6">
                  Deploying IoT telemetry sensors to maintain optimal climatic conditions. Our upcoming module ensures cold-chain integrity during transit.
                </p>
                <button className="text-emerald-forest font-bold text-xs flex items-center gap-2 hover:text-digital-mint transition-colors group">
                  Read the Whitepaper 
                  <span className="material-symbols-outlined text-sm transform transition-transform group-hover:translate-x-1">arrow_forward</span>
                </button>
              </div>
              
              {/* Logistics Chips Visual */}
              <div className="w-full md:w-auto grid grid-cols-2 gap-4 shrink-0">
                <div className="bg-white p-4 rounded-xl border border-outline-variant/20 flex flex-col gap-1 min-w-[130px] shadow-sm">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-outline">Temp [Demo]</span>
                  <span className="text-xs text-emerald-forest flex items-center gap-1.5 font-bold font-mono">
                    <span className="w-2 h-2 rounded-full bg-digital-mint"></span> 2.4°C
                  </span>
                </div>
                <div className="bg-white p-4 rounded-xl border border-outline-variant/20 flex flex-col gap-1 min-w-[130px] shadow-sm">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-outline">Humidity [Demo]</span>
                  <span className="text-xs text-emerald-forest flex items-center gap-1.5 font-bold font-mono">
                    <span className="w-2 h-2 rounded-full bg-digital-mint"></span> 88%
                  </span>
                </div>
                <div className="bg-white p-4 rounded-xl border border-outline-variant/20 flex flex-col gap-1 min-w-[130px] shadow-sm">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-outline">Ethylene [Demo]</span>
                  <span className="text-xs text-emerald-forest flex items-center gap-1.5 font-bold font-mono">
                    <span className="w-2 h-2 rounded-full bg-error"></span> Alert
                  </span>
                </div>
                <div className="bg-white p-4 rounded-xl border border-outline-variant/20 flex flex-col gap-1 min-w-[130px] shadow-sm">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-outline">ETA [Demo]</span>
                  <span className="text-xs text-emerald-forest flex items-center gap-1.5 font-bold font-mono">
                    <span className="w-2 h-2 rounded-full bg-emerald-forest"></span> 4 Hrs
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-emerald-forest w-full py-16 flex flex-col items-center justify-center px-margin-desktop text-center text-white/80">
        <div className="text-xl font-bold text-digital-mint mb-8 flex items-center gap-2 justify-center">
          <span className="material-symbols-outlined">agriculture</span>
          AgriChain AI
        </div>
        <nav className="flex flex-wrap justify-center gap-8 mb-10 text-white/60">
          <a className="font-semibold text-xs hover:text-digital-mint underline decoration-2 underline-offset-4 transition-colors" href="#">Network Status</a>
          <a className="font-semibold text-xs hover:text-digital-mint underline decoration-2 underline-offset-4 transition-colors" href="#">Data Privacy</a>
          <a className="font-semibold text-xs hover:text-digital-mint underline decoration-2 underline-offset-4 transition-colors" href="#">Terms of Service</a>
          <a className="font-semibold text-xs hover:text-digital-mint underline decoration-2 underline-offset-4 transition-colors" href="#">AI Ethics</a>
        </nav>
        <div className="text-xs text-white/40">
          © 2026 AgriChain AI. Precision Logistics & Organic Vitality.
        </div>
      </footer>

      {/* Stakeholder Role Selection Modal */}
      <RoleSelectionModal
        isOpen={showRoleModal}
        activeRole={activeRole}
        onSelectRole={handleRoleSelect}
        onClose={() => setShowRoleModal(false)}
        canDismiss={canDismissRoleModal}
      />
    </div>
  );
}
