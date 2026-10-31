/**
 * Resolves a consistent local API host for the browser.
 *
 * `localhost` and `127.0.0.1` are different cookie sites. In local development,
 * pair the API hostname with the hostname used to open the frontend so that the
 * HttpOnly session cookie remains first-party/same-site. An explicit remote API
 * URL remains untouched.
 */
export function getApiBaseUrl(): string {
  const configured = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim();
  const fallbackHost =
    typeof window !== "undefined" && window.location.hostname === "localhost"
      ? "localhost"
      : "127.0.0.1";
  const raw = configured || `http://${fallbackHost}:8000`;

  try {
    const parsed = new URL(raw);
    const loopbackHosts = new Set(["localhost", "127.0.0.1"]);
    if (
      typeof window !== "undefined" &&
      loopbackHosts.has(parsed.hostname) &&
      loopbackHosts.has(window.location.hostname)
    ) {
      parsed.hostname = window.location.hostname;
    }
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return raw.replace(/\/+$/, "");
  }
}
