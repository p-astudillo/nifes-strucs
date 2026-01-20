/**
 * SnapIndicator - Visual indicator for active snap point in viewport.
 * Shows different symbols based on snap type.
 */

import { useMemo } from 'react'
import { useStore } from '../store/useStore'
import { Line, Ring } from '@react-three/drei'
import * as THREE from 'three'

// Colors for different snap types
const SNAP_COLORS: Record<string, string> = {
  endpoint: '#00ff00',
  midpoint: '#ffff00',
  node: '#00ffff',
  grid: '#ffffff',
  perpendicular: '#ff00ff',
  intersection: '#ff8800',
}

/**
 * Endpoint snap indicator - Square
 */
function EndpointIndicator({ position }: { position: THREE.Vector3 }) {
  const size = 0.2
  const points: [number, number, number][] = [
    [position.x - size, position.y, position.z - size],
    [position.x + size, position.y, position.z - size],
    [position.x + size, position.y, position.z + size],
    [position.x - size, position.y, position.z + size],
    [position.x - size, position.y, position.z - size],
  ]

  return (
    <Line
      points={points}
      color={SNAP_COLORS.endpoint}
      lineWidth={3}
    />
  )
}

/**
 * Midpoint snap indicator - Triangle
 */
function MidpointIndicator({ position }: { position: THREE.Vector3 }) {
  const size = 0.2
  const h = size * Math.sqrt(3) / 2
  const points: [number, number, number][] = [
    [position.x, position.y, position.z - h * 0.67],
    [position.x + size, position.y, position.z + h * 0.33],
    [position.x - size, position.y, position.z + h * 0.33],
    [position.x, position.y, position.z - h * 0.67],
  ]

  return (
    <Line
      points={points}
      color={SNAP_COLORS.midpoint}
      lineWidth={3}
    />
  )
}

/**
 * Node snap indicator - Circle
 */
function NodeIndicator({ position }: { position: THREE.Vector3 }) {
  return (
    <Ring
      args={[0.15, 0.2, 16]}
      position={[position.x, position.y + 0.01, position.z]}
      rotation={[-Math.PI / 2, 0, 0]}
    >
      <meshBasicMaterial color={SNAP_COLORS.node} />
    </Ring>
  )
}

/**
 * Grid snap indicator - Cross/Plus
 */
function GridIndicator({ position }: { position: THREE.Vector3 }) {
  const size = 0.15

  return (
    <group>
      <Line
        points={[
          [position.x - size, position.y, position.z],
          [position.x + size, position.y, position.z],
        ]}
        color={SNAP_COLORS.grid}
        lineWidth={2}
      />
      <Line
        points={[
          [position.x, position.y, position.z - size],
          [position.x, position.y, position.z + size],
        ]}
        color={SNAP_COLORS.grid}
        lineWidth={2}
      />
    </group>
  )
}

/**
 * Perpendicular snap indicator - Right angle symbol
 */
function PerpendicularIndicator({ position }: { position: THREE.Vector3 }) {
  const size = 0.15
  const points: [number, number, number][] = [
    [position.x - size, position.y, position.z],
    [position.x - size, position.y, position.z - size],
    [position.x, position.y, position.z - size],
  ]

  return (
    <Line
      points={points}
      color={SNAP_COLORS.perpendicular}
      lineWidth={3}
    />
  )
}

/**
 * Intersection snap indicator - X mark
 */
function IntersectionIndicator({ position }: { position: THREE.Vector3 }) {
  const size = 0.15

  return (
    <group>
      <Line
        points={[
          [position.x - size, position.y, position.z - size],
          [position.x + size, position.y, position.z + size],
        ]}
        color={SNAP_COLORS.intersection}
        lineWidth={3}
      />
      <Line
        points={[
          [position.x + size, position.y, position.z - size],
          [position.x - size, position.y, position.z + size],
        ]}
        color={SNAP_COLORS.intersection}
        lineWidth={3}
      />
    </group>
  )
}

/**
 * Main SnapIndicator component - renders appropriate indicator based on snap type.
 */
function SnapIndicator() {
  const activeSnapPoint = useStore((state) => state.activeSnapPoint)

  const indicator = useMemo(() => {
    if (!activeSnapPoint) return null

    const { type, position } = activeSnapPoint

    switch (type) {
      case 'endpoint':
        return <EndpointIndicator position={position} />
      case 'midpoint':
        return <MidpointIndicator position={position} />
      case 'node':
        return <NodeIndicator position={position} />
      case 'grid':
        return <GridIndicator position={position} />
      case 'perpendicular':
        return <PerpendicularIndicator position={position} />
      case 'intersection':
        return <IntersectionIndicator position={position} />
      default:
        return null
    }
  }, [activeSnapPoint])

  if (!activeSnapPoint) return null

  return <>{indicator}</>
}

export default SnapIndicator
