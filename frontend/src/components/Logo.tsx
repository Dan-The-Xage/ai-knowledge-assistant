'use client';

import React from 'react';

interface LogoProps {
  className?: string;
  showText?: boolean;
}

export const Logo = ({ className = "h-10", showText = true }: LogoProps) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* DSN Logo */}
      <div className="relative flex items-center justify-start h-full shrink-0">
        <img
          src="/dsn-logo.svg"
          alt="DSN Logo"
          className="h-full w-auto object-contain max-w-[180px]"
        />
      </div>

      {/* App Name - "DocuLens" */}
      {showText && (
        <div className="flex flex-col justify-center h-8">
           <span className="font-normal text-dsn-blue text-xl tracking-tight border-l-2 border-gray-300 pl-3 ml-1 leading-none flex items-center h-full">
             DocuLens
           </span>
        </div>
      )}
    </div>
  );
};
