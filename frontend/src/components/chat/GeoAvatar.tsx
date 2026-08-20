import React from 'react';
import geoAvatarIcon from '../../assets/geo_Avatar.svg';

interface GeoAvatarProps {
  spinning?: boolean;
}

export const GeoAvatar: React.FC<GeoAvatarProps> = ({ spinning = false }) => (
  <img
    src={geoAvatarIcon}
    alt="Geologist Avatar"
    className={`w-6 h-6 object-contain rounded bg-[#2e2308] p-0.5 border border-[#efb027] ${
      spinning ? 'animate-spin' : ''
    }`}
  />
);
