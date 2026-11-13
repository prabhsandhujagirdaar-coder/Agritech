"use client";
import React, { useState, useEffect } from "react";
import { SUPPORTED_ROLES, ROLE_DEFAULT_TABS, Z_INDEX } from "../lib/constants";

export { SUPPORTED_ROLES, ROLE_DEFAULT_TABS };

export default function RoleSelectionModal({
  isOpen,
  activeRole = "Farmer",
  onSelectRole,
  onClose,
  canDismiss = true,
}) {
  const [selectedRoleId, setSelectedRoleId] = useState(activeRole || "Farmer");

  // Keep local selection in sync with activeRole when modal opens
  useEffect(() => {
    if (activeRole) {
      setSelectedRoleId(activeRole);
    }
  }, [activeRole, isOpen]);

  // Keyboard navigation: Enter to confirm, Escape to cancel (if dismissible)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape" && canDismiss && onClose) {
        onClose();
      } else if (e.key === "Enter") {
        const role = SUPPORTED_ROLES.find((r) => r.id === selectedRoleId) || SUPPORTED_ROLES[0];
        if (role && onSelectRole) {
          onSelectRole(role.id, role.defaultTab);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedRoleId, canDismiss, onClose, onSelectRole]);

  if (!isOpen) return null;

  const currentSelectedRole =
    SUPPORTED_ROLES.find((r) => r.id === selectedRoleId) || SUPPORTED_ROLES[0];

  const handleConfirm = () => {
    if (currentSelectedRole && onSelectRole) {
      onSelectRole(currentSelectedRole.id, currentSelectedRole.defaultTab);
    }
  };

  return (
    <div
      className="fixed inset-0 flex items-center justify-center p-3 sm:p-6 bg-black/70 backdrop-blur-sm animate-fade-in"
      style={{ zIndex: Z_INDEX.MODAL_BACKDROP }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="role-modal-title"
    >
      <div
        className="bg-white rounded-3xl max-w-5xl w-full p-5 sm:p-8 border border-outline-variant/60 shadow-2xl max-h-[92vh] overflow-y-auto scrollbar-thin flex flex-col justify-between relative"
        style={{ zIndex: Z_INDEX.MODAL_CONTENT }}
      >
        {/* Onboarding Header */}
        <div>
          <div className="flex justify-between items-start gap-4 pb-4 border-b border-outline-variant/40">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-digital-mint/15 text-emerald-forest border border-digital-mint/30 text-[10px] font-bold uppercase tracking-wider mb-2">
                <span className="material-symbols-outlined text-xs">psychiatry</span>
                AgriChain AI • Predictive Multi-Fruit Supply Platform
              </div>
              <h2 id="role-modal-title" className="text-xl sm:text-2xl font-extrabold text-emerald-forest tracking-tight">
                Welcome to AgriChain AI
              </h2>
              <p className="text-xs text-on-surface-variant mt-1.5 max-w-2xl leading-relaxed">
                Select your role to access your personalized workspace. Each stakeholder enters a dedicated environment tailored strictly to their workflows, tools, and telemetry.
              </p>
            </div>

            {canDismiss && onClose && (
              <button
                onClick={onClose}
                className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container-high transition-colors shrink-0"
                aria-label="Close modal"
                title="Close (Esc)"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            )}
          </div>

          {/* Balanced 5 Roles Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4 my-6">
            {SUPPORTED_ROLES.map((role) => {
              const isSelected = selectedRoleId === role.id;
              const isCurrentlyActive = activeRole === role.id;

              return (
                <div
                  key={role.id}
                  onClick={() => setSelectedRoleId(role.id)}
                  onDoubleClick={handleConfirm}
                  className={`cursor-pointer rounded-2xl p-4 sm:p-5 border-2 transition-all duration-200 flex flex-col justify-between group relative select-none ${
                    isSelected
                      ? "border-digital-mint bg-digital-mint/5 shadow-md shadow-digital-mint/15 ring-2 ring-digital-mint/30"
                      : `border-outline-variant/60 bg-surface-container-low/30 ${role.borderHover} hover:bg-white hover:shadow-sm`
                  }`}
                >
                  <div>
                    {/* Top row: Icon + Status Pills */}
                    <div className="flex justify-between items-start mb-3">
                      <div className={`w-11 h-11 rounded-xl ${role.iconBg} flex items-center justify-center shrink-0 shadow-xs`}>
                        <span className="material-symbols-outlined text-2xl">{role.icon}</span>
                      </div>

                      <div className="flex flex-col items-end gap-1">
                        {/* Radio selection indicator */}
                        <div
                          className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                            isSelected
                              ? "border-digital-mint bg-digital-mint text-white"
                              : "border-outline-variant group-hover:border-outline"
                          }`}
                        >
                          {isSelected && <span className="material-symbols-outlined text-xs">check</span>}
                        </div>

                        {isCurrentlyActive && (
                          <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                            Active Role
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Role Title and Badge */}
                    <h3 className="font-bold text-base text-primary leading-tight group-hover:text-emerald-forest transition-colors">
                      {role.title}
                    </h3>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-outline mt-0.5">
                      {role.badge}
                    </div>

                    {/* Description */}
                    <p className="text-xs text-on-surface-variant mt-2 leading-relaxed">
                      {role.description}
                    </p>
                  </div>

                  {/* Card Bottom Meta */}
                  <div className="mt-4 pt-3 border-t border-outline-variant/30 flex justify-between items-center text-[11px]">
                    <span className="font-medium text-outline">
                      Default: <span className="text-primary font-semibold">{role.subtitle}</span>
                    </span>
                    <span
                      className={`font-bold transition-colors ${
                        isSelected ? "text-emerald-forest" : "text-outline group-hover:text-emerald-forest"
                      }`}
                    >
                      {isSelected ? "Selected" : "Click to select"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom Actions and Transparency Footer */}
        <div className="pt-4 border-t border-outline-variant/40 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 mt-2">
          {/* Transparency note */}
          <div className="flex items-center gap-2.5 text-xs text-on-surface-variant">
            <span className="material-symbols-outlined text-digital-mint text-base shrink-0">verified_user</span>
            <span>
              Perspective: <strong className="text-primary">{currentSelectedRole?.title}</strong> ({currentSelectedRole?.subtitle})
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3 justify-end">
            {canDismiss && onClose && (
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 rounded-xl border border-outline-variant/70 hover:bg-surface-container-high text-on-surface-variant font-bold text-xs uppercase tracking-wider transition-colors"
              >
                Cancel
              </button>
            )}

            <button
              type="button"
              onClick={handleConfirm}
              className="px-6 py-2.5 rounded-xl bg-emerald-forest hover:bg-primary text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-sm transition-all hover:shadow-md cursor-pointer"
            >
              <span>Continue to {currentSelectedRole?.title} Workspace</span>
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
