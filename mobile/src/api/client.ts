/**
 * SemPKM API client for the mobile app.
 *
 * Mirrors the extension's SemPKMClient pattern with TypeScript types.
 * All methods use fetch() with Authorization: Bearer header.
 *
 * @module api/client
 */

// ── Response types matching backend Pydantic models ─────────────

/** Discovery document from GET /.well-known/sempkm */
export interface InstanceInfo {
  version: string;
  endpoints: Record<string, string>;
  auth: Record<string, boolean | string>;
  capabilities: string[];
}

/**
 * Current context snapshot from GET /api/context/current.
 *
 * All fields are optional/nullable — a freshly created user may have
 * no context at all (the endpoint returns `{ context: null }`).
 */
export interface ContextResponse {
  location_zone: string | null;
  activity: string | null;
  time_period: string | null;
  calendar_event: string | null;
  calendar_busy: boolean;
  device_id: string | null;
  is_stale: boolean;
  ttl_seconds: number;
  updated_at: string;
  created_at: string;
}

/** Geofence zone from GET/POST/PUT /api/context/zones. */
export interface Zone {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

/** Payload for creating a zone. Omits server-assigned fields. */
export interface ZoneCreatePayload {
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  enabled: boolean;
}

/** Payload for POST /api/context/update. All fields optional. */
export interface ContextUpdate {
  location_zone?: string | null;
  activity?: string | null;
  time_period?: string | null;
  calendar_event?: string | null;
  calendar_busy?: boolean | null;
  device_id?: string | null;
}

// ── Notification types ──────────────────────────────────────────

/** User's notification preferences from GET/PUT /api/notifications/preferences. */
export interface NotificationPreferences {
  enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  suppress_when_busy: boolean;
  enabled_types: string[];
}

/** Payload for POST /api/notifications/register. */
export interface RegisterTokenPayload {
  token: string;
  platform: string;
  device_name?: string;
}

/** Response from POST /api/notifications/test. */
export interface TestNotificationResponse {
  sent_count: number;
  suppressed: boolean;
  reason?: string | null;
}

// ── Media scheduler types ───────────────────────────────────────

/**
 * Current media suggestion from the media-scheduler app.
 * Returned by GET /app/media-scheduler/_fragments/current-suggestion/json.
 */
export interface MediaSuggestion {
  title: string;
  slot_start: string;
  slot_end: string;
  status: 'now' | 'next' | 'none';
  source_type: 'podcast' | 'youtube' | 'spotify' | null;
  source_title: string | null;
  enclosure_url: string | null;
  duration_seconds: number | null;
}

// ── Error class ─────────────────────────────────────────────────

/**
 * Custom error for SemPKM API failures.
 * Carries the HTTP status code and parsed detail from the backend.
 */
export class SemPKMError extends Error {
  readonly status: number;
  readonly detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = 'SemPKMError';
    this.status = status;
    this.detail = detail;
  }
}

// ── Client ──────────────────────────────────────────────────────

/**
 * SemPKM API client.
 *
 * Usage:
 *   const client = new SemPKMClient('https://sempkm.example.com', 'my-api-key');
 *   const info = await client.connect();
 *   const ctx  = await client.getCurrentContext();
 */
export class SemPKMClient {
  private readonly instanceUrl: string;
  private readonly apiKey: string;

  constructor(instanceUrl: string, apiKey: string) {
    // Strip trailing slashes for consistent URL construction
    this.instanceUrl = instanceUrl.replace(/\/+$/, '');
    this.apiKey = apiKey;
  }

