'use client';

import { signIn } from 'next-auth/react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

function SignInContent() {
  const searchParams = useSearchParams();
  const error = searchParams.get('error');

  const handleSignIn = () => {
    signIn('cognito', { callbackUrl: '/' });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#202123] to-[#343541]">
      <div className="bg-[#343541] p-8 rounded-2xl shadow-2xl w-full max-w-md border border-white/10">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Mavik AI Assistant</h1>
          <p className="text-white/60 text-sm">Commercial Real Estate Analysis</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
            <p className="text-red-400 text-sm">
              {error === 'OAuthAccountNotLinked'
                ? 'This email is already associated with another account.'
                : 'An error occurred during sign in. Please try again.'}
            </p>
          </div>
        )}

        <button
          onClick={handleSignIn}
          className="w-full bg-white text-gray-900 font-semibold py-3 px-4 rounded-lg hover:bg-gray-100 transition-colors flex items-center justify-center gap-3"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"
              fill="currentColor"
              opacity="0.3"
            />
            <path
              d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zm0 8c-1.65 0-3-1.35-3-3s1.35-3 3-3 3 1.35 3 3-1.35 3-3 3z"
              fill="currentColor"
            />
          </svg>
          Sign in with Mavik Capital
        </button>

        <div className="mt-6 text-center">
          <p className="text-white/40 text-xs">
            Only authorized Mavik Capital employees can access this application
          </p>
        </div>
      </div>
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SignInContent />
    </Suspense>
  );
}
