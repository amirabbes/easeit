const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('easeit_token');
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text || `La requête a échoué (HTTP ${response.status}).`;
    if (text) {
      try {
        const payload = JSON.parse(text) as { detail?: unknown; message?: unknown };
        if (typeof payload.detail === 'string') message = payload.detail;
        else if (typeof payload.message === 'string') message = payload.message;
        else if (payload.detail !== undefined) message = JSON.stringify(payload.detail);
      } catch {
        // Keep the response text when the server does not return JSON.
      }
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
