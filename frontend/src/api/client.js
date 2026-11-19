import axios from "axios";

export const TOKEN_KEY = "bugtracker_token";

const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api`,
});

// Attach the JWT to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// If the server says our token is no good, drop it and go back to the login page.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginCall = error.config?.url?.includes("/auth/login");
    if (error.response?.status === 401 && !isLoginCall && localStorage.getItem(TOKEN_KEY)) {
      localStorage.removeItem(TOKEN_KEY);
      window.location.assign("/login");
    }
    return Promise.reject(error);
  }
);

// Turn whatever the API sent back into one readable sentence.
export function errorMessage(error, fallback = "Something went wrong. Please try again.") {
  if (!error?.response) return "Could not reach the server.";
  const detail = error.response.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(". ");
  return fallback;
}

export default api;
