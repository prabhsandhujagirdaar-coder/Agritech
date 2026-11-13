#!/usr/bin/env python3
"""
AgriChain AI - Lightweight Citrus Image Annotation Tool
=======================================================
Phase 3B: Interactive web-based and CLI annotation application for
evaluating candidate citrus imagery across three maturity stages:
  1. underripe
  2. partially_ripe
  3. fully_ripe
  4. uncertain (quarantine)

Key Principles:
- Preserves candidate manifest completely unchanged (read-only).
- Saves annotations safely to ml/data/processed/citrus_annotations.csv.
- Displays prominent scientific caveat banner (proxy cohort, not certified Kinnow).
- Zero automated label assignment.
- Supports resuming, skipping, revisiting, and group-aware metadata tracking.
"""

import os
import sys
import csv
import json
import time
import argparse
import urllib.parse
from pathlib import Path
from collections import Counter
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Tuple, Set

WORKSPACE = Path(r"C:\Users\PrabSandhu\Documents\codes\Agritech_")
RAW_DIR = WORKSPACE / "ml" / "data" / "raw"
PROCESSED_DIR = WORKSPACE / "ml" / "data" / "processed"
REVIEW_MANIFEST = PROCESSED_DIR / "citrus_candidate_review.csv"
ANNOTATIONS_CSV = PROCESSED_DIR / "citrus_annotations.csv"
HISTORY_CSV = PROCESSED_DIR / "citrus_annotation_history.csv"

