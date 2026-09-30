/**
 * Live Webcam Monitoring API Client
 *
 * Communicates with FastAPI live endpoints (/api/v1/live)
 * for session lifecycle, sampled frame uploads, and metrics.
 */

export interface LiveBBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface LiveCenter {
  x: number;
  y: number;
}

export interface LiveTrackedObject {
  track_id: number;
  class_name: string;
  confidence: number;
  bbox: LiveBBox;
  center: LiveCenter;
}

export interface LiveSafetyEvent {
  event_type: string;
  severity: "info" | "warning" | "medium" | "high" | "critical" | string;
  track_ids: number[];
  message: string;
  distance?: number | null;
  zone_id?: string | null;
  timestamp_seconds?: number;
}

export interface LiveSafetyResult {
  events: LiveSafetyEvent[];
  risk_level: "normal" | "warning" | "high" | "critical" | string;
  error?: string | null;
}

export interface LivePPEWorker {
  track_id: number;
  status: "compliant" | "non_compliant" | "unverified" | string;
  required_ppe: string[];
  detected_ppe: string[];
  missing_ppe: string[];
}

export interface LivePPEResult {
  enabled: boolean;
  available: boolean;
  workers: LivePPEWorker[];
  violations_count: number;
  error?: string | null;
}

export interface LiveInventoryResult {
  enabled: boolean;
  available: boolean;
  counts: Record<string, number>;
  unique_counts: Record<string, number>;
  error?: string | null;
}

export interface LiveFrameResponse {
  session_id: string;
  frame_number: number;
  processing_time_ms: number;
  frame_width: number;
  frame_height: number;
  objects: LiveTrackedObject[];
  safety: LiveSafetyResult;
  ppe: LivePPEResult;
  inventory: LiveInventoryResult;
}

export interface LiveSessionCreateResponse {
  session_id: string;
  status: string;
  created_at: string;
}

export interface LiveSessionSummary {
  session_id: string;
  status: string;
  duration_seconds: number;
  frames_processed: number;
  average_processing_time_ms: number;
  unique_tracks: number;
  safety_events: number;
  ppe_violations: number;
  inventory_events: number;
  created_at?: string | null;
  stopped_at?: string | null;
}

export interface LiveSessionStopResponse {
  session_id: string;
  status: string;
  summary?: LiveSessionSummary | null;
}

export interface LiveSessionItem {
  session_id: string;
  user_id: string;
  status: string;
  frame_count: number;
  duration_seconds: number;
  total_safety_events: number;
  created_at: string;
  last_activity_at?: string | null;
  stopped_at?: string | null;
}

export interface LiveSessionListResponse {
  items: LiveSessionItem[];
  total: number;
}

const API_BASE_URL =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) ||
  "http://localhost:8000/api/v1";

/**
 * Retrieve authorization headers from localStorage or session.
 */
function getAuthHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Create a new live monitoring session with isolated tracker and analyzer state.
 */
export async function createLiveSession(): Promise<LiveSessionCreateResponse> {
  const response = await fetch(`${API_BASE_URL}/live/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create session (${response.status})`);
  }

  return response.json();
}

/**
 * Send an individual sampled webcam frame to the backend for real-time analysis.
 */
export async function sendLiveFrame(
  sessionId: string,
  frameBlob: Blob
): Promise<LiveFrameResponse> {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("frame", frameBlob, "webcam_frame.jpg");

  const response = await fetch(`${API_BASE_URL}/live/frame`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Frame processing failed (${response.status})`);
  }

  return response.json();
}

/**
 * Terminate an active live session, release tracker resources, and record summary.
 */
export async function stopLiveSession(sessionId: string): Promise<LiveSessionStopResponse> {
  const response = await fetch(`${API_BASE_URL}/live/sessions/${sessionId}/stop`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to stop session (${response.status})`);
  }

  return response.json();
}

/**
 * Retrieve current status and metadata for a specific live session.
 */
export async function getLiveSession(sessionId: string): Promise<LiveSessionItem> {
  const response = await fetch(`${API_BASE_URL}/live/sessions/${sessionId}`, {
    method: "GET",
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch session (${response.status})`);
  }

  return response.json();
}

/**
 * List live monitoring sessions created by the authenticated user.
 */
export async function listLiveSessions(
  skip: number = 0,
  limit: number = 20
): Promise<LiveSessionListResponse> {
  const response = await fetch(`${API_BASE_URL}/live/sessions?skip=${skip}&limit=${limit}`, {
    method: "GET",
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to list sessions (${response.status})`);
  }

  return response.json();
}
