import React from 'react';

const legendStyle = {
  position: 'absolute',
  top: '10px',
  right: '10px',
  zIndex: 1000,
  background: 'rgba(255, 255, 255, 0.9)',
  padding: '10px',
  borderRadius: '5px',
  boxShadow: '0 1px 5px rgba(0,0,0,0.4)',
  fontFamily: 'sans-serif',
  fontSize: '14px',
  color: '#333',
};

const itemStyle = {
  display: 'flex',
  alignItems: 'center',
  marginBottom: '5px',
};

const colorBoxStyle = {
  width: '20px',
  height: '20px',
  marginRight: '10px',
  border: '1px solid #ccc',
};

// This assumes the analysisKey for soil moisture is 'soil-moisture'.
// This might need to be adjusted based on the `LAYERS` configuration.
const LEGEND_DATA = {
  'soil-moisture': {
    title: 'Moisture Level',
    items: [
      { color: '#7B3F00', label: 'Very Dry' },
      { color: '#AD4722', label: 'Dry' },
      { color: '#F7C948', label: 'Moderate' },
      { color: '#58A6FF', label: 'Moist' },
      { color: '#11529E', label: 'Wet' },
      { color: '#00008B', label: 'Very Wet' },
    ],
  },
};

export default function AnalysisLegend({ analysisKey }) {
  const legendData = LEGEND_DATA[analysisKey];
  if (!legendData) return null;

  const { title, items } = legendData;
  return (
    <div style={legendStyle}>
      <strong style={{ marginBottom: '8px', display: 'block' }}>{title}</strong>
      {items.map(({ color, label }) => (
        <div key={label} style={itemStyle}>
          <div style={{ ...colorBoxStyle, backgroundColor: color }}></div>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}