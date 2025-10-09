/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // API rewrites for production and development
  async rewrites() {
    return [
      {
        source: '/api/chat/:path*',
        destination: process.env.NEXT_PUBLIC_BACKEND_URL
          ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/chat/:path*`
          : 'http://localhost:8000/api/chat/:path*',
      },
    ]
  },

  // Production optimizations
  compress: true,
  poweredByHeader: false,

  // Image optimization
  images: {
    domains: ['mavik-ssot.com'],
  },
}

module.exports = nextConfig
