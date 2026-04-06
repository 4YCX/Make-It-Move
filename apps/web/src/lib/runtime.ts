const DEFAULT_API_PORT = '8000';

function resolveConfiguredBaseUrl(envValue: string | undefined, fallbackProtocol: 'http:' | 'ws:') {
  if (envValue) {
    return envValue;
  }

  if (typeof window === 'undefined') {
    return fallbackProtocol === 'http:' ? 'http://localhost:8000' : 'ws://localhost:8000';
  }

  const url = new URL(window.location.origin);
  url.protocol = fallbackProtocol;
  url.port = DEFAULT_API_PORT;
  return url.origin;
}

export function getApiBaseUrl() {
  return resolveConfiguredBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL, 'http:');
}

export function getWsBaseUrl() {
  return resolveConfiguredBaseUrl(process.env.NEXT_PUBLIC_WS_BASE_URL, 'ws:');
}
