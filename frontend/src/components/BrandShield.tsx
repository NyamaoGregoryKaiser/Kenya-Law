import React, { useState } from 'react';

interface BrandShieldProps {
	className?: string;
	imgSrc?: string; // defaults to /assets/kenya/shield.png
	size?: number;
	alt?: string;
}

const ASSET_BASE = process.env.PUBLIC_URL || '';

const BrandShield: React.FC<BrandShieldProps> = ({
	className = '',
	imgSrc,
	size = 56,
	alt = 'Kenyan Shield',
}) => {
	const [imgOk, setImgOk] = useState(true);
	const resolvedSrc = imgSrc || `${ASSET_BASE}/assets/kenya/shield.png`;

	return imgOk ? (
		<img
			src={resolvedSrc}
			alt={alt}
			width={size}
			height={size}
			className={className}
			onError={() => setImgOk(false)}
		/>
	) : (
		<div className={`kenya-shield ${className}`} style={{ width: size, height: size }} />
	);
};

export default BrandShield;
