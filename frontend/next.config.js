/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // API rewrites for production
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_BACKEND_URL
          ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/:path*`
          : 'http://localhost:8000/:path*',
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
