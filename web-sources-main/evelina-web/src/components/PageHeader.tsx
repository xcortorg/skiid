import React from 'react';

interface PageHeaderProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function PageHeader({ icon, title, description }: PageHeaderProps) {
  return (
    <div className="flex items-center mb-12">
      <div className="w-16 h-16 bg-theme/10 rounded-xl flex items-center justify-center mr-6 flex-shrink-0">
        {React.cloneElement(icon as React.ReactElement, { className: 'w-8 h-8 text-theme' })}
      </div>
      <div className="flex flex-col justify-center h-16">
        <h1 className="text-2xl font-bold leading-tight">{title}</h1>
        <p className="text-base text-gray-400 leading-tight">
          {description}
        </p>
      </div>
    </div>
  );
}

export default PageHeader;