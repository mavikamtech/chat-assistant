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

  // Expose public runtime config for environment variables
  publicRuntimeConfig: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
    NEXT_PUBLIC_COGNITO_USER_POOL_ID: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
    NEXT_PUBLIC_COGNITO_CLIENT_ID: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
  },

  // Environment variables for build-time replacement
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000/api',
    NEXT_PUBLIC_COGNITO_USER_POOL_ID: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
    NEXT_PUBLIC_COGNITO_CLIENT_ID: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '',
  },
}

module.exports = nextConfig
