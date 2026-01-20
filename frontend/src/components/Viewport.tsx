import { useMemo, useEffect, useRef } from 'react'
import { Grid, OrbitControls, Line, Text } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import { useStore, DiagramType } from '../store/useStore'
import { FrameResult, RestraintType, DistributedLoadInput, LoadDirection, ShellResponse, FrameReleases } from '../api/client'
import { getSnapService, SnapService, NodeData, FrameData } from '../services/SnapService'
import SnapIndicator from './SnapIndicator'
import DrawingMode from './DrawingMode'
import * as THREE from 'three'

/**
 * Support icon component - renders different icons based on restraint type.
 */
function SupportIcon({ restraintType }: { restraintType: RestraintType }) {
  switch (restraintType) {
    case 'fixed':
      // Fixed/Empotrado: solid box
      return (
        <mesh position={[0, -0.2, 0]}>
          <boxGeometry args={[0.4, 0.15, 0.4]} />
          <meshStandardMaterial color="#00aa00" />
        </mesh>
      )
    case 'pinned':
      // Pinned/Articulado: triangle (cone with 3 segments)
      return (
        <mesh position={[0, -0.2, 0]}>
          <coneGeometry args={[0.2, 0.3, 3]} />
          <meshStandardMaterial color="#00aa00" />
        </mesh>
      )
    case 'roller_x':
      // Roller X: triangle with circles (simplified)
      return (
        <group position={[0, -0.2, 0]}>
          <mesh>
            <coneGeometry args={[0.15, 0.2, 3]} />
            <meshStandardMaterial color="#00aa00" />
          </mesh>
          <mesh position={[0, -0.15, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.06, 0.06, 0.3, 8]} />
            <meshStandardMaterial color="#008800" />
          </mesh>
        </group>
      )
    case 'roller_y':
      // Roller Y: triangle with circles rotated
      return (
        <group position={[0, -0.2, 0]}>
          <mesh>
            <coneGeometry args={[0.15, 0.2, 3]} />
            <meshStandardMaterial color="#00aa00" />
          </mesh>
          <mesh position={[0, -0.15, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.06, 0.06, 0.3, 8]} />
            <meshStandardMaterial color="#008800" />
          </mesh>
        </group>
      )
    case 'roller_z':
      // Roller Z: triangle with small sphere below
      return (
        <group position={[0, -0.2, 0]}>
          <mesh>
            <coneGeometry args={[0.15, 0.2, 3]} />
            <meshStandardMaterial color="#00aa00" />
          </mesh>
          <mesh position={[0, -0.15, 0]}>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshStandardMaterial color="#008800" />
          </mesh>
        </group>
      )
    case 'vertical_only':
      // Vertical only: single arrow up
      return (
        <group position={[0, -0.15, 0]}>
          <mesh>
            <cylinderGeometry args={[0.03, 0.03, 0.2, 8]} />
            <meshStandardMaterial color="#00aa00" />
          </mesh>
          <mesh position={[0, -0.15, 0]}>
            <coneGeometry args={[0.08, 0.1, 8]} />
            <meshStandardMaterial color="#00aa00" />
          </mesh>
        </group>
      )
    case 'custom':
      // Custom: diamond shape
      return (
        <mesh position={[0, -0.2, 0]}>
          <octahedronGeometry args={[0.12]} />
          <meshStandardMaterial color="#ffaa00" />
        </mesh>
      )
    default:
      return null
  }
}

/**
 * Node mesh component - renders a single node as a sphere.
 */
function NodeMesh({
  id,
  x,
  y,
  z,
  isSupported,
  isSelected,
  restraintType
}: {
  id: number
  x: number
  y: number
  z: number
  isSupported: boolean
  isSelected: boolean
  restraintType: RestraintType
}) {
  const selectNode = useStore((state) => state.selectNode)

  return (
    <group position={[x, z, -y]}>
      {/* Node sphere */}
      <mesh
        onClick={(e) => {
          e.stopPropagation()
          selectNode(id)
        }}
      >
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial
          color={isSelected ? '#ffff00' : isSupported ? '#00ff00' : '#4488ff'}
        />
      </mesh>

      {/* Support indicator based on type */}
      {isSupported && <SupportIcon restraintType={restraintType} />}

      {/* Node label */}
      <Text
        position={[0.3, 0.3, 0]}
        fontSize={0.2}
        color="#ffffff"
        anchorX="left"
      >
        {id}
      </Text>
    </group>
  )
}