  /** Standard headers for every API request. */
  private headers(): HeadersInit {
    return {
      Authorization: `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Generic fetch wrapper with uniform error handling.
   *
   * On non-ok responses, attempts to parse a JSON error body for
   * the `detail` field (FastAPI convention), falling back to statusText.
   * Network errors are wrapped in SemPKMError with status 0.
   */
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.instanceUrl}${path}`;

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers: {
          ...this.headers(),
          ...(options.headers as Record<string, string> | undefined),
        },
      });
    } catch (err) {
      // Network error (DNS failure, timeout, offline, etc.)
      const message = err instanceof Error ? err.message : String(err);
      throw new SemPKMError(
        `Network error: ${message}`,
        0,
        message,
      );
    }

    if (!response.ok) {
      let detail: string | null = null;
      try {
        const body = await response.json();
        detail = body.detail ?? body.error ?? JSON.stringify(body);
      } catch {
        detail = response.statusText;
      }
      throw new SemPKMError(
        `API request failed: ${response.status} ${detail}`,
        response.status,
        detail,
      );
    }

    return response.json() as Promise<T>;
  }

  // ── Public methods ──────────────────────────────────────────

  /**
   * Test connection to the SemPKM instance.
   * GET /.well-known/sempkm
   *
   * This is the first call a client should make — it validates both
   * network reachability and API key validity.
   */
  async connect(): Promise<InstanceInfo> {
    return this.request<InstanceInfo>('/.well-known/sempkm');
  }

  /**
   * Fetch the caller's current context snapshot.
   * GET /api/context/current
   *
   * Returns null when the user has never posted context.
   * The backend wraps the data in `{ context: ... }`.
   */
  async getCurrentContext(): Promise<ContextResponse | null> {
    const data = await this.request<{ context: ContextResponse | null }>(
      '/api/context/current',
    );
    return data.context;
  }

  /**
   * Update the caller's context.
   * POST /api/context/update
   *
   * Only provided fields are persisted; omitted fields are unchanged.
   * Returns the full context snapshot after the write.
   */
  async updateContext(update: ContextUpdate): Promise<ContextResponse> {
    return this.request<ContextResponse>('/api/context/update', {
      method: 'POST',
      body: JSON.stringify(update),
    });
  }

  // ── Zone CRUD ───────────────────────────────────────────────

  /**
   * List all geofence zones for the authenticated user.
   * GET /api/context/zones
   */
  async getZones(): Promise<Zone[]> {
    return this.request<Zone[]>('/api/context/zones');
  }

  /**
   * Create a new geofence zone.
   * POST /api/context/zones → 201
   */
  async createZone(zone: ZoneCreatePayload): Promise<Zone> {
    return this.request<Zone>('/api/context/zones', {
      method: 'POST',
      body: JSON.stringify(zone),
    });
  }

  /**
   * Update a geofence zone. Only provided fields are changed.
   * PUT /api/context/zones/{id}
   */
  async updateZone(id: string, zone: Partial<ZoneCreatePayload>): Promise<Zone> {
    return this.request<Zone>(`/api/context/zones/${id}`, {
      method: 'PUT',
      body: JSON.stringify(zone),
    });
  }

  /**
   * Delete a geofence zone.
   * DELETE /api/context/zones/{id} → 204 No Content
   */
  async deleteZone(id: string): Promise<void> {
    const url = `${this.instanceUrl}/api/context/zones/${id}`;

    let response: Response;
    try {
      response = await fetch(url, {
        method: 'DELETE',
        headers: this.headers(),
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new SemPKMError(`Network error: ${message}`, 0, message);
    }

    if (!response.ok) {
      let detail: string | null = null;
      try {
        const body = await response.json();
        detail = body.detail ?? body.error ?? JSON.stringify(body);
      } catch {
        detail = response.statusText;
      }
      throw new SemPKMError(
        `API request failed: ${response.status} ${detail}`,
        response.status,
        detail,
      );
    }
    // 204 No Content — no body to parse
  }

  // ── Notification methods ──────────────────────────────────────

  /**
   * Register a native push token (FCM/APNs) with the backend.
   * POST /api/notifications/register
   */
  async registerPushToken(
    token: string,
    platform: string,
    deviceName?: string,
  ): Promise<void> {
    const payload: RegisterTokenPayload = { token, platform };
    if (deviceName) payload.device_name = deviceName;

    await this.request<{ status: string }>('/api/notifications/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Get the current user's notification preferences.
   * GET /api/notifications/preferences
   */
  async getNotificationPreferences(): Promise<NotificationPreferences> {
    return this.request<NotificationPreferences>('/api/notifications/preferences');
  }

  /**
   * Update notification preferences. Only provided fields are changed.
   * PUT /api/notifications/preferences
   */
  async updateNotificationPreferences(
    prefs: Partial<NotificationPreferences>,
  ): Promise<NotificationPreferences> {
    return this.request<NotificationPreferences>('/api/notifications/preferences', {
      method: 'PUT',
      body: JSON.stringify(prefs),
    });
  }

  /**
   * Send a test notification to the current user's devices.
   * POST /api/notifications/test
   *
   * Returns delivery info including suppression status.
   */
  async sendTestNotification(): Promise<TestNotificationResponse> {
    return this.request<TestNotificationResponse>('/api/notifications/test', {
      method: 'POST',
    });
  }

  // ── Media scheduler ─────────────────────────────────────────

  /**
   * Fetch the current or next media suggestion from the media-scheduler app.
   * GET /app/media-scheduler/_fragments/current-suggestion/json
   *
   * Returns the suggestion with deep-link URL for native playback.
   * Throws SemPKMError on network or API failure.
   */
  async getMediaSuggestion(): Promise<MediaSuggestion> {
    return this.request<MediaSuggestion>(
      '/app/media-scheduler/_fragments/current-suggestion/json',
    );
  }
}
