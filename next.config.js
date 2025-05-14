/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // keep this
  experimental: {
    appDir: true,
  },
};

module.exports = nextConfig;
