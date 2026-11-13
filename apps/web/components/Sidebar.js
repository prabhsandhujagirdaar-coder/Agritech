"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getRoleConfig } from "../lib/roleConfig";

export default function Sidebar({
  activeTab,
  setActiveTab,
  mobileOpen = false,
  setMobileOpen,
  activeRole = "Farmer",
  onOpenRoleSelector,
}) {
  const [status, setStatus] = useState("checking");
  const roleConfig = getRoleConfig(activeRole);
  const navItems = roleConfig.navItems || [];

  const checkStatus = async () => {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        if (data.status === "healthy" || data.api_status === "online") {
          setStatus("online");
          return;
        }
      }
      setStatus("offline");
    } catch {
      setStatus("offline");
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSelect = (id) => {
    setActiveTab(id);
    if (setMobileOpen) {
      setMobileOpen(false);
    }
  };

  const navContent = (isMobile = false) => (
    <>
      {/* Header */}
      <div className="px-6 pb-4 mb-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-forest flex items-center justify-center shrink-0 shadow-sm">
            <span className="material-symbols-outlined text-white filled">psychiatry</span>
          </div>
          <div>
            <h1 className="font-extrabold text-base text-primary leading-tight">AgriChain AI</h1>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`w-2 h-2 rounded-full ${status === "online" ? "bg-digital-mint animate-pulse" : status === "checking" ? "bg-amber-500 animate-pulse" : "bg-error"}`} />
              <p className="text-[10px] font-bold tracking-wider uppercase text-on-surface-variant">
                {status === "online" ? "FastAPI Online" : status === "checking" ? "Checking Status..." : "FastAPI Offline"}
              </p>
            </div>
          </div>
        </div>

        {isMobile && setMobileOpen && (
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-2 rounded-xl text-on-surface-variant hover:bg-surface-container-high transition-colors"
            aria-label="Close navigation"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        )}
      </div>

      {/* Role Indicator Card */}
      <div className="mx-4 mb-4 p-3.5 bg-surface-container-low rounded-2xl border border-outline-variant/60 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`w-9 h-9 rounded-xl ${roleConfig.iconBg} flex items-center justify-center shrink-0 shadow-xs`}>
            <span className="material-symbols-outlined text-lg">{roleConfig.icon}</span>
          </div>
          <div className="min-w-0">
            <div className="text-[9px] uppercase font-bold tracking-wider text-outline flex items-center gap-1">
              <span>Workspace</span>
              <span className="w-1.5 h-1.5 rounded-full bg-digital-mint" />
            </div>
            <div className="text-xs font-extrabold text-primary truncate" title={roleConfig.displayTitle}>
              {roleConfig.title}
            </div>
            <div className="text-[10px] text-on-surface-variant truncate">
              {roleConfig.subtitle}
            </div>
          </div>
        </div>
        {onOpenRoleSelector && (
          <button
            onClick={onOpenRoleSelector}
            className="text-[10px] font-bold text-emerald-forest hover:text-digital-mint bg-white hover:bg-emerald-50/60 border border-outline-variant/70 px-2.5 py-1.5 rounded-xl transition-all shrink-0 flex items-center gap-1 shadow-xs cursor-pointer"
            title="Switch stakeholder workspace"
          >
            <span>Switch</span>
            <span className="material-symbols-outlined text-[13px]">swap_horiz</span>
          </button>
        )}
      </div>

      {/* Role Navigation Header */}
      <div className="px-5 mb-1.5 flex items-center justify-between">
        <span className="text-[9px] font-bold uppercase tracking-wider text-outline/80">
          {roleConfig.title} Workspace Navigation
        </span>
        <span className="text-[8px] font-bold uppercase px-1.5 py-0.5 rounded bg-emerald-forest/10 text-emerald-forest">
          {navItems.length} Views
        </span>
      </div>

      {/* Main Role-Specific Navigation */}
      <div className="flex-1 flex flex-col gap-1.5 overflow-y-auto px-4 py-1 scrollbar-thin">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleSelect(item.id)}
              className={`w-full px-3.5 py-3 flex items-center justify-between rounded-xl text-left transition-all duration-150 group cursor-pointer ${
                isActive
                  ? "bg-emerald-forest text-white font-bold shadow-sm ring-1 ring-emerald-forest/30"
                  : "text-on-surface-variant hover:bg-surface-container-high hover:text-primary"
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className={`material-symbols-outlined text-lg shrink-0 ${isActive ? "text-white" : "text-emerald-forest group-hover:text-primary"}`}>
                  {item.icon}
                </span>
                <div className="min-w-0">
                  <div className={`text-xs font-semibold leading-tight truncate ${isActive ? "text-white font-bold" : "text-primary"}`}>
                    {item.label}
                  </div>
                  {item.description && (
                    <div className={`text-[10px] truncate leading-tight mt-0.5 ${isActive ? "text-white/80" : "text-outline"}`}>
                      {item.description}
                    </div>
                  )}
                </div>
              </div>
              {item.badge && (
                <span className={`text-[8px] uppercase tracking-wider font-extrabold px-1.5 py-0.5 rounded-full shrink-0 ml-1 ${
                  isActive ? "bg-white/20 text-white" : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                }`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Switch Role Quick Button & Home */}
      <div className="px-4 pt-3 border-t border-outline-variant/60 flex flex-col gap-1">
        {onOpenRoleSelector && (
          <button
            onClick={onOpenRoleSelector}
            className="w-full px-3.5 py-2.5 flex items-center gap-2.5 rounded-xl text-left text-xs font-semibold text-emerald-forest hover:bg-emerald-50 transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-base">swap_horiz</span>
            <span>Switch Role Workspace</span>
          </button>
        )}
        <Link
          href="/"
          className="w-full px-3.5 py-2.5 flex items-center gap-2.5 rounded-xl text-left text-xs text-on-surface-variant hover:bg-surface-container-high transition-all"
        >
          <span className="material-symbols-outlined text-base">home</span>
          <span>Back to Landing Page</span>
        </Link>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop Sidebar: hidden on mobile, visible on md+ */}
      <nav className="hidden md:flex flex-col bg-surface border-r border-outline-variant h-screen w-72 shrink-0 py-6 z-20">
        {navContent(false)}
      </nav>

      {/* Mobile Drawer Backdrop and Overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 md:hidden transition-opacity"
          onClick={() => setMobileOpen && setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Slide-over Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 w-72 max-w-[85vw] bg-surface z-50 flex flex-col py-6 shadow-2xl transform transition-transform duration-300 ease-in-out md:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {navContent(true)}
      </aside>
    </>
  );
}
