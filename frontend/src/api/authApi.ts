const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export async function login(username: string, password: string): Promise<LoginResponse> {
  const formData = new URLSearchParams();

  formData.append("username", username);
  formData.append("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      errorText || `Login failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<LoginResponse>;
}
