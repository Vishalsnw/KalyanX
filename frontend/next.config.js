/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // for Vercel custom deployment environments
  experimental: {
    appDir: true, // enables app/ directory (App Router)
  },
  images: {
    domains: ['localhost', 'vercel.app'], // adjust if needed
  },
  reactStrictMode: true,
  swcMinify: true,
};

module.exports = nextConfig;
