"use client";
import React, { useState } from "react";
import { createDemoOrder } from "../lib/api";

export default function OrderPurchaseModal({
  listing,
  isOpen,
  onClose,
  onOrderSuccess,
  defaultBuyerName = "Demo Buyer",
  defaultBuyerOrg = "Punjab Agro Traders",
}) {
  const [quantity, setQuantity] = useState(10);
  const [buyerName, setBuyerName] = useState(defaultBuyerName);
  const [buyerOrg, setBuyerOrg] = useState(defaultBuyerOrg);
  const [destination, setDestination] = useState("Azadpur APMC Mandi, Delhi");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [confirmedOrder, setConfirmedOrder] = useState(null);

  if (!isOpen || !listing) return null;

  const available = listing.available_crates || 0;
  const unitPrice = listing.price_per_crate_inr || 0;
  const crateWeight = listing.crate_weight_kg || 20.0;
  const calculatedTotal = quantity > 0 ? quantity * unitPrice : 0;
  const calculatedWeight = quantity > 0 ? quantity * crateWeight : 0;

  const handleQuantityChange = (val) => {
    const num = parseInt(val, 10);
    if (isNaN(num)) {
      setQuantity(1);
    } else {
      setQuantity(Math.max(1, Math.min(available, num)));
    }
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (quantity <= 0) {
      setError("Please select at least 1 crate.");
      return;
    }
    if (quantity > available) {
      setError(`Cannot exceed available stock of ${available} crates.`);
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const orderPayload = {
        listing_id: listing.id,
        quantity_crates: quantity,
        buyer_name: buyerName.trim() || "Demo Buyer",
        buyer_organization: buyerOrg.trim() || "Punjab Agro Traders",
        shipping_destination: destination.trim() || "Azadpur APMC Mandi, Delhi",
        idempotency_key: `client-${listing.id}-${Date.now()}-${Math.random().toString(36).substring(7)}`,
      };

      const result = await createDemoOrder(orderPayload);
      setConfirmedOrder(result);
      if (onOrderSuccess) {
        onOrderSuccess(result);
      }
    } catch (err) {
      setError(err.message || "Failed to place demo order. Please check backend connectivity.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setConfirmedOrder(null);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div 
        className="bg-white rounded-3xl max-w-xl w-full p-6 md:p-8 border border-outline-variant/60 shadow-2xl max-h-[92vh] overflow-y-auto"
        role="dialog"
        aria-modal="true"
      >
        {/* Confirmed Order State */}
        {confirmedOrder ? (
          <div className="flex flex-col items-center text-center py-4">
            <div className="w-16 h-16 rounded-full bg-digital-mint/20 text-digital-mint flex items-center justify-center mb-4 border border-digital-mint/30">
              <span className="material-symbols-outlined text-3xl">task_alt</span>
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-digital-mint/15 text-emerald-forest border border-digital-mint/30 text-[10px] font-bold uppercase tracking-wider mb-2">
              Order Confirmed (Demo Simulation)
            </div>

            <h3 className="text-xl font-bold text-emerald-forest">
              Demo Purchase Order Placed!
            </h3>
            <p className="text-xs text-on-surface-variant mt-1 max-w-sm">
              Your demo purchase order has been verified and recorded in the AgriChain session ledger.
            </p>

            <div className="w-full bg-surface-container-low rounded-2xl p-5 my-6 text-left border border-outline-variant/40 flex flex-col gap-2.5 text-xs">
              <div className="flex justify-between items-center pb-2 border-b border-outline-variant/40">
                <span className="text-outline uppercase text-[10px] font-bold">Order Reference ID</span>
                <span className="font-mono font-bold text-primary text-sm">{confirmedOrder.id}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-on-surface-variant">Produce Lot:</span>
                <span className="font-bold text-primary">{confirmedOrder.produce_title}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-on-surface-variant">Quantity:</span>
                <span className="font-bold text-primary">{confirmedOrder.quantity_crates} Crates ({confirmedOrder.total_weight_kg} kg)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-on-surface-variant">Unit Price:</span>
                <span className="font-mono font-semibold">₹{confirmedOrder.unit_price_inr?.toLocaleString("en-IN")} / crate</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-outline-variant/40">
                <span className="text-outline uppercase text-[10px] font-bold">Authoritative Server Total:</span>
                <span className="font-mono font-bold text-emerald-forest text-base">₹{confirmedOrder.total_price_inr?.toLocaleString("en-IN")}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-on-surface-variant">Destination:</span>
                <span className="text-primary truncate max-w-[200px]">{confirmedOrder.shipping_destination}</span>
              </div>
            </div>

            <div className="w-full bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-[11px] text-amber-900 text-left mb-6">
              <div className="flex items-center gap-1.5 font-bold mb-0.5">
                <span className="material-symbols-outlined text-xs">info</span>
                Commercial Simulation Notice
              </div>
              {confirmedOrder.simulation_notice}
            </div>

            <button
              onClick={handleClose}
              className="w-full bg-emerald-forest hover:bg-primary text-white py-3 rounded-xl font-bold text-xs transition-colors shadow-md"
            >
              Done &amp; View Orders
            </button>
          </div>
        ) : (
          /* Order Placement Form */
          <div>
            <div className="flex justify-between items-start mb-4">
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-outline">B2B Verified Purchase</span>
                <h3 className="text-xl font-bold text-emerald-forest mt-0.5">
                  Confirm Demo Purchase Order
                </h3>
              </div>
              <button
                onClick={handleClose}
                className="p-1.5 rounded-xl text-on-surface-variant hover:bg-surface-container-high transition-colors"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            {/* Produce Lot Summary Card */}
            <div className="bg-surface-container-low rounded-2xl p-4 border border-outline-variant/40 mb-5 flex gap-4 items-center">
              <img
                src={listing.image_url}
                alt={listing.title}
                className="w-16 h-16 rounded-xl object-cover shrink-0 border border-outline-variant/40"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[9px] bg-digital-mint text-white font-bold uppercase tracking-wider px-2 py-0.5 rounded">
                    AI Verified: {listing.ripeness_stage}
                  </span>
                  <span className="text-[10px] text-outline font-mono">
                    Score: {(listing.softmax_score * 100).toFixed(1)}%
                  </span>
                </div>
                <h4 className="font-bold text-sm text-primary truncate mt-1">{listing.title}</h4>
                <p className="text-[11px] text-on-surface-variant truncate">
                  {listing.origin_name} · Stock: {available} Crates
                </p>
              </div>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-error/10 border border-error/30 text-error text-xs flex items-center gap-2">
                <span className="material-symbols-outlined text-sm shrink-0">error</span>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {/* Quantity Selector */}
              <div>
                <label className="text-xs font-bold text-primary block mb-1.5">
                  Order Quantity (Crates)
                </label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleQuantityChange(quantity - 5)}
                    disabled={quantity <= 1}
                    className="w-10 h-10 rounded-xl border border-outline-variant/60 hover:bg-surface-container-high flex items-center justify-center font-bold text-base disabled:opacity-40"
                  >
                    -
                  </button>
                  <input
                    type="number"
                    min={1}
                    max={available}
                    value={quantity}
                    onChange={(e) => handleQuantityChange(e.target.value)}
                    className="flex-1 bg-background border border-outline-variant rounded-xl p-2.5 text-center font-bold text-sm focus:outline-none focus:border-digital-mint"
                  />
                  <button
                    type="button"
                    onClick={() => handleQuantityChange(quantity + 5)}
                    disabled={quantity >= available}
                    className="w-10 h-10 rounded-xl border border-outline-variant/60 hover:bg-surface-container-high flex items-center justify-center font-bold text-base disabled:opacity-40"
                  >
                    +
                  </button>
                </div>
                <div className="flex justify-between items-center text-[10px] text-on-surface-variant mt-1.5 px-1">
                  <span>Available stock: {available} crates</span>
                  <span>Total weight: {calculatedWeight.toLocaleString("en-IN")} kg</span>
                </div>
              </div>

              {/* Price Calculation Box */}
              <div className="bg-emerald-forest/5 rounded-2xl p-4 border border-digital-mint/30 flex justify-between items-center">
                <div>
                  <span className="text-[10px] uppercase font-bold text-outline block">Calculated Total</span>
                  <span className="text-[11px] text-on-surface-variant font-mono">
                    {quantity} crates × ₹{unitPrice.toLocaleString("en-IN")}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-xl font-bold font-mono text-emerald-forest">
                    ₹{calculatedTotal.toLocaleString("en-IN")}
                  </span>
                  <span className="text-[9px] uppercase font-semibold text-outline block">INR Wholesale</span>
                </div>
              </div>

              {/* Destination & Buyer info */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-bold text-outline uppercase block mb-1">
                    Buyer Name
                  </label>
                  <input
                    type="text"
                    value={buyerName}
                    onChange={(e) => setBuyerName(e.target.value)}
                    required
                    className="w-full bg-background border border-outline-variant rounded-xl p-2.5 text-xs font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-outline uppercase block mb-1">
                    Organization / Firm
                  </label>
                  <input
                    type="text"
                    value={buyerOrg}
                    onChange={(e) => setBuyerOrg(e.target.value)}
                    className="w-full bg-background border border-outline-variant rounded-xl p-2.5 text-xs font-semibold focus:outline-none focus:border-digital-mint"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-bold text-outline uppercase block mb-1">
                  Delivery Destination
                </label>
                <input
                  type="text"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  required
                  className="w-full bg-background border border-outline-variant rounded-xl p-2.5 text-xs font-semibold focus:outline-none focus:border-digital-mint"
                />
              </div>

              {/* Transparency Notice */}
              <div className="bg-surface-container-low rounded-xl p-3 border border-outline-variant/30 text-[10px] text-on-surface-variant leading-relaxed">
                <span className="font-bold text-primary">Demo Order Notice: </span>
                No real payments are collected. Submitting will validate inventory and record a verified order in the AgriChain session ledger.
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 mt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="flex-1 border border-outline-variant/60 hover:bg-surface-container-high py-2.5 rounded-xl font-bold text-xs text-primary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || available <= 0}
                  className="flex-2 bg-emerald-forest hover:bg-primary text-white py-2.5 rounded-xl font-bold text-xs transition-colors flex items-center justify-center gap-2 shadow-md disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                      Validating &amp; Recording...
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-sm">shopping_bag</span>
                      Confirm Demo Order (₹{calculatedTotal.toLocaleString("en-IN")})
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
