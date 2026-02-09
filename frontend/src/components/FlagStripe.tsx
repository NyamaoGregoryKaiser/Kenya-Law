import React from 'react';

interface FlagStripeProps {
	className?: string;
	height?: number;
}

const FlagStripe: React.FC<FlagStripeProps> = ({ className = '', height = 6 }) => {
	return (
		<div
			className={`kenya-flag-stripe ${className}`}
			style={{ height }}
		/>
	);
};

export default FlagStripe;