/**
 * Release indicator component - renders a small circle at frame end to show release.
 */
function ReleaseIndicator({
  position,
  hasRelease,
}: {
  position: [number, number, number]
  hasRelease: boolean
}) {
  if (!hasRelease) return null

  return (
    <mesh position={position}>
      <sphereGeometry args={[0.08, 16, 16]} />
      <meshStandardMaterial color="#00ffff" transparent opacity={0.9} />
    </mesh>
  )
}

/**
 * Frame mesh component - renders a frame as a line or extruded profile.
 */
function FrameMesh({
  id,
  startPos,
  endPos,
  isSelected,
  showExtruded,
  releases,
}: {
  id: number
  startPos: [number, number, number]
  endPos: [number, number, number]
  isSelected: boolean
  showExtruded: boolean
  releases?: FrameReleases
}) {
  const selectFrame = useStore((state) => state.selectFrame)

  // Calculate frame direction and length
  const direction = useMemo(() => {
    return new THREE.Vector3(
      endPos[0] - startPos[0],
      endPos[1] - startPos[1],
      endPos[2] - startPos[2]
    )
  }, [startPos, endPos])

  const length = direction.length()
  const midPoint: [number, number, number] = [
    (startPos[0] + endPos[0]) / 2,
    (startPos[1] + endPos[1]) / 2,
    (startPos[2] + endPos[2]) / 2,
  ]

  // Create rotation to align cylinder with frame direction
  const quaternion = useMemo(() => {
    const up = new THREE.Vector3(0, 1, 0)
    const dir = direction.clone().normalize()
    return new THREE.Quaternion().setFromUnitVectors(up, dir)
  }, [direction])

  return (
    <group>
      {showExtruded ? (
        // Extruded profile (simplified as cylinder/box)
        <mesh
          position={midPoint}
          quaternion={quaternion}
          onClick={(e) => {
            e.stopPropagation()
            selectFrame(id)
          }}
        >
          <boxGeometry args={[0.1, length, 0.15]} />
          <meshStandardMaterial
            color={isSelected ? '#ffff00' : '#ff6600'}
            transparent
            opacity={0.85}
          />
        </mesh>
      ) : (
        // Line representation
        <Line
          points={[startPos, endPos]}
          color={isSelected ? '#ffff00' : '#ff6600'}
          lineWidth={isSelected ? 4 : 2}
          onClick={(e) => {
            e.stopPropagation()
            selectFrame(id)
          }}
        />
      )}
      {/* Frame label at midpoint */}
      <Text
        position={[midPoint[0] + 0.2, midPoint[1] + 0.2, midPoint[2]]}
        fontSize={0.15}
        color="#ff8844"
        anchorX="left"
      >
        F{id}
      </Text>
      {/* Release indicators */}
      <ReleaseIndicator
        position={startPos}
        hasRelease={Boolean(releases?.M2_i || releases?.M3_i || releases?.T_i)}
      />
      <ReleaseIndicator
        position={endPos}
        hasRelease={Boolean(releases?.M2_j || releases?.M3_j || releases?.T_j)}
      />
    </group>
  )
}

/**
 * Shell mesh component - renders a shell as a surface.
 * Converts structural coordinates to Three.js coordinates.
 */
