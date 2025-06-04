import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const StaffRedirect: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/staff/overview', { replace: true });
  }, [navigate]);

  return (
    <div className="flex items-center justify-center h-[50vh]">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
    </div>
  );
};

export default StaffRedirect; 