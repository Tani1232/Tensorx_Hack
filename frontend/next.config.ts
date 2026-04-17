import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "10.206.6.190",
    // Add other IPs/hostnames here if you test from other devices
  ],
};

export default nextConfig;