function ShellMesh({
  shell,
  nodePositions,
  isSelected,
}: {
  shell: ShellResponse
  nodePositions: Map<number, [number, number, number]>
  isSelected: boolean
}) {
  const selectShell = useStore((state) => state.selectShell)

  // Get node positions for this shell
  const positions = shell.node_ids.map((id) => nodePositions.get(id)).filter((p): p is [number, number, number] => p !== undefined)

  if (positions.length < 3) return null

  // Create geometry based on number of nodes
  const geometry = useMemo(() => {
    const geom = new THREE.BufferGeometry()

    if (positions.length === 3) {
      // Triangle
      const vertices = new Float32Array([
        ...positions[0],
        ...positions[1],
        ...positions[2],
      ])
      geom.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
      geom.setIndex([0, 1, 2])
    } else {
      // Quad - split into two triangles
      const vertices = new Float32Array([
        ...positions[0],
        ...positions[1],
        ...positions[2],
        ...positions[3],
      ])
      geom.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
      geom.setIndex([0, 1, 2, 0, 2, 3])
    }

    geom.computeVertexNormals()
    return geom
  }, [positions])

  // Calculate centroid for label
  const centroid: [number, number, number] = useMemo(() => {
    const cx = positions.reduce((sum, p) => sum + p[0], 0) / positions.length
    const cy = positions.reduce((sum, p) => sum + p[1], 0) / positions.length
    const cz = positions.reduce((sum, p) => sum + p[2], 0) / positions.length
    return [cx, cy, cz]
  }, [positions])

  // Shell color based on type
  const shellColor = useMemo(() => {
    if (isSelected) return '#ffff00'
    switch (shell.shell_type) {
      case 'plate': return '#4488cc'
      case 'membrane': return '#88cc44'
      case 'shell':
      default: return '#6688aa'
    }
  }, [shell.shell_type, isSelected])

  return (
    <group>
      {/* Shell surface - front */}
      <mesh
        geometry={geometry}
        onClick={(e) => {
          e.stopPropagation()
          selectShell(shell.id)
        }}
      >
        <meshStandardMaterial
          color={shellColor}
          transparent
          opacity={0.7}
          side={THREE.FrontSide}
        />
      </mesh>
      {/* Shell surface - back */}
      <mesh geometry={geometry}>
        <meshStandardMaterial
          color={shellColor}
          transparent
          opacity={0.5}
          side={THREE.BackSide}
        />
      </mesh>
      {/* Shell edges */}
      <lineSegments>
        <edgesGeometry args={[geometry]} />
        <lineBasicMaterial color={isSelected ? '#ffff00' : '#ffffff'} linewidth={2} />
      </lineSegments>
      {/* Shell label */}
      <Text
        position={[centroid[0], centroid[1] + 0.2, centroid[2]]}
        fontSize={0.15}
        color="#88aacc"
        anchorX="center"
      >
        S{shell.id}
      </Text>
    </group>
  )
}

/**
 * Force diagram component - renders M/V/P diagrams along frames.
 */