ALLOWED_LABELS = {"underripe", "partially_ripe", "fully_ripe", "uncertain"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_EVENT_TYPES = {
    "initial_annotation",
    "revision",
    "reassessment",
    "reassessment_quarantine",
    "quarantine",
    "historical_pilot"
}

ANNOTATION_FIELDS = [
    "candidate_id", "rel_path", "dataset_source", "original_quality_label",
    "quality_category", "width", "height", "format", "size_bytes",
    "sha256", "dhash", "group_id", "candidate_suitability_flag",
    "reviewer_maturity_label", "reviewer_id", "review_confidence",
    "review_notes", "cultivar_verified", "ground_truth_method", "annotated_at"
]

HISTORY_FIELDS = [
    "event_id", "candidate_id", "rel_path", "dataset_source", "original_quality_label",
    "quality_category", "width", "height", "format", "size_bytes",
    "sha256", "dhash", "group_id", "candidate_suitability_flag",
    "reviewer_maturity_label", "reviewer_id", "review_confidence",
    "review_notes", "cultivar_verified", "ground_truth_method",
    "event_type", "previous_event_id", "protocol_version", "event_at"
]

class AnnotationManager:
    """Manages reading candidate manifest, persisting append-only event history,
    and maintaining an up-to-date current view safely."""

    def __init__(
        self,
        manifest_path: Path = REVIEW_MANIFEST,
        annotations_path: Path = ANNOTATIONS_CSV,
        history_path: Optional[Path] = None
    ):
        self.manifest_path = manifest_path
        self.annotations_path = annotations_path
        if history_path is None:
            if annotations_path == ANNOTATIONS_CSV:
                self.history_path = HISTORY_CSV
            else:
                self.history_path = annotations_path.parent / f"{annotations_path.stem}_history{annotations_path.suffix}"
        else:
            self.history_path = history_path

        self.candidates: List[Dict[str, str]] = []
        self.candidate_map: Dict[str, Dict[str, str]] = {}
        self.annotations: Dict[str, Dict[str, str]] = {}
        self.history_events: List[Dict[str, str]] = []
        self.event_ids: Set[str] = set()
        self.latest_event_by_candidate: Dict[str, str] = {}
        self._load_candidates()
        self._load_history()
        self._load_existing_annotations()
        self._reconcile_state()

    def _load_candidates(self):
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Candidate manifest not found at: {self.manifest_path}")

        self.candidates = []
        self.candidate_map = {}
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.candidates.append(row)
                self.candidate_map[row["candidate_id"]] = row

    def _load_history(self):
        """Load append-only event history or seed from existing annotations."""
        self.history_events = []
        self.event_ids = set()
        self.latest_event_by_candidate = {}

        if self.history_path.exists():
            with open(self.history_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    return  # Empty file
                required = {"event_id", "candidate_id", "event_type"}
                if not required.issubset(set(reader.fieldnames)):
                    raise ValueError(
                        f"Malformed history file {self.history_path}: missing required fields {required - set(reader.fieldnames)}"
                    )
                for row in reader:
                    eid = row.get("event_id", "").strip()
                    if not eid:
                        continue
                    self.history_events.append(row)
                    self.event_ids.add(eid)
                    cid = row.get("candidate_id", "").strip()
                    if cid:
                        self.latest_event_by_candidate[cid] = eid
        else:
            # If history does not exist yet, seed it from existing annotations if present
            if self.annotations_path.exists():
                self._seed_history_from_annotations()

    def _seed_history_from_annotations(self):
        """Bootstrap history ledger from existing current annotations without inventing unverified facts."""
        with open(self.annotations_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("candidate_id", "").strip()
                if not cid:
                    continue
                eid = f"EVT-HIST-{cid}"
                event_record = {
                    "event_id": eid,
                    "candidate_id": cid,
                    "rel_path": row.get("rel_path", ""),
                    "dataset_source": row.get("dataset_source", "fruitnet"),
                    "original_quality_label": row.get("original_quality_label", ""),
                    "quality_category": row.get("quality_category", ""),
                    "width": row.get("width", ""),
                    "height": row.get("height", ""),
                    "format": row.get("format", ""),
                    "size_bytes": row.get("size_bytes", ""),
                    "sha256": row.get("sha256", ""),
                    "dhash": row.get("dhash", ""),
                    "group_id": row.get("group_id", ""),
                    "candidate_suitability_flag": row.get("candidate_suitability_flag", ""),
                    "reviewer_maturity_label": row.get("reviewer_maturity_label", "uncertain"),
                    "reviewer_id": row.get("reviewer_id", "historical"),
                    "review_confidence": row.get("review_confidence", "low"),
                    "review_notes": row.get("review_notes", ""),
                    "cultivar_verified": row.get("cultivar_verified", "false"),
                    "ground_truth_method": row.get("ground_truth_method", "human_visual_review"),
                    "event_type": "historical_pilot",
                    "previous_event_id": "none",
                    "protocol_version": "legacy_pilot_v0",
                    "event_at": row.get("annotated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
                }
                self.history_events.append(event_record)
                self.event_ids.add(eid)
                self.latest_event_by_candidate[cid] = eid

        if self.history_events:
            self._flush_history()

    def _append_history_event(self, event_record: Dict[str, str]):
        """Append a single event to the history file with fsync write safety."""
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not self.history_path.exists() or self.history_path.stat().st_size == 0
        with open(self.history_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(event_record)
            f.flush()
            os.fsync(f.fileno())

        self.history_events.append(event_record)
        self.event_ids.add(event_record["event_id"])
        self.latest_event_by_candidate[event_record["candidate_id"]] = event_record["event_id"]

    def _flush_history(self):
        """Atomically write entire history events list to disk."""
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.history_path.with_suffix(".tmp")
        with open(temp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
            writer.writeheader()
            writer.writerows(self.history_events)
            f.flush()
            os.fsync(f.fileno())

        if temp_path.exists():
            os.replace(temp_path, self.history_path)

    def _load_existing_annotations(self):
        self.annotations = {}
        if self.annotations_path.exists():
            with open(self.annotations_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.annotations[row["candidate_id"]] = row

    def _reconcile_state(self):
        """Reconciles current annotations view with the history ledger.
        If history contains events for candidates missing from annotations or
        with newer timestamps (e.g. after a crash before Phase 2 write),
        materialize the latest history event into self.annotations and persist.
        """
        latest_history_map: Dict[str, Dict[str, str]] = {}
        for ev in self.history_events:
            cid = ev.get("candidate_id")
            if cid:
                latest_history_map[cid] = ev

        dirty = False
        for cid, ev in latest_history_map.items():
            curr = self.annotations.get(cid)
            if (curr is None
                or curr.get("reviewer_maturity_label") != ev.get("reviewer_maturity_label")
                or curr.get("annotated_at") != ev.get("event_at")):
                # Materialize current view record from latest history event
                cand = self.candidate_map.get(cid, {})
                record = {
                    "candidate_id": cid,
                    "rel_path": ev.get("rel_path") or cand.get("rel_path", ""),
                    "dataset_source": ev.get("dataset_source") or cand.get("dataset_source", "fruitnet"),
                    "original_quality_label": ev.get("original_quality_label") or cand.get("original_quality_label", ""),
                    "quality_category": ev.get("quality_category") or cand.get("quality_category", ""),
                    "width": ev.get("width") or cand.get("width", ""),
                    "height": ev.get("height") or cand.get("height", ""),
                    "format": ev.get("format") or cand.get("format", ""),
                    "size_bytes": ev.get("size_bytes") or cand.get("size_bytes", ""),
                    "sha256": ev.get("sha256") or cand.get("sha256", ""),
                    "dhash": ev.get("dhash") or cand.get("dhash", ""),
                    "group_id": ev.get("group_id") or cand.get("group_id", ""),
                    "candidate_suitability_flag": ev.get("candidate_suitability_flag") or cand.get("candidate_suitability_flag", ""),
                    "reviewer_maturity_label": ev.get("reviewer_maturity_label", "uncertain"),
                    "reviewer_id": ev.get("reviewer_id", "unknown"),
                    "review_confidence": ev.get("review_confidence", "medium"),
                    "review_notes": ev.get("review_notes", ""),
                    "cultivar_verified": ev.get("cultivar_verified", "false"),
                    "ground_truth_method": ev.get("ground_truth_method", "human_visual_review"),
                    "annotated_at": ev.get("event_at", "")
                }
                self.annotations[cid] = record
                dirty = True

        if dirty:
            self._flush_annotations()

    def get_candidate_history(self, candidate_id: str) -> List[Dict[str, str]]:
        """Return all historical events recorded for this candidate in chronological order."""
        return [ev for ev in self.history_events if ev.get("candidate_id") == candidate_id]

    def save_annotation(
        self,
        candidate_id: str,
        label: str,
        confidence: str = "medium",
        notes: str = "",
        reviewer_id: str = "reviewer_01",
        cultivar_verified: str = "false",
        ground_truth_method: str = "human_visual_review",
        event_type: Optional[str] = None,
        protocol_version: str = "fruitnet_pilot_v1",
        event_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Validate, append to history ledger first (Write-Ahead Log),
        and atomically update current annotations view."""
        if candidate_id not in self.candidate_map:
            raise KeyError(f"Candidate ID {candidate_id} not found in manifest")

        label = label.strip().lower()
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Invalid label '{label}'. Allowed: {sorted(list(ALLOWED_LABELS))}")

        confidence = confidence.strip().lower()
        if confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(f"Invalid confidence '{confidence}'. Allowed: {sorted(list(ALLOWED_CONFIDENCE))}")

        cand = self.candidate_map[candidate_id]
        existing_curr = self.annotations.get(candidate_id)
        prev_event_id = self.latest_event_by_candidate.get(candidate_id, "none")

        # Determine event_type if not explicitly passed
        if event_type is None:
            if existing_curr is None:
                event_type = "initial_annotation"
            elif existing_curr.get("reviewer_maturity_label") == "uncertain":
                event_type = "reassessment" if label != "uncertain" else "reassessment_quarantine"
            else:
                event_type = "revision"
        elif event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{event_type}'. Allowed: {sorted(list(ALLOWED_EVENT_TYPES))}")

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Generate deterministic event_id if not supplied
        if not event_id:
            seq = len(self.history_events) + 1
            event_id = f"EVT-{time.strftime('%Y%m%d%H%M%S', time.gmtime())}-{candidate_id}-{seq:04d}"

        # Deduplication / Idempotency check:
        if event_id in self.event_ids:
            # Retried write or duplicate event ID; return existing record without appending duplicate
            for ev in reversed(self.history_events):
                if ev.get("event_id") == event_id:
                    return ev
            return existing_curr or {}

        history_record = {
            "event_id": event_id,
            "candidate_id": cand["candidate_id"],
            "rel_path": cand["rel_path"],
            "dataset_source": cand.get("dataset_source", "fruitnet"),
            "original_quality_label": cand.get("original_quality_label", ""),
            "quality_category": cand.get("quality_category", ""),
            "width": cand.get("width", ""),
            "height": cand.get("height", ""),
            "format": cand.get("format", ""),
            "size_bytes": cand.get("size_bytes", ""),
            "sha256": cand.get("sha256", ""),
            "dhash": cand.get("dhash", ""),
            "group_id": cand.get("group_id", ""),
            "candidate_suitability_flag": cand.get("candidate_suitability_flag", ""),
            "reviewer_maturity_label": label,
            "reviewer_id": reviewer_id.strip() or "anonymous_reviewer",
            "review_confidence": confidence,
            "review_notes": notes.strip(),
            "cultivar_verified": str(cultivar_verified).lower(),
            "ground_truth_method": ground_truth_method.strip(),
            "event_type": event_type,
            "previous_event_id": prev_event_id,
            "protocol_version": protocol_version,
            "event_at": now_iso
        }

        current_view_record = {
            "candidate_id": cand["candidate_id"],
            "rel_path": cand["rel_path"],
            "dataset_source": cand.get("dataset_source", "fruitnet"),
            "original_quality_label": cand.get("original_quality_label", ""),
            "quality_category": cand.get("quality_category", ""),
            "width": cand.get("width", ""),
            "height": cand.get("height", ""),
            "format": cand.get("format", ""),
            "size_bytes": cand.get("size_bytes", ""),
            "sha256": cand.get("sha256", ""),
            "dhash": cand.get("dhash", ""),
            "group_id": cand.get("group_id", ""),
            "candidate_suitability_flag": cand.get("candidate_suitability_flag", ""),
            "reviewer_maturity_label": label,
            "reviewer_id": reviewer_id.strip() or "anonymous_reviewer",
            "review_confidence": confidence,
            "review_notes": notes.strip(),
            "cultivar_verified": str(cultivar_verified).lower(),
            "ground_truth_method": ground_truth_method.strip(),
            "annotated_at": now_iso
        }

        # TWO-PHASE WRITE:
        # Phase 1: Append to history file (WAL with fsync)
        self._append_history_event(history_record)

        # Phase 2: Update in-memory current view & atomically flush to annotations_path
        self.annotations[candidate_id] = current_view_record
        self._flush_annotations()

        return current_view_record

    def _flush_annotations(self):
        """Atomically write all current annotations to disk."""
        self.annotations_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.annotations_path.with_suffix(".tmp")

        with open(temp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=ANNOTATION_FIELDS)
            writer.writeheader()
            for cand in self.candidates:
                cid = cand["candidate_id"]
                if cid in self.annotations:
                    writer.writerow(self.annotations[cid])
            f.flush()
            os.fsync(f.fileno())

        # Replace destination atomically
        if temp_path.exists():
            os.replace(temp_path, self.annotations_path)

    def get_candidate(self, index: int) -> Tuple[Dict[str, str], Optional[Dict[str, str]]]:
        if index < 0 or index >= len(self.candidates):
            raise IndexError("Candidate index out of range")
        cand = self.candidates[index]
        existing = self.annotations.get(cand["candidate_id"])
        return cand, existing

    def get_first_unannotated_index(self, primary_only: bool = True) -> int:
        for i, cand in enumerate(self.candidates):
            if primary_only and cand.get("candidate_suitability_flag") != "primary_candidate":
                continue
            if cand["candidate_id"] not in self.annotations:
                return i
        return 0

    def get_stage2_training_annotations(self) -> List[Dict[str, str]]:
        """Return only valid, non-quarantined maturity annotations on primary candidates."""
        stage2 = []
        for cand in self.candidates:
            cid = cand["candidate_id"]
            if cid in self.annotations:
                ann = self.annotations[cid]
                # Condition a: candidate_suitability_flag == "primary_candidate"
                if ann.get("candidate_suitability_flag") != "primary_candidate":
                    continue
                # Condition b: reviewer_maturity_label in {"underripe", "partially_ripe", "fully_ripe"}
                if ann.get("reviewer_maturity_label") not in {"underripe", "partially_ripe", "fully_ripe"}:
                    continue
                # Condition c: "[PILOT_QUARANTINE" not in review_notes
                if "[PILOT_QUARANTINE" in ann.get("review_notes", ""):
                    continue
                stage2.append(ann)
        return stage2

    def get_stats(self) -> Dict[str, any]:
        total = len(self.candidates)
        annotated = len(self.annotations)
        history_total = len(self.history_events)
        counts = Counter(a["reviewer_maturity_label"] for a in self.annotations.values())
        primary_candidates_total = sum(1 for c in self.candidates if c.get("candidate_suitability_flag") == "primary_candidate")
        stage2_records = self.get_stage2_training_annotations()
        stage2_valid_annotated = len(stage2_records)
        quarantined_or_defective = sum(
            1 for a in self.annotations.values()
            if a.get("candidate_suitability_flag") != "primary_candidate" or "[PILOT_QUARANTINE" in a.get("review_notes", "")
        )
        return {
            "total_candidates": total,
            "total_annotated": annotated,
            "total_history_events": history_total,
            "remaining": total - annotated,
            "completion_pct": round((annotated / total) * 100, 2) if total else 0.0,
            "label_distribution": dict(counts),
            "primary_candidates_total": primary_candidates_total,
            "stage2_valid_annotated": stage2_valid_annotated,
            "quarantined_or_defective_annotated": quarantined_or_defective
        }

# ==============================================================================
# Lightweight Local Web Server
# ==============================================================================

class AnnotationServerHandler(BaseHTTPRequestHandler):
    manager: AnnotationManager = None

    def log_message(self, format, *args):
        # Silence default request spam in console, only log errors
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._serve_html()
        elif path == "/api/stats":
            self._send_json(self.manager.get_stats())
        elif path == "/api/candidate":
            idx = int(query.get("index", [0])[0])
            total = len(self.manager.candidates)
            primary_only = query.get("primary_only", ["false"])[0].lower() == "true"
            direction = query.get("direction", [""])[0].lower()
            
            if primary_only and total > 0:
                step = -1 if direction == "prev" else 1
                curr = max(0, min(idx, total - 1))
                while 0 <= curr < total and self.manager.candidates[curr].get("candidate_suitability_flag") != "primary_candidate":
                    curr += step
                if 0 <= curr < total:
                    idx = curr
                else:
                    curr = max(0, min(idx, total - 1))
                    while 0 <= curr < total and self.manager.candidates[curr].get("candidate_suitability_flag") != "primary_candidate":
                        curr -= step
                    if 0 <= curr < total:
                        idx = curr
            else:
                idx = max(0, min(idx, total - 1))

            cand, ann = self.manager.get_candidate(idx)
            history = self.manager.get_candidate_history(cand["candidate_id"])
            self._send_json({
                "index": idx,
                "total": total,
                "candidate": cand,
                "annotation": ann,
                "history": history
            })
        elif path == "/api/first_unannotated":
            primary_only = query.get("primary_only", ["true"])[0].lower() == "true"
            idx = self.manager.get_first_unannotated_index(primary_only)
            self._send_json({"index": idx})
        elif path == "/api/image":
            rel_path = query.get("path", [""])[0]
            full_path = RAW_DIR / rel_path
            if full_path.exists() and full_path.is_file():
                ext = full_path.suffix.lower()
                mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
                with open(full_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "Image not found")
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/annotate":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                record = self.manager.save_annotation(
                    candidate_id=data["candidate_id"],
                    label=data["reviewer_maturity_label"],
                    confidence=data.get("review_confidence", "medium"),
                    notes=data.get("review_notes", ""),
                    reviewer_id=data.get("reviewer_id", "reviewer_01"),
                    cultivar_verified=data.get("cultivar_verified", "false"),
                    ground_truth_method=data.get("ground_truth_method", "human_visual_review"),
                    event_type=data.get("event_type"),
                    protocol_version=data.get("protocol_version", "fruitnet_pilot_v1"),
                    event_id=data.get("event_id")
                )
                self._send_json({"status": "ok", "record": record, "stats": self.manager.get_stats()})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, status=400)
        else:
            self.send_error(404, "Not found")

    def _send_json(self, data: dict, status: int = 200):
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_html(self):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgriChain AI — Citrus Maturity Annotation Tool</title>
<style>
  :root {
    --bg-primary: #0f172a;
    --bg-card: #1e293b;
    --border: #334155;
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
    --accent: #10b981;
    --warning-bg: #451a03;
    --warning-border: #b45309;
    --warning-text: #fde68a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: var(--bg-primary); color: var(--text-primary); padding: 1.5rem; }
  .container { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.25rem; }
  
  /* Header & Caveat Banner */
  .caveat-banner {
    background: var(--warning-bg); border: 1px solid var(--warning-border); color: var(--warning-text);
    padding: 0.9rem 1.2rem; border-radius: 8px; font-size: 0.88rem; line-height: 1.4;
  }
  .caveat-banner strong { color: #fff; }

  /* Workspace Layout */
  .workspace { display: grid; grid-template-columns: 500px 1fr; gap: 1.5rem; }
  
  /* Image Card */
  .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; }
  .image-viewport {
    width: 100%; height: 420px; background: #000; border-radius: 8px;
    display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative;
  }
  .image-viewport img { max-width: 100%; max-height: 100%; object-fit: contain; }
  .metadata-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-top: 1rem; font-size: 0.85rem; }
  .meta-item { background: #0f172a; padding: 0.5rem 0.75rem; border-radius: 6px; border: 1px solid #1e293b; }
  .meta-label { color: var(--text-muted); font-size: 0.75rem; display: block; margin-bottom: 2px; }
  .meta-val { font-weight: 600; color: #e2e8f0; }

  /* Annotation Controls */
  .control-group { margin-bottom: 1.25rem; }
  .control-title { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem; }
  .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  
  .label-btn {
    padding: 0.85rem 1rem; border-radius: 8px; border: 2px solid var(--border);
    background: #0f172a; color: #fff; font-weight: 600; cursor: pointer;
    text-align: left; display: flex; flex-direction: column; gap: 4px; transition: all 0.15s;
  }
  .label-btn small { font-size: 0.75rem; font-weight: normal; color: var(--text-muted); }
  .label-btn:hover { border-color: #64748b; }
  .label-btn.selected { border-color: var(--accent); background: rgba(16, 185, 129, 0.15); }
  .label-btn[data-val="underripe"].selected { border-color: #10b981; }
  .label-btn[data-val="partially_ripe"].selected { border-color: #f59e0b; }
  .label-btn[data-val="fully_ripe"].selected { border-color: #ea580c; }
  .label-btn[data-val="uncertain"].selected { border-color: #ef4444; }

  .confidence-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem; }
  .conf-btn {
    padding: 0.5rem; border-radius: 6px; border: 1px solid var(--border);
    background: #0f172a; color: #fff; font-size: 0.85rem; cursor: pointer; text-align: center;
  }
  .conf-btn.selected { border-color: #38bdf8; background: rgba(56, 189, 248, 0.15); font-weight: 600; }

  input[type="text"], textarea {
    width: 100%; background: #0f172a; border: 1px solid var(--border); border-radius: 6px;
    padding: 0.6rem; color: #fff; font-size: 0.85rem;
  }
  textarea { resize: vertical; height: 60px; }

  /* Navigation Bar */
  .nav-bar { display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
  .nav-btn {
    padding: 0.65rem 1.25rem; border-radius: 6px; border: 1px solid var(--border);
    background: #0f172a; color: #fff; font-weight: 600; cursor: pointer;
  }
  .nav-btn:hover { background: #1e293b; }
  .btn-save { background: #059669; border-color: #059669; }
  .btn-save:hover { background: #10b981; }

  /* Stats & Progress */
  .progress-wrap { background: #0f172a; border-radius: 999px; height: 8px; width: 100%; overflow: hidden; margin-top: 6px; }
  .progress-bar { background: var(--accent); height: 100%; width: 0%; transition: width 0.3s; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
  .badge-primary { background: #065f46; color: #6ee7b7; }
  .badge-defective { background: #7f1d1d; color: #fca5a5; }
</style>
</head>
<body>
<div class="container">
  <div class="caveat-banner">
    <strong>⚠️ SCIENTIFIC CAVEAT & RESEARCH RESTRAINT:</strong> These candidate images belong to an unverified Indian citrus cohort (FruitNet) and are <strong>NOT confirmed Kinnow Mandarin</strong>. Visual inspection alone cannot establish certified biological maturity or Brix/acid ground truth. Mark ambiguous or rotted fruit as <code>uncertain</code>; never force a maturity stage.
  </div>

  <div style="display: flex; justify-content: space-between; align-items: center;">
    <div>
      <h2 style="font-size: 1.25rem;">AgriChain AI — Citrus Maturity Review Tool</h2>
      <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;" id="status-text">Loading candidate...</div>
      <div style="margin-top: 6px;">
        <label style="font-size: 0.82rem; color: #38bdf8; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; user-select: none;">
          <input type="checkbox" id="primary-filter-chk" checked onchange="onTogglePrimaryFilter()">
          <strong>Primary Candidates Only (Skip Orange_Bad)</strong>
        </label>
      </div>
    </div>
    <div style="width: 360px; text-align: right;">
      <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;" id="stats-counter">0 / 2500 (0.00%)</div>
      <div style="font-size: 0.75rem; color: #38bdf8; font-weight: 600; margin-top: 2px;" id="stage2-counter">Stage-2 Valid Annotations: 0 / 1,341</div>
      <div class="progress-wrap"><div class="progress-bar" id="progress-bar"></div></div>
    </div>
  </div>

  <div class="workspace">
    <!-- Left: Image Viewport & Metadata -->
    <div class="card">
      <div class="image-viewport">
        <img id="img-display" src="" alt="Citrus Candidate">
      </div>
      <div class="metadata-grid">
        <div class="meta-item"><span class="meta-label">Candidate ID</span><span class="meta-val" id="cand-id">—</span></div>
        <div class="meta-item"><span class="meta-label">Suitability Flag</span><span id="cand-flag">—</span></div>
        <div class="meta-item"><span class="meta-label">Burst Group ID</span><span class="meta-val" id="cand-group">—</span></div>
        <div class="meta-item"><span class="meta-label">Original Category</span><span class="meta-val" id="cand-orig" style="font-size: 0.78rem;">—</span></div>
        <div class="meta-item"><span class="meta-label">Resolution</span><span class="meta-val" id="cand-res">—</span></div>
        <div class="meta-item"><span class="meta-label">History Ledger</span><span class="meta-val" id="cand-history" style="color: #38bdf8;">—</span></div>
      </div>
    </div>

    <!-- Right: Annotation Controls -->
    <div class="card">
      <div class="control-group">
        <div class="control-title">1. Target Maturity Stage (Keys: 1, 2, 3, 4)</div>
        <div class="btn-grid">
          <button class="label-btn" data-val="underripe" onclick="selectLabel('underripe')">
            <span>[1] Underripe</span>
            <small>>60% deep green rind, tight glands</small>
          </button>
          <button class="label-btn" data-val="partially_ripe" onclick="selectLabel('partially_ripe')">
            <span>[2] Partially Ripe</span>
            <small>25%-60% breaker yellow/orange</small>
          </button>
          <button class="label-btn" data-val="fully_ripe" onclick="selectLabel('fully_ripe')">
            <span>[3] Fully Ripe</span>
            <small>>80% golden-orange, pliant rind</small>
          </button>
          <button class="label-btn" data-val="uncertain" onclick="selectLabel('uncertain')">
            <span>[4] Uncertain / Quarantine</span>
            <small>Heavy glare, rot, ambiguous hue</small>
          </button>
        </div>
      </div>

      <div class="control-group">
        <div class="control-title">2. Review Confidence (Keys: Q, W, E)</div>
        <div class="confidence-grid">
          <button class="conf-btn selected" data-val="high" onclick="selectConf('high')">[Q] High</button>
          <button class="conf-btn" data-val="medium" onclick="selectConf('medium')">[W] Medium</button>
          <button class="conf-btn" data-val="low" onclick="selectConf('low')">[E] Low</button>
        </div>
      </div>

      <div class="control-group" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
        <div>
          <div class="control-title">Reviewer ID</div>
          <input type="text" id="reviewer-id" value="reviewer_01">
        </div>
        <div>
          <div class="control-title">Cultivar Status</div>
          <div style="font-size: 0.8rem; color: var(--text-muted); padding: 0.6rem; background: #0f172a; border-radius: 6px; border: 1px solid var(--border);">
            Unverified Indian Citrus
          </div>
        </div>
      </div>

      <div class="control-group">
        <div class="control-title">Review Notes (Optional)</div>
        <textarea id="review-notes" placeholder="e.g. Flavedo is 40% orange breaker, green button intact."></textarea>
      </div>

      <div class="nav-bar">
        <div>
          <button class="nav-btn" onclick="prevImage()">← Previous</button>
          <button class="nav-btn" onclick="nextImage()">Skip →</button>
        </div>
        <button class="nav-btn btn-save" onclick="saveAndNext()">Save & Next (Enter) →</button>
      </div>
    </div>
  </div>
</div>

<script>
let currentIndex = 0;
let currentCandidate = null;
let selectedLabel = null;
let selectedConfidence = "high";

function isPrimaryOnly() {
  const el = document.getElementById("primary-filter-chk");
  return el ? el.checked : true;
}

async function loadCandidate(idx, direction = "") {
  try {
    const primaryOnly = isPrimaryOnly();
    const res = await fetch(`/api/candidate?index=${idx}&direction=${direction}&primary_only=${primaryOnly}`);
    const data = await res.json();
    currentIndex = data.index;
    currentCandidate = data.candidate;
    
    // Update image & metadata
    document.getElementById("img-display").src = `/api/image?path=${encodeURIComponent(currentCandidate.rel_path)}`;
    document.getElementById("cand-id").innerText = currentCandidate.candidate_id;
    document.getElementById("cand-group").innerText = currentCandidate.group_id;
    document.getElementById("cand-orig").innerText = currentCandidate.original_quality_label;
    document.getElementById("cand-res").innerText = `${currentCandidate.width} × ${currentCandidate.height}`;
    document.getElementById("cand-size").innerText = `${(currentCandidate.size_bytes / 1024).toFixed(1)} KB`;
    
    const flagEl = document.getElementById("cand-flag");
    if (currentCandidate.candidate_suitability_flag === "primary_candidate") {
      flagEl.innerHTML = `<span class="badge badge-primary">Primary Candidate</span>`;
    } else {
      flagEl.innerHTML = `<span class="badge badge-defective">Defective Rot</span>`;
    }

    document.getElementById("status-text").innerText = `Candidate ${currentIndex + 1} of ${data.total} | Path: ${currentCandidate.rel_path}`;

    const histLen = data.history ? data.history.length : 0;
    const histEl = document.getElementById("cand-history");
    if (histEl) {
      if (histLen > 0) {
        const lastEv = data.history[data.history.length - 1];
        histEl.innerText = `${histLen} event(s) (${lastEv.event_type})`;
      } else {
        histEl.innerText = "None (New)";
      }
    }

    // Reset controls or load existing annotation
    if (data.annotation) {
      selectLabel(data.annotation.reviewer_maturity_label);
      selectConf(data.annotation.review_confidence || "high");
      document.getElementById("review-notes").value = data.annotation.review_notes || "";
      if (data.annotation.reviewer_id) document.getElementById("reviewer-id").value = data.annotation.reviewer_id;
    } else {
      clearSelection();
      document.getElementById("review-notes").value = "";
    }

    updateStats();
  } catch (err) {
    console.error("Failed to load candidate:", err);
  }
}

async function updateStats() {
  const res = await fetch('/api/stats');
  const stats = await res.json();
  const histStr = stats.total_history_events ? ` | Events: ${stats.total_history_events}` : "";
  document.getElementById("stats-counter").innerText = `Total: ${stats.total_annotated} / ${stats.total_candidates} (${stats.completion_pct}%)${histStr}`;
  document.getElementById("stage2-counter").innerText = `Stage-2 Valid Annotations: ${stats.stage2_valid_annotated} / ${stats.primary_candidates_total || 1341}`;
  document.getElementById("progress-bar").style.width = `${stats.completion_pct}%`;
}

function selectLabel(val) {
  selectedLabel = val;
  document.querySelectorAll(".label-btn").forEach(b => {
    b.classList.toggle("selected", b.getAttribute("data-val") === val);
  });
}

function clearSelection() {
  selectedLabel = null;
  document.querySelectorAll(".label-btn").forEach(b => b.classList.remove("selected"));
}

function selectConf(val) {
  selectedConfidence = val;
  document.querySelectorAll(".conf-btn").forEach(b => {
    b.classList.toggle("selected", b.getAttribute("data-val") === val);
  });
}

async function saveAndNext() {
  if (!selectedLabel) {
    alert("Please select a maturity label (1, 2, 3, or 4 for Uncertain) before saving.");
    return;
  }
  const payload = {
    candidate_id: currentCandidate.candidate_id,
    reviewer_maturity_label: selectedLabel,
    review_confidence: selectedConfidence,
    reviewer_id: document.getElementById("reviewer-id").value.trim() || "reviewer_01",
    review_notes: document.getElementById("review-notes").value.trim(),
    cultivar_verified: "false",
    ground_truth_method: "human_visual_review"
  };
  await fetch("/api/annotate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  nextImage();
}

function nextImage() {
  loadCandidate(currentIndex + 1, "next");
}

function prevImage() {
  if (currentIndex > 0) {
    loadCandidate(currentIndex - 1, "prev");
  }
}

function onTogglePrimaryFilter() {
  const primaryOnly = isPrimaryOnly();
  if (primaryOnly && currentCandidate && currentCandidate.candidate_suitability_flag !== "primary_candidate") {
    loadCandidate(currentIndex, "next");
  }
}

// Keyboard shortcuts
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  if (e.key === "1") selectLabel("underripe");
  else if (e.key === "2") selectLabel("partially_ripe");
  else if (e.key === "3") selectLabel("fully_ripe");
  else if (e.key === "4") selectLabel("uncertain");
  else if (e.key.toLowerCase() === "q") selectConf("high");
  else if (e.key.toLowerCase() === "w") selectConf("medium");
  else if (e.key.toLowerCase() === "e") selectConf("low");
  else if (e.key === "Enter") saveAndNext();
  else if (e.key === " " || e.key === "ArrowRight") { e.preventDefault(); nextImage(); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); prevImage(); }
});

// Initial boot: fetch first unannotated primary candidate
async function initBoot() {
  try {
    const primaryOnly = isPrimaryOnly();
    const res = await fetch(`/api/first_unannotated?primary_only=${primaryOnly}`);
    const data = await res.json();
    await loadCandidate(data.index, "next");
  } catch (err) {
    loadCandidate(0);
  }
}
initBoot();
</script>
</body>
</html>"""
        content = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

# ==============================================================================
# CLI Interactive Loop (Headless / Terminal Mode)
# ==============================================================================

def run_cli_loop(manager: AnnotationManager, primary_only: bool = True):
    print("=" * 70)
    print("AGRICHAIN AI — CITRUS MATURITY ANNOTATION CLI (STAGE 2 INTACT FRUIT)")
    print("=" * 70)
    if primary_only:
        print("Mode: Primary Candidates Only (Skipping Orange_Bad / Defective Rot).")
    else:
        print("Mode: All Candidates (Including Defective Rot).")
    print("⚠️ CAVEAT: Unverified Indian Citrus cohort (FruitNet), not confirmed Kinnow.")
    print("Commands: [1] underripe, [2] partially_ripe, [3] fully_ripe, [4] uncertain")
    print("          [s] skip, [p] previous, [q] quit\n")

    current_idx = manager.get_first_unannotated_index(primary_only=primary_only)
    reviewer_id = input("Enter Reviewer ID [reviewer_01]: ").strip() or "reviewer_01"

    while 0 <= current_idx < len(manager.candidates):
        cand, existing = manager.get_candidate(current_idx)
        if primary_only and cand.get("candidate_suitability_flag") != "primary_candidate":
            current_idx += 1
            continue

        print("-" * 70)
        status_str = f"[{existing['reviewer_maturity_label']}]" if existing else "[UNANNOTATED]"
        cand_hist = manager.get_candidate_history(cand["candidate_id"])
        hist_str = f"(History: {len(cand_hist)} event(s))" if cand_hist else "(New)"
        print(f"[{current_idx + 1}/{len(manager.candidates)}] ID: {cand['candidate_id']} {status_str} {hist_str}")
        print(f"Path        : {cand['rel_path']}")
        print(f"Category    : {cand['original_quality_label']} ({cand['candidate_suitability_flag']})")
        print(f"Burst Group : {cand['group_id']}")
        print(f"Dimensions  : {cand['width']}x{cand['height']}")

        choice = input("Select maturity (1=underripe, 2=partially_ripe, 3=fully_ripe, 4=uncertain, s=skip, p=prev, q=quit): ").strip().lower()
        if choice == "q":
            print("Exiting CLI review.")
            break
        elif choice == "p":
            while current_idx > 0:
                current_idx -= 1
                if not primary_only or manager.candidates[current_idx].get("candidate_suitability_flag") == "primary_candidate":
                    break
            continue
        elif choice == "s" or choice == "":
            while current_idx < len(manager.candidates) - 1:
                current_idx += 1
                if not primary_only or manager.candidates[current_idx].get("candidate_suitability_flag") == "primary_candidate":
                    break
            else:
                current_idx = len(manager.candidates)
            continue
        
        label_map = {"1": "underripe", "2": "partially_ripe", "3": "fully_ripe", "4": "uncertain"}
        if choice not in label_map:
            print("Invalid choice. Try again.")
            continue

        label = label_map[choice]
        conf_in = input("Confidence [1=high, 2=medium, 3=low] (default: high): ").strip()
        conf = {"1": "high", "2": "medium", "3": "low"}.get(conf_in, "high")
        notes = input("Review notes (optional): ").strip()

        manager.save_annotation(
            candidate_id=cand["candidate_id"],
            label=label,
            confidence=conf,
            notes=notes,
            reviewer_id=reviewer_id
        )
        print(f"-> Saved {cand['candidate_id']} as {label} ({conf}).")
        while current_idx < len(manager.candidates) - 1:
            current_idx += 1
            if not primary_only or manager.candidates[current_idx].get("candidate_suitability_flag") == "primary_candidate":
                break
        else:
            current_idx = len(manager.candidates)

    stats = manager.get_stats()
    print("\nSession Complete:")
    print(f"Total Annotated: {stats['total_annotated']} / {stats['total_candidates']} ({stats['completion_pct']}%)")
    print(f"Total Events   : {stats.get('total_history_events', stats['total_annotated'])}")
    print(f"Stage-2 Valid Annotated: {stats['stage2_valid_annotated']} / {stats['primary_candidates_total']}")
    print(f"Label Counts: {stats['label_distribution']}")

def run_server(port: int = 8080):
    manager = AnnotationManager()
    AnnotationServerHandler.manager = manager
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, AnnotationServerHandler)
    stats = manager.get_stats()

    print("=" * 70)
    print("AGRICHAIN AI — CITRUS MATURITY ANNOTATION SERVER")
    print("=" * 70)
    print(f"Local URL   : http://127.0.0.1:{port}")
    print(f"Source      : {REVIEW_MANIFEST}")
    print(f"Current View: {ANNOTATIONS_CSV}")
    print(f"History CSV : {manager.history_path}")
    print(f"Progress    : {stats['total_annotated']} / {stats['total_candidates']} annotated ({stats['completion_pct']}%)")
    print(f"Events      : {stats.get('total_history_events', 0)} recorded history events")
    print(f"Stage-2     : {stats['stage2_valid_annotated']} / {stats['primary_candidates_total']} primary maturity annotated")
    print("Press Ctrl+C to stop the server.")
    print("=" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping annotation server...")
        httpd.server_close()
        print("Server stopped cleanly.")

def main():
    parser = argparse.ArgumentParser(description="AgriChain AI Citrus Maturity Annotation Tool")
    parser.add_argument("--cli", action="store_true", help="Run interactive terminal CLI instead of web server")
    parser.add_argument("--include-defective", action="store_true", help="Include defective rot specimens instead of primary candidates only")
    parser.add_argument("--port", type=int, default=8080, help="Port for web interface (default: 8080)")
    args = parser.parse_args()

    if args.cli:
        manager = AnnotationManager()
        run_cli_loop(manager, primary_only=not args.include_defective)
    else:
        run_server(args.port)

if __name__ == "__main__":
    main()
