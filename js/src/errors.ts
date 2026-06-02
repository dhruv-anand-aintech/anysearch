/** Exception hierarchy mirroring the Python SDK. */

export class AnySearchError extends Error {
  constructor(message: string) {
    super(message);
    this.name = new.target.name;
  }
}

export class ConfigurationError extends AnySearchError {}

export class MissingAPIKeyError extends ConfigurationError {
  provider: string;
  constructor(provider: string, hint = "") {
    super(`No credentials configured for provider '${provider}'.${hint ? " " + hint : ""}`);
    this.provider = provider;
  }
}

export class ProviderNotFoundError extends ConfigurationError {
  provider: string;
  constructor(provider: string, known: string[] = []) {
    super(
      `Unknown search provider '${provider}'.` +
        (known.length ? ` Available: ${[...known].sort().join(", ")}.` : ""),
    );
    this.provider = provider;
  }
}

export class NoProviderAvailableError extends ConfigurationError {}

export class UnsupportedParameterError extends AnySearchError {
  provider: string;
  params: string[];
  constructor(provider: string, params: string[]) {
    super(`Provider '${provider}' does not support parameter(s): ${params.join(", ")}.`);
    this.provider = provider;
    this.params = params;
  }
}

export class ProviderError extends AnySearchError {
  provider: string;
  statusCode?: number;
  response?: unknown;
  constructor(message: string, opts: { provider: string; statusCode?: number; response?: unknown }) {
    const prefix = `[${opts.provider}]${opts.statusCode != null ? ` HTTP ${opts.statusCode}` : ""}`;
    super(`${prefix}: ${message}`);
    this.provider = opts.provider;
    this.statusCode = opts.statusCode;
    this.response = opts.response;
  }
}

export class AuthenticationError extends ProviderError {}
export class RateLimitError extends ProviderError {}
export class BadRequestError extends ProviderError {}
export class ProviderTimeoutError extends ProviderError {}
export class ProviderConnectionError extends ProviderError {}

/** True for errors a fallback chain should recover from. */
export function isRecoverable(err: unknown): boolean {
  return err instanceof ProviderError || err instanceof MissingAPIKeyError;
}
