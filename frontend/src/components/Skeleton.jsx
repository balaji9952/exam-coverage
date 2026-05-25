import React from 'react';

const Skeleton = ({ className, variant = 'rect', width, height, style = {} }) => {
  const combinedStyle = {
    width: width || '100%',
    height: height || (variant === 'text' ? '1rem' : '100%'),
    display: 'inline-block',
    ...style
  };

  return (
    <div 
      className={`skeleton-shimmer skeleton-${variant} ${className || ''}`}
      style={combinedStyle}
    />
  );
};

export default Skeleton;
