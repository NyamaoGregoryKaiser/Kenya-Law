import React, { useEffect, useState } from 'react';

interface WatermarkCoAProps {
	className?: string;
	src?: string; // defaults to /assets/kenya/coat-of-arms.png
	alt?: string;
}

const ASSET_BASE = process.env.PUBLIC_URL || '';

const WatermarkCoA: React.FC<WatermarkCoAProps> = ({
	className = '',
	src,
	alt = 'Kenya Coat of Arms',
}) => {
	const [show, setShow] = useState(true);
	const resolvedSrc = src || `${ASSET_BASE}/assets/kenya/coat-of-arms.png`;

	useEffect(() => {
		const img = new Image();
		img.onload = () => setShow(true);
		img.onerror = () => setShow(false);
		img.src = resolvedSrc;
	}, [resolvedSrc]);

	if (!show) return null;

	return (
		<div className={`watermark-coa ${className}`}>
			<img src={resolvedSrc} alt={alt} className="coa-image" />
		</div>
	);
};

export default WatermarkCoA;