function ForceDiagram({
  startPos,
  endPos,
  frameResult,
  diagramType,
  scale,
}: {
  frameId: number
  startPos: [number, number, number]
  endPos: [number, number, number]
  frameResult: FrameResult | undefined
  diagramType: DiagramType
  scale: number
}) {
  // Memoize all calculations
  const diagramData = useMemo(() => {
    if (!frameResult || diagramType === 'none') return null

    const forces = frameResult.forces
    if (!forces || forces.length === 0) return null

    // Get the relevant force values based on diagram type
    // For moment: negate to draw on tension side (engineering convention)
    const getForceValue = (f: { P: number; V2: number; V3: number; M2: number; M3: number }) => {
      switch (diagramType) {
        case 'axial': return f.P
        case 'shear': return Math.abs(f.V2) > Math.abs(f.V3) ? f.V2 : f.V3
        case 'moment':
          // Negate moment to draw on tension side (standard engineering convention)
          const m = Math.abs(f.M3) > Math.abs(f.M2) ? f.M3 : f.M2
          return -m
        default: return 0
      }
    }

    // Calculate frame direction and length
    const direction = new THREE.Vector3(
      endPos[0] - startPos[0],
      endPos[1] - startPos[1],
      endPos[2] - startPos[2]
    )
    const length = direction.length()
    if (length < 0.001) return null
    direction.normalize()

    // Find perpendicular vector for diagram offset
    // The diagram should be shown perpendicular to the frame axis
    // For structural engineering visualization, we want:
    // - For horizontal beams (along X or Z): show diagram in Y (vertical)
    // - For vertical columns (along Y): show diagram in Z (horizontal, towards viewer)
    let perp: THREE.Vector3

    // Use the global Y axis (vertical in Three.js) as the preferred diagram direction
    // unless the frame is nearly vertical
    const up = new THREE.Vector3(0, 1, 0)
    const isAlongY = Math.abs(direction.y) > 0.9

    if (isAlongY) {
      // Frame is vertical (along Y) - show diagram towards Z (viewer)
      perp = new THREE.Vector3(0, 0, 1)
    } else {
      // Frame is horizontal or inclined - show diagram vertically (Y direction)
      // Project UP onto the plane perpendicular to the frame
      // perp = up - (up · direction) * direction
      const dot = up.dot(direction)
      perp = new THREE.Vector3(
        up.x - dot * direction.x,
        up.y - dot * direction.y,
        up.z - dot * direction.z
      )
      if (perp.lengthSq() < 0.01) {
        perp.set(0, 0, 1)  // Fallback
      } else {
        perp.normalize()
      }
    }

    // Find max force value for auto-scaling
    const forceValues = forces.map(f => getForceValue(f))
    const maxForce = Math.max(...forceValues.map(Math.abs), 0.001)

    // Scale factor: make diagram visible relative to frame length
    // Base scale: diagram height = length * 0.3 for max force
    const autoScale = (length * 0.3) / maxForce
    const finalScale = scale * autoScale

    // Generate diagram points
    const diagramPoints: THREE.Vector3[] = []
    const basePoints: THREE.Vector3[] = []

    forces.forEach((f) => {
      const t = f.location
      const value = getForceValue(f) * finalScale

      const basePoint = new THREE.Vector3(
        startPos[0] + direction.x * length * t,
        startPos[1] + direction.y * length * t,
        startPos[2] + direction.z * length * t
      )
      basePoints.push(basePoint.clone())

      // Offset perpendicular to frame
      const offsetPoint = basePoint.clone().add(perp.clone().multiplyScalar(value))
      diagramPoints.push(offsetPoint)
    })

    // Create outline for the diagram
    const outlinePoints: [number, number, number][] = []

    // Start from first base point, go through diagram, back to last base point
    outlinePoints.push([basePoints[0].x, basePoints[0].y, basePoints[0].z])
    diagramPoints.forEach(p => {
      outlinePoints.push([p.x, p.y, p.z])
    })
    outlinePoints.push([basePoints[basePoints.length - 1].x, basePoints[basePoints.length - 1].y, basePoints[basePoints.length - 1].z])

    // Create triangles for filled area
    // Each segment between consecutive points creates a quad (2 triangles)
    const trianglePositions: number[] = []
    for (let i = 0; i < diagramPoints.length - 1; i++) {
      const b1 = basePoints[i]
      const b2 = basePoints[i + 1]
      const d1 = diagramPoints[i]
      const d2 = diagramPoints[i + 1]

      // Triangle 1: b1, d1, d2
      trianglePositions.push(b1.x, b1.y, b1.z)
      trianglePositions.push(d1.x, d1.y, d1.z)
      trianglePositions.push(d2.x, d2.y, d2.z)

      // Triangle 2: b1, d2, b2
      trianglePositions.push(b1.x, b1.y, b1.z)
      trianglePositions.push(d2.x, d2.y, d2.z)
      trianglePositions.push(b2.x, b2.y, b2.z)
    }

    return {
      outlinePoints,
      trianglePositions: new Float32Array(trianglePositions),
      hasTriangles: trianglePositions.length > 0,
    }
  }, [frameResult, diagramType, scale, startPos, endPos])

  if (!diagramData) return null

  // Get color based on diagram type
  const color = useMemo(() => {
    switch (diagramType) {
      case 'axial': return '#00ff00'  // Green for axial
      case 'shear': return '#ff00ff'  // Magenta for shear
      case 'moment': return '#00ffff' // Cyan for moment
      default: return '#ffffff'
    }
  }, [diagramType])

  return (
    <group>
      {/* Outline */}
      <Line
        points={diagramData.outlinePoints}
        color={color}
        lineWidth={2}
      />
      {/* Filled area */}
      {diagramData.hasTriangles && (
        <mesh>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              count={diagramData.trianglePositions.length / 3}
              array={diagramData.trianglePositions}
              itemSize={3}
            />
          </bufferGeometry>
          <meshBasicMaterial
            color={color}
            transparent
            opacity={0.3}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}
    </group>
  )
}

/**
 * Arrow component for load visualization.
 */
function LoadArrow({
  position,
  direction,
  length,
  color = '#ff0000',
}: {
  position: [number, number, number]
  direction: [number, number, number]
  length: number
  color?: string
}) {
  const arrowLength = Math.max(0.3, Math.min(length, 2)) // Clamp arrow length

  // Calculate rotation to align arrow with direction
  const quaternion = useMemo(() => {
    const dir = new THREE.Vector3(...direction).normalize()
    const up = new THREE.Vector3(0, 1, 0)
    return new THREE.Quaternion().setFromUnitVectors(up, dir)
  }, [direction])

  return (
    <group position={position} quaternion={quaternion}>
      {/* Arrow shaft */}
      <mesh position={[0, arrowLength / 2, 0]}>
        <cylinderGeometry args={[0.02, 0.02, arrowLength, 8]} />
        <meshStandardMaterial color={color} />
      </mesh>
      {/* Arrow head */}
      <mesh position={[0, arrowLength, 0]}>
        <coneGeometry args={[0.06, 0.15, 8]} />
        <meshStandardMaterial color={color} />
      </mesh>
    </group>
  )
}

/**
 * Reaction arrow component for visualizing support reactions.
 */
function ReactionArrow({
  position,
  force,
  moment,
  scale = 0.1,
}: {
  position: [number, number, number]
  force: { x: number; y: number; z: number }
  moment: { x: number; y: number; z: number }
  scale?: number
}) {
  // Only show arrows for significant forces/moments
  const forceThreshold = 0.01
  const momentThreshold = 0.01

  const arrows: JSX.Element[] = []

  // Force arrows (green for positive, red for negative in each direction)
  if (Math.abs(force.x) > forceThreshold) {
    const length = Math.min(Math.abs(force.x) * scale, 2)
    const dir = force.x > 0 ? 1 : -1
    arrows.push(
      <group key="fx" position={position}>
        <mesh position={[dir * length / 2, 0, 0]} rotation={[0, 0, dir > 0 ? -Math.PI / 2 : Math.PI / 2]}>
          <cylinderGeometry args={[0.03, 0.03, length, 8]} />
          <meshStandardMaterial color="#00ff00" />
        </mesh>
        <mesh position={[dir * length, 0, 0]} rotation={[0, 0, dir > 0 ? -Math.PI / 2 : Math.PI / 2]}>
          <coneGeometry args={[0.08, 0.2, 8]} />
          <meshStandardMaterial color="#00ff00" />
        </mesh>
      </group>
    )
  }

  if (Math.abs(force.y) > forceThreshold) {
    const length = Math.min(Math.abs(force.y) * scale, 2)
    const dir = force.y > 0 ? 1 : -1
    // Y structural = -Z Three.js
    arrows.push(
      <group key="fy" position={position}>
        <mesh position={[0, 0, -dir * length / 2]} rotation={[dir > 0 ? Math.PI / 2 : -Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.03, 0.03, length, 8]} />
          <meshStandardMaterial color="#00ff00" />
        </mesh>
        <mesh position={[0, 0, -dir * length]} rotation={[dir > 0 ? Math.PI / 2 : -Math.PI / 2, 0, 0]}>
          <coneGeometry args={[0.08, 0.2, 8]} />
          <meshStandardMaterial color="#00ff00" />
        </mesh>
      </group>
    )
  }

  if (Math.abs(force.z) > forceThreshold) {
    const length = Math.min(Math.abs(force.z) * scale, 2)
    const dir = force.z > 0 ? 1 : -1
    // Z structural = Y Three.js
    arrows.push(
      <group key="fz" position={position}>
        <mesh position={[0, dir * length / 2, 0]}>
          <cylinderGeometry args={[0.03, 0.03, length, 8]} />
          <meshStandardMaterial color="#00ff00" />
        </mesh>
        <mesh position={[0, dir * length, 0]} rotation={[dir > 0 ? 0 : Math.PI, 0, 0]}>
          <coneGeometry args={[0.08, 0.2, 8]} />
          <meshStandardMaterial color="#00ff00" />
        </mesh>
      </group>
    )
  }

  // Moment arrows (curved arrows - simplified as circles with arrows)
  if (Math.abs(moment.x) > momentThreshold) {
    const radius = Math.min(Math.abs(moment.x) * scale * 0.5, 0.5)
    arrows.push(
      <group key="mx" position={position}>
        <mesh rotation={[0, Math.PI / 2, 0]}>
          <torusGeometry args={[radius, 0.02, 8, 16, Math.PI * 1.5]} />
          <meshStandardMaterial color="#ff00ff" />
        </mesh>
      </group>
    )
  }

  if (Math.abs(moment.y) > momentThreshold) {
    const radius = Math.min(Math.abs(moment.y) * scale * 0.5, 0.5)
    arrows.push(
      <group key="my" position={position}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[radius, 0.02, 8, 16, Math.PI * 1.5]} />
          <meshStandardMaterial color="#ff00ff" />
        </mesh>
      </group>
    )
  }

  if (Math.abs(moment.z) > momentThreshold) {
    const radius = Math.min(Math.abs(moment.z) * scale * 0.5, 0.5)
    arrows.push(
      <group key="mz" position={position}>
        <mesh>
          <torusGeometry args={[radius, 0.02, 8, 16, Math.PI * 1.5]} />
          <meshStandardMaterial color="#ff00ff" />
        </mesh>
      </group>
    )
  }

  if (arrows.length === 0) return null

  return <group>{arrows}</group>
}

