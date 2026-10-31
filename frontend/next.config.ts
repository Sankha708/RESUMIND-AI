import type { NextConfig } from "next";

const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim();
const apiOrigin = (() => {
  try {
    return apiBase ? new URL(apiBase).origin : "'self'";
  } catch {
    return "'self'";
  }
})();
const connectSources = ["'self'", apiOrigin];
const scriptSources = ["'self'", "'unsafe-inline'"];
if (process.env.NODE_ENV !== "production") {
  connectSources.push("http://localhost:8000", "http://127.0.0.1:8000");
}
if (process.env.NODE_ENV === "development") {
  // React/Next development tooling uses eval-based source reconstruction. Keep
  // this permission out of the production policy.
  scriptSources.push("'unsafe-eval'");
}

const securityHeaders = [
  { key: "Content-Security-Policy", value: `default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src ${scriptSources.join(" ")}; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src ${connectSources.join(" ")}` },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];
if (process.env.ENABLE_HSTS === "true") {
  securityHeaders.push({
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains",
  });
}

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  distDir: process.env.RESUMIND_NEXT_DIST_DIR || ".next",
  typescript: {
    tsconfigPath: process.env.RESUMIND_NEXT_TSCONFIG_PATH || "tsconfig.json",
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
