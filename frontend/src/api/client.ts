const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown; // Expect raw objects or FormData, never pre-stringified strings
  token?: string | null;
};

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const headers: Record<string, string> = {};

  // Set Authorization header if token exists
  if (options.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }

  let requestBody: BodyInit | undefined = undefined;

  // Dynamically determine headers and body formatting based on payload type
  if (options.body !== undefined) {
    if (options.body instanceof FormData) {
      // For FormData uploads, the browser must set the multipart boundary automatically.
      // Explicitly leaving Content-Type empty lets the browser insert the boundary tag.
      requestBody = options.body;
    } else {
      // Safe fallback for standard JSON objects
      headers["Content-Type"] = "application/json";
      requestBody = JSON.stringify(options.body);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body: requestBody,
  });

  if (!response.ok) {
    let errorMessage = `API request failed with status ${response.status}`;
    try {
      // Attempt to parse structured error details from FastAPI if available
      const errorJson = await response.json();
      errorMessage = errorJson?.detail || JSON.stringify(errorJson) || errorMessage;
    } catch {
      // Fallback if the response is raw text instead of JSON
      const errorText = await response.text();
      if (errorText) errorMessage = errorText;
    }

    throw new Error(errorMessage);
  }

  // Handle successful empty responses safely
  const responseText = await response.text();
  return responseText ? (JSON.parse(responseText) as T) : ({} as T);
}