/**
 * Distributed load visualization component.
 * Renders arrows along the frame to show load distribution.
 */
function DistributedLoadViz({
  load,
  startPos,
  endPos,
}: {
  load: DistributedLoadInput
  startPos: [number, number, number]
  endPos: [number, number, number]
}) {
  const arrows = useMemo(() => {
    const result: { position: [number, number, number]; intensity: number }[] = []
    const numArrows = 5 // Number of arrows to display

    const startLoc = load.start_loc ?? 0
    const endLoc = load.end_loc ?? 1
    const wStart = load.w_start
    const wEnd = load.w_end ?? load.w_start

    for (let i = 0; i < numArrows; i++) {
      const t = startLoc + (endLoc - startLoc) * (i / (numArrows - 1))

      // Interpolate position along frame
      const x = startPos[0] + (endPos[0] - startPos[0]) * t
      const y = startPos[1] + (endPos[1] - startPos[1]) * t
      const z = startPos[2] + (endPos[2] - startPos[2]) * t

      // Interpolate intensity
      const intensity = wStart + (wEnd - wStart) * ((t - startLoc) / (endLoc - startLoc || 1))

      result.push({
        position: [x, y, z],
        intensity: Math.abs(intensity),
      })
    }

    return result
  }, [load, startPos, endPos])

  // Determine arrow direction based on load direction
  const getArrowDirection = (dir: LoadDirection | undefined): [number, number, number] => {
    switch (dir) {
      case 'Gravity':
      case undefined:
        return [0, -1, 0] // Down in Three.js
      case 'Global X':
        return [1, 0, 0]
      case 'Global Y':
        return [0, 0, -1] // Y structural = -Z Three.js
      case 'Global Z':
        return [0, 1, 0] // Z structural = Y Three.js
      default:
        return [0, -1, 0]
    }
  }

  const arrowDirection = getArrowDirection(load.direction)
  const maxIntensity = Math.max(...arrows.map((a) => a.intensity), 1)

  return (
    <group>
      {arrows.map((arrow, index) => (
        <LoadArrow
          key={index}
          position={arrow.position}
          direction={arrowDirection}
          length={0.3 + (arrow.intensity / maxIntensity) * 0.7}
          color="#ff4444"
        />
      ))}
      {/* Connecting line at arrow tips */}
      <Line
        points={arrows.map((a) => {
          const offset = 0.3 + (a.intensity / maxIntensity) * 0.7
          return [
            a.position[0] + arrowDirection[0] * offset,
            a.position[1] + arrowDirection[1] * offset,
            a.position[2] + arrowDirection[2] * offset,
          ] as [number, number, number]
        })}
        color="#ff4444"
        lineWidth={2}
      />
    </group>
  )
}

