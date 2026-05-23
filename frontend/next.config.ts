import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // In production, NEXT_PUBLIC_API_URL points to the Render backend.
  // In development, it defaults to localhost:8001.
  // No rewrites needed — the browser calls the API directly.
};

export default nextConfig;
