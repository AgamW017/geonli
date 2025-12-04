import { useState, useRef, useMemo, useEffect } from 'react';
import { TransformWrapper, TransformComponent, useTransformEffect } from 'react-zoom-pan-pinch';

function ImageViewer({ uploadedImage, overlays = [] }) {
  const imageRef = useRef(null);
  const transformComponentRef = useRef(null);
  const containerRef = useRef(null);
  
  // State for dynamic configuration
  const [initialConfig, setInitialConfig] = useState(null);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });

  const overlaysWithColors = useMemo(() => {
    const getRandomColor = () => {
      const colors = [
        '#ff0000', '#ff8800', '#00ffff', '#0088ff', '#ff00ff',
        '#ffff00', '#ff0088', '#8800ff',
      ];
      return colors[Math.floor(Math.random() * colors.length)];
    };

    return overlays.map(overlay => ({
      ...overlay,
      color: overlay.color || getRandomColor()
    }));
  }, [overlays]);

  const handleImageLoad = (e) => {
    const { naturalWidth, naturalHeight } = e.target;
    
    setImageDimensions({
      width: naturalWidth,
      height: naturalHeight
    });

    if (containerRef.current) {
      const { clientWidth, clientHeight } = containerRef.current;
      const scale = Math.min(
        clientWidth / naturalWidth,
        clientHeight / naturalHeight
      );

      const x = (clientWidth - naturalWidth * scale) / 2;
      const y = (clientHeight - naturalHeight * scale) / 2;

      if (!initialConfig) {
        setInitialConfig({ scale, x, y });
      }
    }
  };

  // Child component that listens to transform changes and renders overlays
  function OverlayLayer({ imageDimensions, colorizedOverlays, initialScale = 1 }) {
    const [scale, setScale] = useState(initialScale || 1);
    useTransformEffect(({ state }) => {
      if (state?.scale) setScale(state.scale);
    });

    useEffect(() => {
      if (initialScale && initialScale !== scale) {
        setScale(initialScale);
      }
    }, [initialScale]);

    if (imageDimensions.width === 0) return null;


    return (
      <svg
        className="absolute top-0 left-0"
        width={imageDimensions.width}
        height={imageDimensions.height}
        style={{ pointerEvents: 'none' }}
        viewBox={`0 0 ${imageDimensions.width} ${imageDimensions.height}`}
      >
        {colorizedOverlays.map(overlay => {
          const effectiveScale = Math.max(scale || 1, 0.1);
          const styles = {
            strokeWidth: 2 / effectiveScale,
            fontSize: 14 / effectiveScale,
            pinRadius: 3 / effectiveScale,
            pinHitRadius: 15 / effectiveScale,
            boxHitPadding: 5 / effectiveScale,
            textOffsetBox: 8 / effectiveScale,
            textOffsetPin: 18 / effectiveScale,
          };

          if (overlay.type === 'box') {
            const hasQuad = ['x1','y1','x2','y2','x3','y3','x4','y4'].every(k => overlay[k] !== undefined && overlay[k] !== null);
            if (hasQuad) {
              const pts = [
                [overlay.x1, overlay.y1],
                [overlay.x2, overlay.y2],
                [overlay.x3, overlay.y3],
                [overlay.x4, overlay.y4],
              ];
              const pointsAttr = pts.map(p => p.join(',')).join(' ');
              const avgX = (overlay.x1 + overlay.x2 + overlay.x3 + overlay.x4) / 4;
              const minY = Math.min(overlay.y1, overlay.y2, overlay.y3, overlay.y4);
              return (
                <g key={overlay.id}>
                  {/* Click hit area */}
                  <polygon
                    points={pointsAttr}
                    fill="transparent"
                    style={{ pointerEvents: 'auto', cursor: 'pointer' }}
                    onClick={(e) => { e.stopPropagation()}}
                  />
                  <polygon
                    points={pointsAttr}
                    fill="none"
                    stroke={overlay.color || 'var(--color-secondary)'}
                    strokeWidth={styles.strokeWidth}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  {overlay.label && (
                    <text
                      x={avgX}
                      y={minY - styles.textOffsetBox}
                      textAnchor="middle"
                      fill={overlay.color || 'var(--color-secondary)'}
                      fontSize={styles.fontSize}
                      fontWeight="600"
                    >
                      {overlay.label}
                    </text>
                  )}
                </g>
              );
            }
            return (
              <g key={overlay.id}>
                <rect
                  x={overlay.x - styles.boxHitPadding}
                  y={overlay.y - styles.boxHitPadding}
                  width={overlay.width + (styles.boxHitPadding * 2)}
                  height={overlay.height + (styles.boxHitPadding * 2)}
                  fill="transparent"
                  style={{ pointerEvents: 'auto', cursor: 'pointer' }}
                  onClick={(e) => { e.stopPropagation() }}
                />
                <rect
                  x={overlay.x}
                  y={overlay.y}
                  width={overlay.width}
                  height={overlay.height}
                  fill="none"
                  stroke={overlay.color || 'var(--color-secondary)'}
                  strokeWidth={styles.strokeWidth}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {overlay.label && (
                  <text
                    x={overlay.x + overlay.width / 2}
                    y={overlay.y - styles.textOffsetBox}
                    textAnchor="middle"
                    fill={overlay.color || 'var(--color-secondary)'}
                    fontSize={styles.fontSize}
                    fontWeight="600"
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
                  r={styles.pinHitRadius}
                  fill="transparent"
                  style={{ pointerEvents: 'auto', cursor: 'pointer' }}
                  onClick={(e) => { e.stopPropagation();}}
                />
                <circle
                  cx={overlay.x}
                  cy={overlay.y}
                  r={styles.pinRadius}
                  fill={overlay.color || 'var(--color-secondary)'}
                  style={{ pointerEvents: 'none' }}
                />
                {overlay.label && (
                  <text
                    x={overlay.x}
                    y={overlay.y - styles.textOffsetPin}
                    textAnchor="middle"
                    fill={overlay.color || 'var(--color-secondary)'}
                    fontSize={styles.fontSize}
                    fontWeight="600"
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
    );
  }

  return (
    <div className="flex-1 flex flex-col p-4 sm:p-6 overflow-hidden relative h-full min-w-0 w-0">
      <div 
        ref={containerRef} 
        className="relative flex-1 w-full h-full rounded-lg overflow-hidden bg-light-bg dark:bg-dark-bg"
      >
        <TransformWrapper
          ref={transformComponentRef}
          key={initialConfig ? "loaded" : "loading"} 
          initialScale={initialConfig ? initialConfig.scale : 1}
          initialPositionX={initialConfig ? initialConfig.x : 0}
          initialPositionY={initialConfig ? initialConfig.y : 0}
          minScale={initialConfig ? initialConfig.scale * 0.75 : 0.75}
          velocityAnimation={{disabled: false, animationTime: 250, easing: "easeOutQuad"}}
          alignmentAnimation={{ disabled: false, animationTime: 250, easing: "easeOutQuad" }}
          zoomAnimation={{ disabled: false, animationTime: 200, easing: "easeOutQuad" }}
          maxScale={20}
          centerOnInit={true} 
          wheel={{ step: 0.1 }}
        >
          {() => (
            <TransformComponent
              wrapperStyle={{ width: "100%", height: "100%", overflow: "hidden" }}
            >
              <div 
                style={{ 
                  position: "relative", 
                  width: "fit-content", 
                  height: "fit-content",
                  opacity: initialConfig ? 1 : 0,
                  transition: 'opacity 0.2s ease-in'
                }}
              >
                <img
                  ref={imageRef}
                  src={uploadedImage || 'https://placehold.co/1200x800/27272a/404040?text=NO+IMAGE'}
                  alt="Satellite view"
                  className="select-none block max-w-none"
                  draggable="false"
                  onLoad={handleImageLoad}
                />

                <OverlayLayer 
                  imageDimensions={imageDimensions} 
                  overlays={overlays} 
                  colorizedOverlays={overlaysWithColors}
                  initialScale={initialConfig?.scale || 1}
                />
              </div>
            </TransformComponent>
          )}
        </TransformWrapper>
      </div>
    </div>
  );
}

export default ImageViewer;