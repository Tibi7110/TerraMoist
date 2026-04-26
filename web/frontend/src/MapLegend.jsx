import React from 'react';
import { PARCEL_STYLES } from './mapStyles';

const legendStyle = {
  position: 'absolute',
  top: '10px',
  right: '10px',
  zIndex: 1000,
  background: 'rgba(255, 255, 255, 0.9)',
  padding: '10px',
  borderRadius: '5px',
  boxShadow: '0 1px 5px rgba(0,0,0,0.4)',
  lineHeight: '1.5',
  fontFamily: 'sans-serif',
  fontSize: '14px',
  color: '#333',
};

const itemStyle = {
  display: 'flex',
  alignItems: 'center',
  marginBottom: '8px',
};

const symbolStyle = {
  width: '30px',
  height: '20px',
  marginRight: '10px',
};

function hexToRgba(hex, opacity) {
  if (!hex) return '';
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? `rgba(${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${
        parseInt(result[3], 16)
      }, ${opacity})`
    : '';
}

const LegendItem = ({ style }) => {
  const itemSymbolStyle = {
    ...symbolStyle,
    backgroundColor: hexToRgba(style.fillColor, style.fillOpacity),
    border: `${style.weight}px ${style.dashArray ? 'dashed' : 'solid'} ${
      style.color
    }`,
  };

  return (
    <div style={itemStyle}>
      <div style={itemSymbolStyle}></div>
      <span>{style.label}</span>
    </div>
  );
};

export default function MapLegend() {
  return (
    <div style={legendStyle}>
      <strong style={{ marginBottom: '8px', display: 'block' }}>Legendă</strong>
      {Object.values(PARCEL_STYLES).map((style) => (
        <LegendItem key={style.label} style={style} />
      ))}
    </div>
  );
}