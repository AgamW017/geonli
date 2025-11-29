import { useState, useRef, useEffect, useMemo } from 'react';

function ImageViewer({ uploadedImage, overlays = [] }) {
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const [minScale, setMinScale] = useState(1);
  const imageContainerRef = useRef(null);
  const imageRef = useRef(null);
  
  const overlaysWithColors = useMemo(() => {
    const getRandomColor = () => {
      const colors = [
        '#ff0000',
        '#ff8800',
        '#00ffff',
        '#0088ff',
        '#ff00ff',
        '#ffff00',
        '#ff0088',
        '#8800ff',
      ];
      return colors[Math.floor(Math.random() * colors.length)];
    };

    return overlays.map(overlay => ({
      ...overlay,
      color: overlay.color || getRandomColor()
    }));
  }, [overlays]);

  const constrainPan = (x, y, scale) => {
    if (!imageRef.current || !imageContainerRef.current) return { x, y };
    
    const img = imageRef.current;
    const container = imageContainerRef.current;
    const imgWidth = img.naturalWidth * scale;
    const imgHeight = img.naturalHeight * scale;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    let constrainedX = x;
    let constrainedY = y;
    if (imgWidth > containerWidth) {
      const maxX = 0;
      const minX = -(imgWidth - containerWidth);
      constrainedX = Math.max(Math.min(x, maxX), minX);
    } else {
      constrainedX = (containerWidth - imgWidth) / 2;
    }

    if (imgHeight > containerHeight) {
      const maxY = 0;
      const minY = -(imgHeight - containerHeight);
      constrainedY = Math.max(Math.min(y, maxY), minY);
    } else {
      constrainedY = (containerHeight - imgHeight) / 2;
    }

    return { x: constrainedX, y: constrainedY };
  };

  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsPanning(true);
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  const handleMouseLeave = () => {
    setIsPanning(false);
  };

  const handleMouseMove = (e) => {
    if (!isPanning) return;
    const newX = transform.x + e.movementX;
    const newY = transform.y + e.movementY;
    const constrained = constrainPan(newX, newY, transform.scale);
    setTransform(t => ({
      ...t,
      x: constrained.x,
      y: constrained.y,
    }));
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const container = imageContainerRef.current;
    if (!container) return;
    
    const rect = container.getBoundingClientRect();
    const scaleAmount = -e.deltaY * 0.001;
    const newScale = Math.min(Math.max(minScale, transform.scale + scaleAmount), 10);
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Calculate new origin
    let newX = transform.x + (mouseX - transform.x) * (1 - newScale / transform.scale);
    let newY = transform.y + (mouseY - transform.y) * (1 - newScale / transform.scale);

    // Constrain pan after zoom
    const constrained = constrainPan(newX, newY, newScale);

    setTransform({
      scale: newScale,
      x: constrained.x,
      y: constrained.y,
    });
  };

  useEffect(() => {
    const container = imageContainerRef.current;
    if (!container) return;

    const wheelHandler = (ev) => {
      // Prevent page scroll
      ev.preventDefault();
      handleWheel(ev);
    };

    container.addEventListener('wheel', wheelHandler, { passive: false });
    return () => container.removeEventListener('wheel', wheelHandler);
  }, [imageContainerRef, handleWheel]);

  // Center image on load and handle container resize
  useEffect(() => {
    const centerImage = () => {
      if (uploadedImage && imageRef.current && imageContainerRef.current) {
        const img = imageRef.current;
        const container = imageContainerRef.current;
        
        const imgWidth = img.naturalWidth;
        const imgHeight = img.naturalHeight;
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;

        if (imgWidth === 0 || imgHeight === 0) return;

        const scaleX = containerWidth / imgWidth;
        const scaleY = containerHeight / imgHeight;
        if (scaleX>1 && scaleY>1){const fitScale = Math.min(scaleX, scaleY);
        
        // Store fit scale as minimum zoom level
        setMinScale(fitScale);

        // Center the image at fit scale
        const x = (containerWidth - imgWidth * fitScale) / 2;
        const y = (containerHeight - imgHeight * fitScale) / 2;

        setTransform({ x, y, scale: fitScale });}
        else{
          setMinScale(1);
          setTransform({ x: 0, y: 0, scale: 1 });
        }
        // idk why but this way its working
      }
    };

    if (imageRef.current?.complete) {
        centerImage();
    } else if (imageRef.current) {
        imageRef.current.onload = centerImage;
    }

  }, [uploadedImage]);

  return (
    <div className="flex-1 flex flex-col p-4 sm:p-6 overflow-hidden relative">
      
      {/* Image Viewer */}
      <div 
        ref={imageContainerRef}
        className="relative flex-1 w-full h-full rounded-lg overflow-hidden cursor-grab bg-light-bg dark:bg-dark-bg"
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onMouseMove={handleMouseMove}
        style={{ touchAction: 'none' }}
      >
        {isPanning && <div className="absolute inset-0 cursor-grabbing z-30"></div>}
        
        <div
          className="absolute"
          style={{
            transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
            transformOrigin: '0 0',
            transition: isPanning ? 'none' : 'transform 0.1s ease-out',
          }}
        >
          {/* Image */}
          <img
            ref={imageRef}
            src={uploadedImage || 'https://placehold.co/1200x800/27272a/404040?text=NO+IMAGE'}
            alt="Satellite view"
            className="select-none"
            draggable="false"
          />
          
          {/* SVG Overlay */}
          <svg
            className="absolute top-0 left-0"
            width={imageRef.current?.naturalWidth || 1200}
            height={imageRef.current?.naturalHeight || 800}
            style={{
              pointerEvents: 'none',
            }}
          >
            {overlaysWithColors.map(overlay => {
              if (overlay.type === 'box') {
                return (
                  <g key={overlay.id}>
                    <rect
                      x={overlay.x - 5 / transform.scale}
                      y={overlay.y - 5 / transform.scale}
                      width={overlay.width + 10 / transform.scale}
                      height={overlay.height + 10 / transform.scale}
                      fill="transparent"
                      style={{ pointerEvents: 'auto', cursor: 'pointer' }}
                      onClick={(e) => { e.stopPropagation(); console.log(`Clicked box ${overlay.id}`)}}
                    />
                    {/* Visible box */}
                    <rect
                      x={overlay.x}
                      y={overlay.y}
                      width={overlay.width}
                      height={overlay.height}
                      fill="none"
                      stroke={overlay.color || '#ef4444'}
                      strokeWidth={2 / transform.scale}
                      style={{ pointerEvents: 'none' }}
                    />
                    {overlay.label && (
                      <text
                        x={overlay.x + overlay.width / 2}
                        y={overlay.y - 8 / transform.scale}
                        textAnchor="middle"
                        fill={overlay.color || '#ef4444'}
                        fontSize={14 / transform.scale}
                        fontWeight="600"
                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                      >
                        {overlay.label}
                      </text>
                    )}
                  </g>
                );
              }
              if (overlay.type === 'pin') {
                return (
                  <g key={overlay.id}>
                    <circle
                      cx={overlay.x}
                      cy={overlay.y}
                      r={15 / transform.scale}
                      fill="transparent"
                      style={{ pointerEvents: 'auto', cursor: 'pointer' }}
                      onClick={(e) => { e.stopPropagation(); console.log(`Clicked pin ${overlay.id}`)}}
                    />
                    {/* Visible pin */}
                    <circle
                      cx={overlay.x}
                      cy={overlay.y}
                      r={3 / transform.scale}
                      fill={overlay.color || '#3b82f6'}
                      style={{ pointerEvents: 'none' }}
                    />
                    {overlay.label && (
                      <text
                        x={overlay.x}
                        y={overlay.y - 18 / transform.scale}
                        textAnchor="middle"
                        fill={overlay.color || '#3b82f6'}
                        fontSize={14 / transform.scale}
                        fontWeight="600"
                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                      >
                        {overlay.label}
                      </text>
                    )}
                  </g>
                );
              }
              return null;
            })}
          </svg>
        </div>
      </div>
    </div>
  );
}

export default ImageViewer;
