/**
 * DrawingMode - Visual components for frame drawing mode.
 * Shows preview line from start point to current cursor position.
 */

import { useMemo } from 'react'
import { Line, Sphere } from '@react-three/drei'
import { useStore } from '../store/useStore'

/**
 * Preview line component - shows the line being drawn.
 */
function PreviewLine() {
  const drawingMode = useStore((state) => state.drawingMode)
  const activeSnapPoint = useStore((state) => state.activeSnapPoint)

  const { startPoint, currentPoint, state } = drawingMode

  // Determine end point: use snap point if available, otherwise current point
  const endPosition = useMemo(() => {
    if (activeSnapPoint) {
      return {
        x: activeSnapPoint.position.x,
        y: activeSnapPoint.position.y,
        z: activeSnapPoint.position.z,
      }
    }
    return currentPoint
  }, [activeSnapPoint, currentPoint])

  if (state !== 'drawing' || !startPoint || !endPosition) {
    return null
  }

  // Convert from structural coords (X, Y, Z) to Three.js (X, Z, -Y)
  const start: [number, number, number] = [startPoint.x, startPoint.z, -startPoint.y]
  const end: [number, number, number] = [endPosition.x, endPosition.y, endPosition.z]

  return (
    <group>
      {/* Start point marker */}
      <Sphere args={[0.1, 16, 16]} position={start}>
        <meshStandardMaterial color="#00ff88" />
      </Sphere>

      {/* Preview line - dashed style */}
      <Line
        points={[start, end]}
        color="#00ff88"
        lineWidth={2}
        dashed
        dashSize={0.2}
        gapSize={0.1}
      />

      {/* End point marker */}
      <Sphere args={[0.08, 16, 16]} position={end}>
        <meshStandardMaterial color="#88ff00" />
      </Sphere>
    </group>
  )
}

/**
 * Drawing mode indicator - shows when drawing mode is active.
 */
function DrawingModeIndicator() {
  const drawingMode = useStore((state) => state.drawingMode)

  if (!drawingMode.isActive) return null

  // Show a subtle visual indicator that drawing mode is active
  return null // The main indicator is in the UI, not 3D
}

/**
 * Main DrawingMode component - combines all drawing visuals.
 */
function DrawingMode() {
  const drawingMode = useStore((state) => state.drawingMode)

  if (!drawingMode.isActive) return null

  return (
    <>
      <PreviewLine />
      <DrawingModeIndicator />
    </>
  )
}

export default DrawingMode
