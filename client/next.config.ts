import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enables a minimal standalone server.js output for the production Docker image.
  output: "standalone",
};

export default nextConfig;
