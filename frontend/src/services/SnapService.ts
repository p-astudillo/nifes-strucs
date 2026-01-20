/**
 * SnapService - Object snap system for precise drawing.
 * Provides snap detection for endpoints, midpoints, nodes, grid, etc.
 */

import * as THREE from 'three'

// Snap types available
export type SnapType =
  | 'endpoint'
  | 'midpoint'
  | 'node'
  | 'grid'
  | 'perpendicular'
  | 'intersection'

// Snap type labels for UI
export const SNAP_TYPE_LABELS: Record<SnapType, string> = {
  endpoint: 'Extremo',
  midpoint: 'Punto Medio',
  node: 'Nodo',
  grid: 'Grilla',
  perpendicular: 'Perpendicular',
  intersection: 'Interseccion',
}

// Snap type icons/symbols
export const SNAP_TYPE_SYMBOLS: Record<SnapType, string> = {
  endpoint: '□',
  midpoint: '△',
  node: '○',
  grid: '+',
  perpendicular: '⊥',
  intersection: '×',
}

// Snap result with type and position
export interface SnapResult {
  type: SnapType
  position: THREE.Vector3
  elementId?: number // Node or frame ID if applicable
  distance: number // Distance from cursor
}

// Snap settings configuration
export interface SnapSettings {
  enabled: boolean
  activeSnaps: Record<SnapType, boolean>
  threshold: number // Snap distance threshold in world units
  gridSpacing: number // Grid spacing for grid snap
}

// Default snap settings
export const DEFAULT_SNAP_SETTINGS: SnapSettings = {
  enabled: true,
  activeSnaps: {
    endpoint: true,
    midpoint: true,
    node: true,
    grid: true,
    perpendicular: false,
    intersection: false,
  },
  threshold: 0.5,
  gridSpacing: 1,
}

// Node data for snap detection
export interface NodeData {
  id: number
  position: THREE.Vector3
}

// Frame data for snap detection
export interface FrameData {
  id: number
  startPos: THREE.Vector3
  endPos: THREE.Vector3
}

/**
 * SnapService class - handles all snap detection logic.
 */
export class SnapService {
  private settings: SnapSettings
  private nodes: NodeData[] = []
  private frames: FrameData[] = []

  constructor(settings: SnapSettings = DEFAULT_SNAP_SETTINGS) {
    this.settings = settings
  }

  /**
   * Update settings.
   */
  updateSettings(settings: Partial<SnapSettings>): void {
    this.settings = { ...this.settings, ...settings }
  }

  /**
   * Update nodes for snap detection.
   */
  setNodes(nodes: NodeData[]): void {
    this.nodes = nodes
  }

  /**
   * Update frames for snap detection.
   */
  setFrames(frames: FrameData[]): void {
    this.frames = frames
  }

  /**
   * Check if snap is enabled globally.
   */
  isEnabled(): boolean {
    return this.settings.enabled
  }

  /**
   * Toggle snap enabled state.
   */
  toggle(): boolean {
    this.settings.enabled = !this.settings.enabled
    return this.settings.enabled
  }

  /**
   * Find the best snap point near a cursor position.
   * Returns null if no snap point is within threshold.
   */
  findSnapPoint(cursorPosition: THREE.Vector3): SnapResult | null {
    if (!this.settings.enabled) return null

    const candidates: SnapResult[] = []

    // Check each enabled snap type
    if (this.settings.activeSnaps.node) {
      candidates.push(...this.findNodeSnaps(cursorPosition))
    }

    if (this.settings.activeSnaps.endpoint) {
      candidates.push(...this.findEndpointSnaps(cursorPosition))
    }

    if (this.settings.activeSnaps.midpoint) {
      candidates.push(...this.findMidpointSnaps(cursorPosition))
    }

    if (this.settings.activeSnaps.grid) {
      const gridSnap = this.findGridSnap(cursorPosition)
      if (gridSnap) candidates.push(gridSnap)
    }

    if (this.settings.activeSnaps.perpendicular) {
      candidates.push(...this.findPerpendicularSnaps(cursorPosition))
    }

    if (this.settings.activeSnaps.intersection) {
      candidates.push(...this.findIntersectionSnaps(cursorPosition))
    }

    // Filter by threshold and find closest
    const validSnaps = candidates.filter(
      (snap) => snap.distance <= this.settings.threshold
    )

    if (validSnaps.length === 0) return null

    // Sort by distance and return closest
    validSnaps.sort((a, b) => a.distance - b.distance)
    return validSnaps[0]
  }

  /**
   * Find snaps to existing nodes.
   */
  private findNodeSnaps(cursor: THREE.Vector3): SnapResult[] {
    return this.nodes.map((node) => ({
      type: 'node' as SnapType,
      position: node.position.clone(),
      elementId: node.id,
      distance: cursor.distanceTo(node.position),
    }))
  }

