import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  async headers() {
    return [
      {
        source: '/:locale(en|vi|ar)/q/:slug',
        headers: [{ key: 'Cache-Control', value: 'public, s-maxage=300, stale-while-revalidate=86400' }],
      },
      {
        source: '/p/:fallbackSlug',
        headers: [{ key: 'Cache-Control', value: 'public, s-maxage=300, stale-while-revalidate=86400' }],
      },
    ];
  },
  async rewrites() {
    const backendUrl =
      process.env.QUOTATION_INTERNAL_API_URL ??
      process.env.NEXT_PUBLIC_QUOTATION_API_URL ??
      'http://localhost:8111';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "images.pexels.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "media.capellatravel.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "*.capellatravel.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "*.selvarajourneys.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "*.vietnamsafar.vn",
        pathname: "/**",
      },
      {
        protocol: "http",
        hostname: "localhost",
      },
      {
        protocol: "http",
        hostname: "127.0.0.1",
      },
      {
        protocol: "http",
        hostname: "host.docker.internal",
      },
      {
        protocol: "http",
        hostname: "quote-generator",
      },
      {
        protocol: "http",
        hostname: "app",
      },
    ],
  },
};

export default nextConfig;
