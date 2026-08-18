import { CorporateError } from "./errors.js";

export type BreakerState = "closed" | "open" | "half_open";

export class CircuitBreaker {
  private stateValue: BreakerState = "closed";
  private failures = 0;
  private openedAt = 0;
  private probeInFlight = false;
  public constructor(private readonly threshold = 5, private readonly recoveryMs = 30_000, private readonly now = Date.now) {
    if (threshold < 1 || recoveryMs < 1) throw new RangeError("Circuit breaker values must be positive.");
  }
  public get state(): BreakerState { return this.stateValue; }
  public beforeCall(): void {
    if (this.stateValue === "closed") return;
    if (this.stateValue === "open") {
      if (this.now() - this.openedAt < this.recoveryMs) throw new CorporateError("circuit_open", "Dependency circuit is open.");
      this.stateValue = "half_open"; this.probeInFlight = true; return;
    }
    if (this.probeInFlight) throw new CorporateError("circuit_open", "Dependency circuit probe is in progress.");
    this.probeInFlight = true;
  }
  public success(): void { this.stateValue = "closed"; this.failures = 0; this.probeInFlight = false; }
  public failure(): void {
    this.probeInFlight = false; this.failures += 1;
    if (this.stateValue === "half_open" || this.failures >= this.threshold) { this.stateValue = "open"; this.openedAt = this.now(); }
  }
}

export interface RetryPolicy { maxAttempts: number; baseDelayMs: number; maxDelayMs: number; maxElapsedMs: number; }
export interface ResilientClientOptions { allowedHosts: ReadonlySet<string>; retry?: Partial<RetryPolicy>; breaker?: CircuitBreaker; timeoutMs?: number; maxResponseBytes?: number; allowHttp?: boolean; }

export class ResilientHttpClient {
  private readonly retry: RetryPolicy;
  private readonly breaker: CircuitBreaker;
  private readonly timeoutMs: number;
  private readonly maxResponseBytes: number;
  private readonly retryable = new Set([408, 425, 429, 500, 502, 503, 504]);
  public constructor(private readonly options: ResilientClientOptions) {
    if (options.allowedHosts.size === 0) throw new RangeError("At least one allowed host is required.");
    this.retry = { maxAttempts: 3, baseDelayMs: 250, maxDelayMs: 4_000, maxElapsedMs: 15_000, ...options.retry };
    this.breaker = options.breaker ?? new CircuitBreaker();
    this.timeoutMs = options.timeoutMs ?? 5_000;
    this.maxResponseBytes = options.maxResponseBytes ?? 1_048_576;
  }

  public async request(urlValue: string, init: RequestInit = {}): Promise<Response> {
    const url = new URL(urlValue);
    const allowedScheme = url.protocol === "https:" || (this.options.allowHttp === true && url.protocol === "http:");
    if (!allowedScheme || url.username || url.password || !this.options.allowedHosts.has(url.hostname.toLowerCase())) throw new CorporateError("host_not_allowed", "Destination URL is not allowed.");
    const method = (init.method ?? "GET").toUpperCase();
    const headers = new Headers(init.headers);
    const idempotent = new Set(["GET", "HEAD", "PUT", "DELETE", "OPTIONS"]).has(method) || headers.has("Idempotency-Key");
    if (!idempotent) throw new CorporateError("non_idempotent_request", "A non-idempotent request requires an Idempotency-Key header.");
    this.breaker.beforeCall();
    const started = Date.now();
    let lastCause: unknown;
    for (let attempt = 1; attempt <= this.retry.maxAttempts; attempt += 1) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(new Error("request timeout")), this.timeoutMs);
      try {
        const response = await fetch(url, { ...init, method, headers, signal: controller.signal });
        const contentLength = Number(response.headers.get("content-length") ?? 0);
        if (contentLength > this.maxResponseBytes) throw new CorporateError("response_too_large", "Dependency response exceeds the configured limit.");
        if (!this.retryable.has(response.status)) { this.breaker.success(); return response; }
        lastCause = new Error(`retryable HTTP ${response.status}`);
        await response.body?.cancel();
      } catch (cause) { lastCause = cause; }
      finally { clearTimeout(timeout); }
      if (attempt === this.retry.maxAttempts) break;
      const exponential = Math.min(this.retry.maxDelayMs, this.retry.baseDelayMs * 2 ** (attempt - 1));
      const delay = exponential * (0.5 + Math.random());
      if (Date.now() - started + delay >= this.retry.maxElapsedMs) break;
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
    this.breaker.failure();
    throw new CorporateError("dependency_unavailable", "Dependency remained unavailable after retries.", { cause: lastCause });
  }
}
