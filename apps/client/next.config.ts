import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
      {
        protocol: "https",
        hostname: "shadcnblocks.com",
      },
    ],
  },
  async rewrites() {
    const gatewayUrl = process.env.GATEWAY_URL || "http://gateway:8080";
    return [
      {
        source: "/api/:path*",
        destination: `${gatewayUrl}/api/:path*`,
      },
      {
        source: "/ws/:path*",
        destination: `${gatewayUrl}/ws/:path*`,
      },
    ];
  },
};

export default nextConfig;
