import type { NextConfig } from 'next';
const nextConfig: NextConfig = {
  poweredByHeader: false,
  distDir: process.env.RUYA_E2E === '1' ? '.next-e2e' : '.next',
};
export default nextConfig;
