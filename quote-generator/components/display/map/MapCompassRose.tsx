'use client';

import React from 'react';

interface MapCompassRoseProps {
  className?: string;
  size?: number;
  color?: string;
}

export function MapCompassRose({
  className = '',
  size = 110,
  color = 'var(--color-accent)',
}: MapCompassRoseProps) {
  return (
    <div
      className={`luxury-compass-rose ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 100 100"
        width={size}
        height={size}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full drop-shadow-sm"
      >
        {/* Outer Ring & Minute Marks */}
        <circle cx="50" cy="50" r="46" stroke={color} strokeWidth="0.75" strokeOpacity="0.4" />
        <circle cx="50" cy="50" r="42" stroke={color} strokeWidth="0.5" strokeDasharray="1.5 2" strokeOpacity="0.6" />
        <circle cx="50" cy="50" r="38" stroke={color} strokeWidth="0.5" strokeOpacity="0.3" />

        {/* 4 Cardinal Rays Background (Minor Points) */}
        <g stroke={color} strokeWidth="0.5" strokeOpacity="0.25">
          <line x1="50" y1="12" x2="50" y2="88" />
          <line x1="12" y1="50" x2="88" y2="50" />
          <line x1="23" y1="23" x2="77" y2="77" strokeDasharray="1 3" />
          <line x1="77" y1="23" x2="23" y2="77" strokeDasharray="1 3" />
        </g>

        {/* Secondary Points (NE, NW, SE, SW) */}
        <polygon points="50,50 48,34 50,22 50,50" fill={color} fillOpacity="0.35" />
        <polygon points="50,50 52,34 50,22 50,50" fill={color} fillOpacity="0.15" />

        <polygon points="50,50 66,48 78,50 50,50" fill={color} fillOpacity="0.35" />
        <polygon points="50,50 66,52 78,50 50,50" fill={color} fillOpacity="0.15" />

        <polygon points="50,50 52,66 50,78 50,50" fill={color} fillOpacity="0.35" />
        <polygon points="50,50 48,66 50,78 50,50" fill={color} fillOpacity="0.15" />

        <polygon points="50,50 34,52 22,50 50,50" fill={color} fillOpacity="0.35" />
        <polygon points="50,50 34,48 22,50 50,50" fill={color} fillOpacity="0.15" />

        {/* Major Cardinal Star Points (North, East, South, West) */}
        {/* North Main Point */}
        <polygon points="50,50 46,28 50,8 50,50" fill={color} fillOpacity="0.85" />
        <polygon points="50,50 54,28 50,8 50,50" fill={color} fillOpacity="0.45" />

        {/* East Main Point */}
        <polygon points="50,50 72,46 92,50 50,50" fill={color} fillOpacity="0.75" />
        <polygon points="50,50 72,54 92,50 50,50" fill={color} fillOpacity="0.35" />

        {/* South Main Point */}
        <polygon points="50,50 54,72 50,92 50,50" fill={color} fillOpacity="0.75" />
        <polygon points="50,50 46,72 50,92 50,50" fill={color} fillOpacity="0.35" />

        {/* West Main Point */}
        <polygon points="50,50 28,54 8,50 50,50" fill={color} fillOpacity="0.75" />
        <polygon points="50,50 28,46 8,50 50,50" fill={color} fillOpacity="0.35" />

        {/* Center Pivot Ring & Core Pearl */}
        <circle cx="50" cy="50" r="5" fill="var(--color-surface)" stroke={color} strokeWidth="1" />
        <circle cx="50" cy="50" r="2.5" fill={color} />

        {/* North Arrow / Fleur-de-lis Top Accent */}
        <path
          d="M50 3 L47 7 L50 6 L53 7 Z"
          fill={color}
        />

        {/* Cardinal Letters */}
        <text
          x="50"
          y="6.5"
          textAnchor="middle"
          dominantBaseline="central"
          fill={color}
          fontSize="5.5"
          fontFamily="serif"
          fontWeight="600"
          letterSpacing="0.05em"
        >
          N
        </text>
        <text
          x="94.5"
          y="50.5"
          textAnchor="middle"
          dominantBaseline="central"
          fill={color}
          fontSize="4.5"
          fontFamily="serif"
          fontWeight="500"
        >
          E
        </text>
        <text
          x="50"
          y="95"
          textAnchor="middle"
          dominantBaseline="central"
          fill={color}
          fontSize="4.5"
          fontFamily="serif"
          fontWeight="500"
        >
          S
        </text>
        <text
          x="5.5"
          y="50.5"
          textAnchor="middle"
          dominantBaseline="central"
          fill={color}
          fontSize="4.5"
          fontFamily="serif"
          fontWeight="500"
        >
          W
        </text>
      </svg>
    </div>
  );
}
