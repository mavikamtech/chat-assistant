'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import ChatInterface from '@/components/chat-interface';
import { isAuthenticated } from '@/lib/cognito';

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
    } else {
      setLoading(false);
    }
  }, [router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#343541]">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  return <ChatInterface />;
}
