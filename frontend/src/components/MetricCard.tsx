import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  titleSwahili: string;
  value: string;
  change: string;
  changeType: 'increase' | 'decrease' | 'neutral';
  icon: LucideIcon;
  color: 'maroon' | 'gold' | 'red' | 'green' | 'blue' | 'purple';
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  titleSwahili,
  value,
  change,
  changeType,
  icon: Icon,
  color
}) => {
  const colorClasses = {
    maroon: 'text-legal-maroon bg-legal-maroon-light',
    gold: 'text-legal-gold-dark bg-legal-gold-light',
    red: 'text-red-600 bg-red-50',
    green: 'text-green-600 bg-green-50',
    blue: 'text-blue-600 bg-blue-50',
    purple: 'text-purple-600 bg-purple-50'
  };

  return (
    <div className="legal-card p-6 hover:shadow-legal-lg transition-all duration-300">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-legal-text-muted">{title}</p>
          <p className="text-xs text-legal-text-muted/70">{titleSwahili}</p>
          <p className="text-2xl font-serif font-bold text-legal-gold-dark mt-2">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
      {change && (
        <div className="mt-4 flex items-center">
          <span
            className={`text-sm font-medium ${
              changeType === 'increase' ? 'text-green-600' : 
              changeType === 'decrease' ? 'text-red-600' : 
              'text-legal-text-muted'
            }`}
          >
            {change}
          </span>
          <span className="text-sm text-legal-text-muted ml-2">from last period</span>
        </div>
      )}
    </div>
  );
};

export default MetricCard;
