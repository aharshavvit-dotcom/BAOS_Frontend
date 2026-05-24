import React from 'react';

type ChartCardProps = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
};

export default function ChartCard({ title, subtitle, children, className = '' }: ChartCardProps) {
  return (
    <div className={`baos-card p-6 flex flex-col justify-between ${className}`}>
      <div className="mb-6">
        <h3 className="text-lg font-extrabold text-slate-900 tracking-tight">
          {title}
        </h3>
        {subtitle && (
          <p className="mt-1 text-sm text-slate-500 font-medium">
            {subtitle}
          </p>
        )}
      </div>
      <div className="h-[320px] w-full min-w-0">
        {children}
      </div>
    </div>
  );
}
