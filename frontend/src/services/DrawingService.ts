/**
 * DrawingService - Handles frame drawing logic in the viewport.
 * Manages drawing state, preview lines, and node/frame creation.
 */

import * as THREE from 'three'

// Drawing mode states
export type DrawingState = 'idle' | 'drawing'

// Drawing service configuration
export interface DrawingConfig {
  continuousMode: boolean // Continue drawing after creating a frame
  autoCreateNodes: boolean // Create nodes automatically if they don't exist
  defaultMaterial: string
  defaultSection: string
}

// Default configuration
export const DEFAULT_DRAWING_CONFIG: DrawingConfig = {
  continuousMode: true,
  autoCreateNodes: true,
  defaultMaterial: 'Steel_A36',
  defaultSection: 'W14X22',
}

// Drawing session data
export interface DrawingSession {
  state: DrawingState
  startPoint: THREE.Vector3 | null
  startNodeId: number | null // If clicking on existing node
  currentPoint: THREE.Vector3 | null // Current mouse/snap position
  config: DrawingConfig
}

// Initial session state
export const INITIAL_DRAWING_SESSION: DrawingSession = {
  state: 'idle',
  startPoint: null,
  startNodeId: null,
  currentPoint: null,
  config: DEFAULT_DRAWING_CONFIG,
}

/**
 * DrawingService class - manages drawing operations.
 */
export class DrawingService {
  private session: DrawingSession
  private onSessionChange?: (session: DrawingSession) => void

  constructor(onChange?: (session: DrawingSession) => void) {
    this.session = { ...INITIAL_DRAWING_SESSION }
    this.onSessionChange = onChange
  }

  /**
   * Get current session state.
   */
  getSession(): DrawingSession {
    return { ...this.session }
  }

  /**
   * Check if currently in drawing mode.
   */
  isDrawing(): boolean {
    return this.session.state === 'drawing'
  }

  /**
   * Start drawing mode - first click sets start point.
   */
  startDrawing(point: THREE.Vector3, nodeId?: number): void {
    this.session = {
      ...this.session,
      state: 'drawing',
      startPoint: point.clone(),
      startNodeId: nodeId ?? null,
      currentPoint: point.clone(),
    }
    this.notifyChange()
  }

  /**
   * Update current point (mouse move).
   */
  updateCurrentPoint(point: THREE.Vector3): void {
    if (this.session.state !== 'drawing') return

    this.session = {
      ...this.session,
      currentPoint: point.clone(),
    }
    this.notifyChange()
  }

  /**
   * Complete drawing - second click sets end point.
   * Returns start and end points for frame creation.
   */
  completeDrawing(
    endPoint: THREE.Vector3,
    endNodeId?: number
  ): {
    startPoint: THREE.Vector3
    endPoint: THREE.Vector3
    startNodeId: number | null
    endNodeId: number | null
  } | null {
    if (this.session.state !== 'drawing' || !this.session.startPoint) {
      return null
    }

    const result = {
      startPoint: this.session.startPoint.clone(),
      endPoint: endPoint.clone(),
      startNodeId: this.session.startNodeId,
      endNodeId: endNodeId ?? null,
    }

    // If continuous mode, end point becomes new start point
    if (this.session.config.continuousMode) {
      this.session = {
        ...this.session,
        startPoint: endPoint.clone(),
        startNodeId: endNodeId ?? null,
        currentPoint: endPoint.clone(),
      }
    } else {
      // Reset to idle
      this.session = {
        ...this.session,
        state: 'idle',
        startPoint: null,
        startNodeId: null,
        currentPoint: null,
      }
    }

    this.notifyChange()
    return result
  }

  /**
   * Cancel current drawing operation.
   */
  cancel(): void {
    this.session = {
      ...this.session,
      state: 'idle',
      startPoint: null,
      startNodeId: null,
      currentPoint: null,
    }
    this.notifyChange()
  }

  /**
   * Update configuration.
   */
  setConfig(config: Partial<DrawingConfig>): void {
    this.session = {
      ...this.session,
      config: { ...this.session.config, ...config },
    }
    this.notifyChange()
  }

  /**
   * Notify listener of session change.
   */
  private notifyChange(): void {
    if (this.onSessionChange) {
      this.onSessionChange(this.getSession())
    }
  }
}

// Singleton instance
let drawingServiceInstance: DrawingService | null = null

export function getDrawingService(
  onChange?: (session: DrawingSession) => void
): DrawingService {
  if (!drawingServiceInstance) {
    drawingServiceInstance = new DrawingService(onChange)
  }
  return drawingServiceInstance
}

export function resetDrawingService(): void {
  drawingServiceInstance = null
}
