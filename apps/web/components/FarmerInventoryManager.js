"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  fetchCropCatalogue,
  fetchFarmerInventory,
  createInventoryItem,
  updateInventoryItem,
  deleteInventoryItem,
} from "../lib/api";

export default function FarmerInventoryManager({ currentFarmerId = "FARMER-PB-001", role = "farmer" }) {
  const [crops, setCrops] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filter state
  const [filterCrop, setFilterCrop] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

  // Form state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedCrop, setSelectedCrop] = useState("guava");
  const [crateQuantity, setCrateQuantity] = useState(50);
  const [pricePerCrate, setPricePerCrate] = useState(450);
  const [location, setLocation] = useState("Abohar Orchard Gate, Punjab");
  const [harvestDate, setHarvestDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState(null);

  // Edit modal state
  const [editingItem, setEditingItem] = useState(null);
  const [editQuantity, setEditQuantity] = useState(1);
  const [editPrice, setEditPrice] = useState(1);
  const [editStatus, setEditStatus] = useState("available");
  const [editLocation, setEditLocation] = useState("");
  const [updating, setUpdating] = useState(false);

  // Delete modal state
  const [deletingId, setDeletingId] = useState(null);

  // Auth headers
  const authHeaders = useMemo(() => ({
    "X-Role": role.toLowerCase(),
    "X-Farmer-ID": currentFarmerId,
  }), [role, currentFarmerId]);

  // Load initial data
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cropsData, invData] = await Promise.all([
        fetchCropCatalogue(),
        fetchFarmerInventory({ farmer_id: currentFarmerId }, authHeaders),
      ]);
      setCrops(cropsData || []);
      setInventory(invData || []);
    } catch (err) {
      setError(err.message || "Failed to load farmer inventory data.");
    } finally {
      setLoading(false);
    }
  }, [currentFarmerId, authHeaders]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Client-side estimated preview
  const estimatedTotal = useMemo(() => {
    const q = parseInt(crateQuantity, 10) || 0;
    const p = parseFloat(pricePerCrate) || 0;
    return q > 0 && p > 0 ? (q * p).toLocaleString("en-IN") : "0";
  }, [crateQuantity, pricePerCrate]);

  // Selected crop details
  const activeCropMeta = useMemo(() => {
    return crops.find((c) => c.crop_id === selectedCrop) || crops[0] || null;
  }, [crops, selectedCrop]);

  // Summary Metrics
  const metrics = useMemo(() => {
    const totalCrates = inventory.reduce((sum, item) => sum + (item.crate_quantity || 0), 0);
    const totalVal = inventory.reduce((sum, item) => sum + (item.total_stock_value || 0), 0);
    const availableCrates = inventory
      .filter((i) => i.status === "available")
      .reduce((sum, item) => sum + (item.crate_quantity || 0), 0);

    return {
      totalCrates,
      totalVal: Math.round(totalVal).toLocaleString("en-IN"),
      availableCrates,
      totalLots: inventory.length,
    };
  }, [inventory]);

  // Filtered inventory list
  const filteredInventory = useMemo(() => {
    return inventory.filter((item) => {
      if (filterCrop !== "all" && item.crop_type !== filterCrop) return false;
      if (filterStatus !== "all" && item.status !== filterStatus) return false;
      return true;
    });
  }, [inventory, filterCrop, filterStatus]);

  // Handle Form Submission
  const handleAddStock = async (e) => {
    e.preventDefault();
    setFormError(null);

    const qty = parseInt(crateQuantity, 10);
    const price = parseFloat(pricePerCrate);

    if (!qty || qty <= 0) {
      setFormError("Crate quantity must be a positive integer greater than zero.");
      return;
    }
    if (!price || price <= 0) {
      setFormError("Price per crate must be a positive number greater than zero.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        farmer_id: currentFarmerId,
        crop_type: selectedCrop,
        crate_quantity: qty,
        price_per_crate: price,
        description: description.trim() || undefined,
        harvest_date: harvestDate || undefined,
        location: location.trim() || undefined,
        status: "available",
      };

      const created = await createInventoryItem(payload, authHeaders);
      setInventory((prev) => [created, ...prev]);
      setSuccessMsg(`Successfully added ${created.crate_quantity} crates of ${created.crop_type.toUpperCase()} to your stock ledger.`);
      setTimeout(() => setSuccessMsg(null), 4000);

      // Reset form
      setCrateQuantity(50);
      setPricePerCrate(450);
      setDescription("");
      setIsFormOpen(false);
    } catch (err) {
      setFormError(err.message || "Failed to create inventory item.");
    } finally {
      setSubmitting(false);
    }
  };

  // Open Edit Modal
  const openEditModal = (item) => {
    setEditingItem(item);
    setEditQuantity(item.crate_quantity);
    setEditPrice(item.price_per_crate);
    setEditStatus(item.status);
    setEditLocation(item.location || "");
  };

  // Handle Update
  const handleUpdate = async () => {
    if (!editingItem) return;
    const qty = parseInt(editQuantity, 10);
    const price = parseFloat(editPrice);
    if (!qty || qty <= 0 || !price || price <= 0) {
      alert("Quantity and price must be positive numbers greater than 0.");
      return;
    }

    setUpdating(true);
    try {
      const updates = {
        crate_quantity: qty,
        price_per_crate: price,
        status: editStatus,
        location: editLocation,
      };
      const updated = await updateInventoryItem(editingItem.id, updates, authHeaders);
      setInventory((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
      setEditingItem(null);
      setSuccessMsg(`Updated inventory item ${updated.id}. Value recalculated: ₹${updated.total_stock_value.toLocaleString("en-IN")}`);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      alert(err.message || "Failed to update item.");
    } finally {
      setUpdating(false);
    }
  };

  // Handle Delete
  const handleDelete = async (id) => {
    if (!confirm(`Are you sure you want to remove stock record ${id}?`)) return;
    setDeletingId(id);
    try {
      await deleteInventoryItem(id, authHeaders);
      setInventory((prev) => prev.filter((i) => i.id !== id));
      setSuccessMsg(`Stock record ${id} removed.`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      alert(err.message || "Failed to delete item.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="bg-white rounded-2xl p-6 border border-outline-variant/60 premium-shadow flex flex-col gap-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-outline-variant/40 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-digital-mint text-2xl">warehouse</span>
            <h3 className="font-bold text-emerald-forest text-base uppercase tracking-wide">
              Farmer Stock &amp; Inventory Management
            </h3>
            <span className="bg-digital-mint/15 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-digital-mint/30">
              Active Ledger
            </span>
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            Authoritative produce inventory for <strong className="text-slate-800">{currentFarmerId}</strong>. Server-side valuations &amp; marketplace synchronization.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsFormOpen(!isFormOpen)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm ${
              isFormOpen
                ? "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300"
                : "bg-digital-mint text-white hover:bg-emerald-600 shadow-digital-mint/20"
            }`}
          >
            <span className="material-symbols-outlined text-sm">{isFormOpen ? "close" : "add_circle"}</span>
            {isFormOpen ? "Cancel" : "Add New Stock"}
          </button>
          <button
            onClick={loadData}
            title="Refresh Inventory"
            className="p-2 rounded-xl border border-outline-variant/60 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <span className={`material-symbols-outlined text-sm ${loading ? "animate-spin" : ""}`}>refresh</span>
          </button>
        </div>
      </div>

      {/* Feedback Messages */}
      {successMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs font-semibold flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-emerald-600">check_circle</span>
          {successMsg}
        </div>
      )}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs font-semibold flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-red-600">error</span>
          {error}
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-50 border border-slate-200/70 rounded-xl p-4">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Total Crates in Stock</span>
          <div className="text-xl font-extrabold text-emerald-950 mt-1">{metrics.totalCrates}</div>
          <span className="text-[10px] text-slate-500">{metrics.totalLots} recorded lots</span>
        </div>
        <div className="bg-emerald-50/50 border border-emerald-100 rounded-xl p-4">
          <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block">Available for Sale</span>
          <div className="text-xl font-extrabold text-emerald-700 mt-1">{metrics.availableCrates} crates</div>
          <span className="text-[10px] text-emerald-600">Market-ready intake</span>
        </div>
        <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-4">
          <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider block">Total Stock Valuation</span>
          <div className="text-xl font-extrabold text-blue-900 mt-1">₹{metrics.totalVal}</div>
          <span className="text-[10px] text-blue-600">Server calculated</span>
        </div>
        <div className="bg-purple-50/50 border border-purple-100 rounded-xl p-4">
          <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider block">Farmer Tenant ID</span>
          <div className="text-sm font-mono font-bold text-purple-900 mt-1 truncate">{currentFarmerId}</div>
          <span className="text-[10px] text-purple-600">Role: {role.toUpperCase()}</span>
        </div>
      </div>

      {/* Add Stock Collapsible Form */}
      {isFormOpen && (
        <form onSubmit={handleAddStock} className="bg-emerald-50/30 border border-digital-mint/40 rounded-2xl p-5 flex flex-col gap-4 animate-fade-in">
          <div className="flex items-center justify-between border-b border-digital-mint/20 pb-3">
            <h4 className="font-bold text-emerald-900 text-sm flex items-center gap-1.5">
              <span className="material-symbols-outlined text-digital-mint text-base">post_add</span>
              Record New Produce Stock
            </h4>
            <span className="text-[11px] text-slate-500">All prices and quantities subject to server-side integrity validation</span>
          </div>

          {formError && (
            <div className="p-2.5 bg-red-100/80 border border-red-300 rounded-lg text-red-800 text-xs font-semibold">
              ⚠️ {formError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Crop Picker */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Select Produce Crop <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedCrop}
                onChange={(e) => setSelectedCrop(e.target.value)}
                className="w-full text-xs font-semibold p-2.5 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-digital-mint outline-none"
              >
                {crops.map((c) => (
                  <option key={c.crop_id} value={c.crop_id}>
                    {c.name} ({c.primary_variety})
                  </option>
                ))}
              </select>
              {activeCropMeta && (
                <div className="mt-1.5 flex items-center gap-1">
                  {activeCropMeta.ai_classification_available ? (
                    <span className="text-[9px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded border border-emerald-300">
                      ✓ AI Inspection Active ({activeCropMeta.ai_model})
                    </span>
                  ) : activeCropMeta.ai_task === "detection_only" ? (
                    <span className="text-[9px] bg-amber-100 text-amber-800 font-bold px-1.5 py-0.5 rounded border border-amber-300">
                      ⚡ Object Detection Only ({activeCropMeta.ai_model})
                    </span>
                  ) : (
                    <span className="text-[9px] bg-slate-100 text-slate-700 font-medium px-1.5 py-0.5 rounded border border-slate-300">
                      Commercial Trading (No AI Model)
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Crate Quantity */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Quantity (Crates) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={crateQuantity}
                onChange={(e) => setCrateQuantity(e.target.value)}
                className="w-full text-xs font-semibold p-2.5 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-digital-mint outline-none"
                placeholder="e.g. 100"
                required
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Positive integers only (&gt; 0)</span>
            </div>

            {/* Price per Crate */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Price Per Crate (₹ INR) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                min="1"
                step="0.5"
                value={pricePerCrate}
                onChange={(e) => setPricePerCrate(e.target.value)}
                className="w-full text-xs font-semibold p-2.5 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-digital-mint outline-none"
                placeholder="e.g. 450"
                required
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Positive float in INR</span>
            </div>

            {/* Location */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Farm / Storage Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full text-xs font-semibold p-2.5 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-digital-mint outline-none"
                placeholder="e.g. Abohar Orchard Gate, Punjab"
              />
            </div>

            {/* Harvest Date */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Harvest Date
              </label>
              <input
                type="date"
                value={harvestDate}
                onChange={(e) => setHarvestDate(e.target.value)}
                className="w-full text-xs font-semibold p-2.5 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-digital-mint outline-none"
              />
            </div>

            {/* Estimated Total Display */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Estimated Lot Value
              </label>
              <div className="w-full text-xs font-bold p-2.5 bg-emerald-100/60 border border-emerald-300 rounded-xl text-emerald-900 flex items-center justify-between">
                <span>Total:</span>
                <span className="font-mono text-sm">₹{estimatedTotal}</span>
              </div>
              <span className="text-[9px] text-slate-500 mt-1 block">Calculated authoritatively on server upon submission</span>
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1">
              Produce Notes / Harvest Batch Description
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-digital-mint outline-none"
              placeholder="e.g. Grade A harvest ready for cold chain dispatch"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsFormOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-digital-mint text-white hover:bg-emerald-600 transition-all flex items-center gap-1.5 shadow-md shadow-digital-mint/20 disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <div className="w-3.5 h-3.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">save</span>
                  Save Stock Record
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-600">Crop:</span>
            <select
              value={filterCrop}
              onChange={(e) => setFilterCrop(e.target.value)}
              className="text-xs font-semibold bg-white border border-slate-300 rounded-lg px-2.5 py-1 outline-none"
            >
              <option value="all">All Crops ({crops.length})</option>
              {crops.map((c) => (
                <option key={c.crop_id} value={c.crop_id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-600">Status:</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-xs font-semibold bg-white border border-slate-300 rounded-lg px-2.5 py-1 outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="available">Available</option>
              <option value="reserved">Reserved</option>
              <option value="sold">Sold</option>
              <option value="unavailable">Unavailable</option>
            </select>
          </div>
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Showing <strong>{filteredInventory.length}</strong> of <strong>{inventory.length}</strong> listings
        </div>
      </div>

      {/* Inventory Table */}
      <div className="overflow-x-auto min-w-0 w-full scrollbar-thin">
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center gap-2">
            <div className="w-8 h-8 rounded-full border-2 border-digital-mint border-t-transparent animate-spin" />
            <span className="text-xs text-slate-500">Loading farmer stock records...</span>
          </div>
        ) : filteredInventory.length === 0 ? (
          <div className="py-12 flex flex-col items-center justify-center gap-2 text-center">
            <span className="material-symbols-outlined text-4xl text-slate-300">inventory_2</span>
            <div className="text-sm font-bold text-slate-600">No stock listings found</div>
            <p className="text-xs text-slate-400 max-w-sm">
              {inventory.length === 0
                ? "You haven't recorded any produce lots yet. Click 'Add New Stock' above to list your harvest."
                : "No stock records match your selected filters."}
            </p>
          </div>
        ) : (
          <table className="w-full text-left text-xs border-collapse min-w-[700px]">
            <thead>
              <tr className="border-b border-outline-variant/60 text-slate-500 font-semibold bg-slate-50/50">
                <th className="py-3 px-3">Lot ID</th>
                <th className="py-3 px-3">Crop &amp; Variety</th>
                <th className="py-3 px-3">AI Capability</th>
                <th className="py-3 px-3 text-right">Quantity</th>
                <th className="py-3 px-3 text-right">Price / Crate</th>
                <th className="py-3 px-3 text-right">Stock Valuation</th>
                <th className="py-3 px-3">Location &amp; Date</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredInventory.map((item) => {
                const cropMeta = crops.find((c) => c.crop_id === item.crop_type) || {};
                const isGuava = item.crop_type === "guava";
                const isBanana = item.crop_type === "banana";
                const isApple = item.crop_type === "apple";

                const statusStyles = {
                  available: "bg-emerald-100 text-emerald-800 border-emerald-300",
                  reserved: "bg-amber-100 text-amber-800 border-amber-300",
                  sold: "bg-blue-100 text-blue-800 border-blue-300",
                  unavailable: "bg-slate-100 text-slate-700 border-slate-300",
                };

                return (
                  <tr key={item.id} className="border-b border-outline-variant/30 hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-3 font-mono font-bold text-slate-800">
                      {item.id}
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-bold text-slate-900 capitalize">{cropMeta.name || item.crop_type}</div>
                      <div className="text-[10px] text-slate-500">{cropMeta.primary_variety || "Regional Variety"}</div>
                    </td>
                    <td className="py-3 px-3">
                      {isGuava ? (
                        <span className="text-[9px] bg-emerald-50 text-emerald-700 font-bold px-1.5 py-0.5 rounded border border-emerald-200">
                          ResNet18 v2.0
                        </span>
                      ) : isBanana ? (
                        <span className="text-[9px] bg-emerald-50 text-emerald-700 font-bold px-1.5 py-0.5 rounded border border-emerald-200">
                          ResNet18 v1.0
                        </span>
                      ) : isApple ? (
                        <span className="text-[9px] bg-amber-50 text-amber-700 font-bold px-1.5 py-0.5 rounded border border-amber-200">
                          YOLOv8n (Detect)
                        </span>
                      ) : (
                        <span className="text-[9px] bg-slate-100 text-slate-600 font-medium px-1.5 py-0.5 rounded border border-slate-200">
                          Market Trading
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-slate-800">
                      {item.crate_quantity} crates
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-slate-700">
                      ₹{item.price_per_crate}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-extrabold text-emerald-900">
                      ₹{Number(item.total_stock_value || 0).toLocaleString("en-IN")}
                    </td>
                    <td className="py-3 px-3">
                      <div className="truncate max-w-[160px] text-slate-700" title={item.location}>
                        📍 {item.location || "Farm Gate"}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {item.harvest_date || item.created_at?.split("T")[0] || "N/A"}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border capitalize ${statusStyles[item.status] || statusStyles.available}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => openEditModal(item)}
                          title="Edit Stock Details"
                          className="p-1 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded transition-colors"
                        >
                          <span className="material-symbols-outlined text-base">edit</span>
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          disabled={deletingId === item.id}
                          title="Delete Stock Record"
                          className="p-1 text-slate-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                        >
                          <span className="material-symbols-outlined text-base">delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Edit Modal */}
      {editingItem && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-outline-variant flex flex-col gap-4 animate-scale-up">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <span className="material-symbols-outlined text-digital-mint text-base">edit_note</span>
                Edit Stock Record ({editingItem.id})
              </h4>
              <button onClick={() => setEditingItem(null)} className="text-slate-400 hover:text-slate-600">
                <span className="material-symbols-outlined text-base">close</span>
              </button>
            </div>

            <div className="flex flex-col gap-3">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Crop</label>
                <input
                  type="text"
                  value={editingItem.crop_type.toUpperCase()}
                  disabled
                  className="w-full text-xs font-mono bg-slate-100 p-2.5 rounded-xl border border-slate-200 text-slate-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Quantity (Crates)</label>
                  <input
                    type="number"
                    min="1"
                    value={editQuantity}
                    onChange={(e) => setEditQuantity(e.target.value)}
                    className="w-full text-xs font-semibold p-2 bg-white border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-digital-mint"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Price / Crate (₹)</label>
                  <input
                    type="number"
                    min="1"
                    value={editPrice}
                    onChange={(e) => setEditPrice(e.target.value)}
                    className="w-full text-xs font-semibold p-2 bg-white border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-digital-mint"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Availability Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full text-xs font-semibold p-2 bg-white border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-digital-mint"
                >
                  <option value="available">Available</option>
                  <option value="reserved">Reserved</option>
                  <option value="sold">Sold</option>
                  <option value="unavailable">Unavailable</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Location</label>
                <input
                  type="text"
                  value={editLocation}
                  onChange={(e) => setEditLocation(e.target.value)}
                  className="w-full text-xs p-2 bg-white border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-digital-mint"
                />
              </div>

              <div className="bg-emerald-50 p-2.5 rounded-xl border border-emerald-200 text-[11px] text-emerald-800 flex justify-between items-center">
                <span>Recalculated Value:</span>
                <strong className="font-mono text-sm">
                  ₹{((parseInt(editQuantity, 10) || 0) * (parseFloat(editPrice) || 0)).toLocaleString("en-IN")}
                </strong>
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-200 pt-3">
              <button
                type="button"
                onClick={() => setEditingItem(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleUpdate}
                disabled={updating}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-digital-mint text-white hover:bg-emerald-600 transition-all flex items-center gap-1"
              >
                {updating ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
