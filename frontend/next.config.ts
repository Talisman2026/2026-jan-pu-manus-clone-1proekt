import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return [
      { source: '/auth/:path*', destination: `${apiUrl}/auth/:path*` },
      { source: '/tasks/:path*', destination: `${apiUrl}/tasks/:path*` },
      { source: '/health', destination: `${apiUrl}/health` },
    ]
  },
}

export default nextConfig
