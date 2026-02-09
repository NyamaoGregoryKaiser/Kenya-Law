import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in Leaflet with Webpack
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.3/images/marker-shadow.png',
});

const MapWidget: React.FC = () => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);

  useEffect(() => {
    if (mapRef.current && !mapInstance.current) {
      // Initialize map centered on Kenya
      mapInstance.current = L.map(mapRef.current).setView([-0.0236, 37.9062], 6);

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(mapInstance.current);

      // Court locations across Kenya - Using maroon/gold theme
      const courts = [
        {
          lat: -1.2921,
          lng: 36.8219,
          title: 'Supreme Court of Kenya',
          type: 'supreme',
          judgments: 234,
          city: 'Nairobi'
        },
        {
          lat: -1.2833,
          lng: 36.8167,
          title: 'Court of Appeal - Nairobi',
          type: 'appeal',
          judgments: 1567,
          city: 'Nairobi'
        },
        {
          lat: -1.2864,
          lng: 36.8172,
          title: 'High Court - Nairobi',
          type: 'high',
          judgments: 4521,
          city: 'Nairobi'
        },
        {
          lat: -4.0437,
          lng: 39.6682,
          title: 'High Court - Mombasa',
          type: 'high',
          judgments: 1234,
          city: 'Mombasa'
        },
        {
          lat: -0.0917,
          lng: 34.7680,
          title: 'High Court - Kisumu',
          type: 'high',
          judgments: 892,
          city: 'Kisumu'
        },
        {
          lat: 0.5143,
          lng: 35.2698,
          title: 'High Court - Eldoret',
          type: 'high',
          judgments: 756,
          city: 'Eldoret'
        },
        {
          lat: -0.2827,
          lng: 36.0666,
          title: 'High Court - Nakuru',
          type: 'high',
          judgments: 645,
          city: 'Nakuru'
        },
        {
          lat: -1.5177,
          lng: 37.2634,
          title: 'Environment & Land Court - Machakos',
          type: 'elc',
          judgments: 423,
          city: 'Machakos'
        }
      ];

      courts.forEach(court => {
        // Color based on court type - using Kenya Law maroon/gold
        const color = court.type === 'supreme' ? '#7A1F33' :  // Deep Maroon for Supreme
                     court.type === 'appeal' ? '#5C1727' :    // Dark Maroon for Appeal
                     court.type === 'high' ? '#D9A12D' :      // Gold for High Court
                     '#B8861F';                               // Dark gold for others
        
        const radius = court.type === 'supreme' ? 12 : 
                      court.type === 'appeal' ? 10 : 8;

        L.circleMarker([court.lat, court.lng], {
          radius: radius,
          fillColor: color,
          color: '#ffffff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.85
        })
        .addTo(mapInstance.current!)
        .bindPopup(`
          <div class="p-3 min-w-48">
            <h3 style="font-family: 'Merriweather', serif; font-weight: bold; font-size: 14px; color: #232323; margin-bottom: 4px;">${court.title}</h3>
            <p style="font-size: 12px; color: #5A5A5A; margin-bottom: 8px;">📍 ${court.city}</p>
            <div style="display: flex; align-items: center; justify-content: space-between; background: #F5E8EB; border-radius: 6px; padding: 8px;">
              <span style="font-size: 11px; color: #5A5A5A;">Judgments Indexed</span>
              <span style="font-size: 14px; font-weight: bold; color: #7A1F33;">${court.judgments.toLocaleString()}</span>
            </div>
          </div>
        `);
      });

      // Add a legend using Leaflet Control class
      const LegendControl = L.Control.extend({
        onAdd: function() {
          const div = L.DomUtil.create('div', 'bg-white p-3 rounded-lg shadow-lg text-xs');
          div.style.fontFamily = "'Source Sans Pro', sans-serif";
          div.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 8px; color: #232323;">Court Types</div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 12px; height: 12px; border-radius: 50%; background: #7A1F33;"></span>
                <span style="color: #5A5A5A;">Supreme Court</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 12px; height: 12px; border-radius: 50%; background: #5C1727;"></span>
                <span style="color: #5A5A5A;">Court of Appeal</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 12px; height: 12px; border-radius: 50%; background: #D9A12D;"></span>
                <span style="color: #5A5A5A;">High Court</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 12px; height: 12px; border-radius: 50%; background: #B8861F;"></span>
                <span style="color: #5A5A5A;">Specialized Courts</span>
              </div>
            </div>
          `;
          return div;
        }
      });
      new LegendControl({ position: 'bottomright' }).addTo(mapInstance.current);
    }

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, []);

  return (
    <div className="w-full h-80 rounded-lg overflow-hidden border border-legal-border">
      <div ref={mapRef} className="w-full h-full" />
    </div>
  );
};

export default MapWidget;
