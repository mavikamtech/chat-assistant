/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // API rewrites for production
  async rewrites() {
    return [
      {
        source: '/api/chat/:path*',
        destination: process.env.NEXT_PUBLIC_BACKEND_URL
          ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/chat/:path*`
          : 'http://localhost:8000/chat/:path*',
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