/**
 * SnapDetector - Handles mouse movement and snap detection.
 * Updates the snap service with current model data and detects snap points.
 * Also updates drawing point when in drawing mode.
 */
function SnapDetector() {
  const { camera, raycaster, pointer } = useThree()
  const nodes = useStore((state) => state.nodes)
  const frames = useStore((state) => state.frames)
  const snapSettings = useStore((state) => state.snapSettings)
  const setActiveSnapPoint = useStore((state) => state.setActiveSnapPoint)
  const drawingMode = useStore((state) => state.drawingMode)
  const updateDrawingPoint = useStore((state) => state.updateDrawingPoint)

  const snapService = useRef<SnapService>(getSnapService())
  const groundPlane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), [])
  const intersectionPoint = useMemo(() => new THREE.Vector3(), [])

  // Update snap service with current model data
  useEffect(() => {
    // Convert nodes to snap format (Three.js coordinates)
    const nodeData: NodeData[] = nodes.map((node) => ({
      id: node.id,
      position: new THREE.Vector3(node.x, node.z, -node.y),
    }))
    snapService.current.setNodes(nodeData)

    // Convert frames to snap format
    const frameData: FrameData[] = frames.map((frame) => {
      const nodeI = nodes.find((n) => n.id === frame.node_i_id)
      const nodeJ = nodes.find((n) => n.id === frame.node_j_id)
      if (!nodeI || !nodeJ) {
        return null
      }
      return {
        id: frame.id,
        startPos: new THREE.Vector3(nodeI.x, nodeI.z, -nodeI.y),
        endPos: new THREE.Vector3(nodeJ.x, nodeJ.z, -nodeJ.y),
      }
    }).filter((f): f is FrameData => f !== null)
    snapService.current.setFrames(frameData)
  }, [nodes, frames])

  // Update snap service settings
  useEffect(() => {
    snapService.current.updateSettings(snapSettings)
  }, [snapSettings])

  // Detect snap on each frame and update drawing point
  useFrame(() => {
    // Raycast to ground plane to get cursor position
    raycaster.setFromCamera(pointer, camera)
    const hit = raycaster.ray.intersectPlane(groundPlane, intersectionPoint)

    if (hit) {
      // Snap detection
      if (snapSettings.enabled) {
        const snapResult = snapService.current.findSnapPoint(intersectionPoint)
        setActiveSnapPoint(snapResult)
      } else {
        setActiveSnapPoint(null)
      }

      // Update drawing point when in drawing mode
      if (drawingMode.isActive && drawingMode.state === 'drawing') {
        // Convert from Three.js coords back to structural coords
        updateDrawingPoint({
          x: intersectionPoint.x,
          y: -intersectionPoint.z, // Three.js Z = -structural Y
          z: intersectionPoint.y,  // Three.js Y = structural Z
        })
      }
    } else {
      setActiveSnapPoint(null)
    }
  })

  return null
}

