/**
 * API client helper for test data arrangement.
 *
 * Uses Playwright's request context to call the SemPKM API directly,
 * bypassing the UI for faster test setup. Handles session cookies
 * automatically.
 */
import { APIRequestContext } from '@playwright/test';

export class ApiClient {
  constructor(
    private request: APIRequestContext,
    private baseURL: string = process.env.TEST_BASE_URL || 'http://localhost:3901',
  ) {}

  /** GET /api/health */
  async getHealth() {
    const resp = await this.request.get(`${this.baseURL}/api/health`);
    return resp.json();
  }

  /** GET /api/auth/status */
  async getAuthStatus(): Promise<{ setup_complete: boolean; setup_mode: boolean }> {
    const resp = await this.request.get(`${this.baseURL}/api/auth/status`);
    return resp.json();
  }

  /**
   * Extract the setup token from Docker container logs.
   * Falls back to reading the .setup-token file via docker exec.
   */
  async getSetupToken(): Promise<string> {
    // The setup token is written to /app/data/.setup-token in the container
    // We read it by exec-ing into the API container
    const { execSync } = await import('child_process');
    try {
      const token = execSync(
        'docker compose -f docker-compose.test.yml exec -T api cat /app/data/.setup-token',
        { cwd: `${this.baseURL.includes('localhost') ? process.cwd() + '/..' : '.'}`, encoding: 'utf-8', timeout: 5000 }
      ).trim();
      return token;
    } catch {
      // Fallback: parse from docker logs
      const logs = execSync(
        'docker compose -f docker-compose.test.yml logs api 2>&1',
        { cwd: `${this.baseURL.includes('localhost') ? process.cwd() + '/..' : '.'}`, encoding: 'utf-8', timeout: 5000 }
      );
      const match = logs.match(/Setup token:\s+(\S+)/);
      if (!match) throw new Error('Could not find setup token in API logs');
      return match[1];
    }
  }

  /** POST /api/auth/setup — claim the instance */
  async setup(token: string, email = 'owner@test.local') {
    const resp = await this.request.post(`${this.baseURL}/api/auth/setup`, {
      data: { token, email },
    });
    return { status: resp.status(), data: await resp.json(), headers: resp.headers() };
  }

  /** POST /api/auth/magic-link — request a login token */
  async requestMagicLink(email: string) {
    const resp = await this.request.post(`${this.baseURL}/api/auth/magic-link`, {
      data: { email },
    });
    return { status: resp.status(), data: await resp.json() };
  }

  /** POST /api/auth/verify — verify a magic link token and get session */
  async verifyToken(token: string) {
    const resp = await this.request.post(`${this.baseURL}/api/auth/verify`, {
      data: { token },
    });
    return { status: resp.status(), data: await resp.json(), headers: resp.headers() };
  }

  /** GET /api/auth/me — get current user info */
  async getMe() {
    const resp = await this.request.get(`${this.baseURL}/api/auth/me`);
    return { status: resp.status(), data: await resp.json() };
  }

  /** POST /api/auth/logout */
  async logout() {
    const resp = await this.request.post(`${this.baseURL}/api/auth/logout`);
    return { status: resp.status() };
  }

  /**
   * POST /api/commands — execute a command.
   * For object creation, editing, edge creation, etc.
   */
  async executeCommand(command: string, params: Record<string, unknown>) {
    const resp = await this.request.post(`${this.baseURL}/api/commands`, {
      data: { command, params },
    });
    return { status: resp.status(), data: await resp.json() };
  }

  /** Create an object via the command API */
  async createObject(type: string, properties: Record<string, string>) {
    return this.executeCommand('object.create', { type, properties });
  }

  /** Create an edge between two objects */
  async createEdge(source: string, target: string, predicate: string) {
    return this.executeCommand('edge.create', { source, target, predicate });
  }

  /** POST /api/sparql — run a SPARQL query */
  async sparql(query: string) {
    const resp = await this.request.post(`${this.baseURL}/api/sparql`, {
      data: { query },
    });
    return { status: resp.status(), data: await resp.json() };
  }

  /** POST /api/auth/invite — invite a user (requires owner session) */
  async inviteUser(email: string, role = 'member') {
    const resp = await this.request.post(`${this.baseURL}/api/auth/invite`, {
      data: { email, role },
    });
    return { status: resp.status(), data: await resp.json() };
  }
}
