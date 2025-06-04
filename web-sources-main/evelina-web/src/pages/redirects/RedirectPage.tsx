import React, { useEffect } from 'react';
import { Navigate } from 'react-router-dom';

interface RedirectPageProps {
  to: string;
  external?: boolean;
}

const RedirectPage: React.FC<RedirectPageProps> = ({ to, external = true }) => {
  useEffect(() => {
    if (external) {
      window.location.href = to;
    }
  }, [to, external]);

  return external ? (
    <div className="max-w-7xl mx-auto px-4 py-12 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">Redirecting...</h1>
        <p className="text-gray-400 mb-4">You are being redirected to {to}</p>
        <p className="text-gray-400">
          If you are not redirected automatically, please{' '}
          <a href={to} className="text-theme hover:underline">
            click here
          </a>
        </p>
      </div>
    </div>
  ) : (
    <Navigate to={to} replace />
  );
};

export default RedirectPage; 