/**
 * DrawingClickHandler - Handles clicks for frame drawing.
 */
function DrawingClickHandler() {
  const { camera, raycaster, pointer } = useThree()
  const drawingMode = useStore((state) => state.drawingMode)
  const activeSnapPoint = useStore((state) => state.activeSnapPoint)
  const startDrawing = useStore((state) => state.startDrawing)
  const completeDrawing = useStore((state) => state.completeDrawing)

  const groundPlane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), [])

  const handleClick = () => {
    if (!drawingMode.isActive) return

    // Get click position
    raycaster.setFromCamera(pointer, camera)
    const intersectionPoint = new THREE.Vector3()
    const hit = raycaster.ray.intersectPlane(groundPlane, intersectionPoint)

    if (!hit) return

    // Use snap point if available
    let clickPoint: { x: number; y: number; z: number }
    let nodeId: number | undefined

    if (activeSnapPoint) {
      // Convert from Three.js to structural coords
      clickPoint = {
        x: activeSnapPoint.position.x,
        y: -activeSnapPoint.position.z,
        z: activeSnapPoint.position.y,
      }
      // If snapping to a node, use its ID
      if (activeSnapPoint.type === 'node' && activeSnapPoint.elementId) {
        nodeId = activeSnapPoint.elementId
      }
    } else {
      // Convert from Three.js to structural coords
      clickPoint = {
        x: intersectionPoint.x,
        y: -intersectionPoint.z,
        z: intersectionPoint.y,
      }
    }

    if (drawingMode.state === 'idle') {
      // First click - start drawing
      startDrawing(clickPoint, nodeId)
    } else if (drawingMode.state === 'drawing') {
      // Second click - complete drawing
      completeDrawing(clickPoint, nodeId)
    }
  }

  if (!drawingMode.isActive) return null

  return (
    <mesh
      position={[0, 0.001, 0]}
      rotation={[-Math.PI / 2, 0, 0]}
      onClick={handleClick}
    >
      <planeGeometry args={[1000, 1000]} />
      <meshBasicMaterial transparent opacity={0} />
    </mesh>
  )
}

/**
 * 3D Viewport component for structural model visualization.
 * Uses Three.js via React Three Fiber.
 */