  /**
   * Find snaps to frame endpoints.
   */
  private findEndpointSnaps(cursor: THREE.Vector3): SnapResult[] {
    const results: SnapResult[] = []

    this.frames.forEach((frame) => {
      results.push({
        type: 'endpoint',
        position: frame.startPos.clone(),
        elementId: frame.id,
        distance: cursor.distanceTo(frame.startPos),
      })
      results.push({
        type: 'endpoint',
        position: frame.endPos.clone(),
        elementId: frame.id,
        distance: cursor.distanceTo(frame.endPos),
      })
    })

    return results
  }

  /**
   * Find snaps to frame midpoints.
   */
  private findMidpointSnaps(cursor: THREE.Vector3): SnapResult[] {
    return this.frames.map((frame) => {
      const midpoint = new THREE.Vector3()
        .addVectors(frame.startPos, frame.endPos)
        .multiplyScalar(0.5)

      return {
        type: 'midpoint' as SnapType,
        position: midpoint,
        elementId: frame.id,
        distance: cursor.distanceTo(midpoint),
      }
    })
  }

  /**
   * Find snap to grid.
   */
  private findGridSnap(cursor: THREE.Vector3): SnapResult | null {
    const spacing = this.settings.gridSpacing

    // Snap to nearest grid intersection
    const snappedX = Math.round(cursor.x / spacing) * spacing
    const snappedZ = Math.round(cursor.z / spacing) * spacing
    const snappedY = cursor.y // Keep Y (height) as is

    const snapPosition = new THREE.Vector3(snappedX, snappedY, snappedZ)

    return {
      type: 'grid',
      position: snapPosition,
      distance: cursor.distanceTo(snapPosition),
    }
  }

  /**
   * Find perpendicular snaps from cursor to frames.
   */
  private findPerpendicularSnaps(cursor: THREE.Vector3): SnapResult[] {
    const results: SnapResult[] = []

    this.frames.forEach((frame) => {
      // Find closest point on line segment to cursor
      const lineDir = new THREE.Vector3().subVectors(frame.endPos, frame.startPos)
      const lineLength = lineDir.length()
      lineDir.normalize()

      const toCursor = new THREE.Vector3().subVectors(cursor, frame.startPos)
      let t = toCursor.dot(lineDir)

      // Clamp to line segment
      t = Math.max(0, Math.min(lineLength, t))

      const closestPoint = new THREE.Vector3()
        .copy(frame.startPos)
        .add(lineDir.multiplyScalar(t))

      // Only add if not at endpoint (those are covered by endpoint snap)
      if (t > 0.01 * lineLength && t < 0.99 * lineLength) {
        results.push({
          type: 'perpendicular',
          position: closestPoint,
          elementId: frame.id,
          distance: cursor.distanceTo(closestPoint),
        })
      }
    })

    return results
  }

  /**
   * Find intersection snaps between frames.
   */
  private findIntersectionSnaps(cursor: THREE.Vector3): SnapResult[] {
    const results: SnapResult[] = []

    // Check all pairs of frames for intersections
    for (let i = 0; i < this.frames.length; i++) {
      for (let j = i + 1; j < this.frames.length; j++) {
        const intersection = this.findLineIntersection(
          this.frames[i],
          this.frames[j]
        )
        if (intersection) {
          results.push({
            type: 'intersection',
            position: intersection,
            distance: cursor.distanceTo(intersection),
          })
        }
      }
    }

    return results
  }

  /**
   * Find intersection point between two line segments (in 2D, XZ plane).
   */
  private findLineIntersection(
    frame1: FrameData,
    frame2: FrameData
  ): THREE.Vector3 | null {
    // Project to XZ plane for 2D intersection
    const x1 = frame1.startPos.x
    const z1 = frame1.startPos.z
    const x2 = frame1.endPos.x
    const z2 = frame1.endPos.z

    const x3 = frame2.startPos.x
    const z3 = frame2.startPos.z
    const x4 = frame2.endPos.x
    const z4 = frame2.endPos.z

    const denom = (x1 - x2) * (z3 - z4) - (z1 - z2) * (x3 - x4)
    if (Math.abs(denom) < 0.0001) return null // Parallel lines

    const t = ((x1 - x3) * (z3 - z4) - (z1 - z3) * (x3 - x4)) / denom
    const u = -((x1 - x2) * (z1 - z3) - (z1 - z2) * (x1 - x3)) / denom

    // Check if intersection is within both line segments
    if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
      const x = x1 + t * (x2 - x1)
      const z = z1 + t * (z2 - z1)

      // Interpolate Y (height) from frame1
      const y = frame1.startPos.y + t * (frame1.endPos.y - frame1.startPos.y)

      return new THREE.Vector3(x, y, z)
    }

    return null
  }
}

// Singleton instance
let snapServiceInstance: SnapService | null = null

export function getSnapService(): SnapService {
  if (!snapServiceInstance) {
    snapServiceInstance = new SnapService()
  }
  return snapServiceInstance
}

export function resetSnapService(): void {
  snapServiceInstance = null
}
