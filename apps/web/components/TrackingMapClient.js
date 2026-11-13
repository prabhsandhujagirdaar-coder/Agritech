"use client";
import dynamic from "next/dynamic";
import React from "react";

// Dynamically import TrackingMap with SSR disabled to prevent Leaflet window errors
const TrackingMapNoSSR = dynamic(() => import("./TrackingMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[500px] rounded-2xl bg-surface-container-low flex flex-col items-center justify-center gap-3 border border-outline-variant/60" style={{ width: "100%", height: "100%" }}>
      <div className="w-8 h-8 rounded-full border-2 border-digital-mint border-t-transparent animate-spin" />
      <span className="text-xs text-on-surface-variant font-medium">
        Loading PostGIS Geospatial Layer...
      </span>
    </div>
  ),
});

export default function TrackingMapClient({ className = "w-full h-full", ...props }) {
  return <TrackingMapNoSSR className={className} {...props} />;
}