function Viewport() {
  const nodes = useStore((state) => state.nodes)
  const frames = useStore((state) => state.frames)
  const shells = useStore((state) => state.shells)
  const selectedNodeId = useStore((state) => state.selectedNodeId)
  const selectedFrameId = useStore((state) => state.selectedFrameId)
  const selectedShellId = useStore((state) => state.selectedShellId)
  const selectNode = useStore((state) => state.selectNode)
  const selectFrame = useStore((state) => state.selectFrame)
  const selectShell = useStore((state) => state.selectShell)
  const viewOptions = useStore((state) => state.viewOptions)
  const gridSettings = useStore((state) => state.gridSettings)
  const analysisResults = useStore((state) => state.analysisResults)
  const distributedLoads = useStore((state) => state.distributedLoads)

  // Create a map of node positions for frame rendering
  const nodePositions = new Map<number, [number, number, number]>()
  nodes.forEach((node) => {
    // Convert from structural coords (X right, Y forward, Z up) to Three.js (X right, Y up, Z back)
    nodePositions.set(node.id, [node.x, node.z, -node.y])
  })

  // Create a map of frame results for diagram rendering
  const frameResultsMap = useMemo(() => {
    const map = new Map<number, FrameResult>()
    if (analysisResults?.frame_results) {
      analysisResults.frame_results.forEach((fr) => {
        map.set(fr.frame_id, fr)
      })
    }
    return map
  }, [analysisResults])

  // Clear selection when clicking on empty space
  const handlePointerMissed = () => {
    selectNode(null)
    selectFrame(null)
    selectShell(null)
  }

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} />

      {/* Camera Controls */}
      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        screenSpacePanning={false}
        maxPolarAngle={Math.PI / 2}
      />

      {/* Reference Grid */}
      {gridSettings.visible && (
        <Grid
          args={[gridSettings.size, gridSettings.size]}
          cellSize={gridSettings.spacing}
          cellThickness={0.5}
          cellColor="#404040"
          sectionSize={gridSettings.spacing * 5}
          sectionThickness={1}
          sectionColor="#606060"
          fadeDistance={50}
          fadeStrength={1}
          followCamera={false}
          infiniteGrid={true}
        />
      )}

      {/* Axes Helper */}
      <axesHelper args={[5]} />

      {/* Render Nodes */}
      {nodes.map((node) => (
        <NodeMesh
          key={node.id}
          id={node.id}
          x={node.x}
          y={node.y}
          z={node.z}
          isSupported={node.is_supported}
          isSelected={node.id === selectedNodeId}
          restraintType={node.restraint_type || 'free'}
        />
      ))}

      {/* Render Frames */}
      {frames.map((frame) => {
        const startPos = nodePositions.get(frame.node_i_id)
        const endPos = nodePositions.get(frame.node_j_id)
        if (!startPos || !endPos) return null

        return (
          <FrameMesh
            key={frame.id}
            id={frame.id}
            startPos={startPos}
            endPos={endPos}
            isSelected={frame.id === selectedFrameId}
            showExtruded={viewOptions.showExtrudedProfiles}
            releases={frame.releases}
          />
        )
      })}

      {/* Render Shells */}
      {shells.map((shell) => (
        <ShellMesh
          key={shell.id}
          shell={shell}
          nodePositions={nodePositions}
          isSelected={shell.id === selectedShellId}
        />
      ))}

      {/* Render Force Diagrams */}
      {viewOptions.diagramType !== 'none' && analysisResults?.success && frames.map((frame) => {
        const startPos = nodePositions.get(frame.node_i_id)
        const endPos = nodePositions.get(frame.node_j_id)
        if (!startPos || !endPos) return null

        return (
          <ForceDiagram
            key={`diagram-${frame.id}`}
            frameId={frame.id}
            startPos={startPos}
            endPos={endPos}
            frameResult={frameResultsMap.get(frame.id)}
            diagramType={viewOptions.diagramType}
            scale={viewOptions.diagramScale}
          />
        )
      })}

      {/* Distributed Loads Visualization */}
      {distributedLoads.map((load, index) => {
        const frame = frames.find((f) => f.id === load.frame_id)
        if (!frame) return null

        const startPos = nodePositions.get(frame.node_i_id)
        const endPos = nodePositions.get(frame.node_j_id)
        if (!startPos || !endPos) return null

        return (
          <DistributedLoadViz
            key={`load-${load.frame_id}-${index}`}
            load={load}
            startPos={startPos}
            endPos={endPos}
          />
        )
      })}

      {/* Reaction Arrows Visualization */}
      {viewOptions.showReactions && analysisResults?.success && analysisResults.reactions?.map((reaction) => {
        const pos = nodePositions.get(reaction.node_id)
        if (!pos) return null

        return (
          <ReactionArrow
            key={`reaction-${reaction.node_id}`}
            position={pos}
            force={{ x: reaction.Fx, y: reaction.Fy, z: reaction.Fz }}
            moment={{ x: reaction.Mx, y: reaction.My, z: reaction.Mz }}
            scale={0.1}
          />
        )
      })}

      {/* Click handler for deselection */}
      <mesh
        position={[0, -0.01, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        visible={false}
        onPointerMissed={handlePointerMissed}
      >
        <planeGeometry args={[1000, 1000]} />
      </mesh>

      {/* Snap detection and indicator */}
      <SnapDetector />
      <SnapIndicator />

      {/* Drawing mode */}
      <DrawingMode />
      <DrawingClickHandler />
    </>
  )
}

export default Viewport
