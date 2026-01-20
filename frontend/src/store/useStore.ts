import { create } from 'zustand'
import { api, NodeResponse, FrameResponse, ShellResponse, ShellType, ProjectResponse, AnalysisResponse, RestraintType, DistributedLoadInput, LoadDirection, MassResponse, FrameReleases, GroupResponse } from '../api/client'
import { SnapType, SnapResult, DEFAULT_SNAP_SETTINGS } from '../services/SnapService'
import { DrawingState, DrawingConfig, DEFAULT_DRAWING_CONFIG } from '../services/DrawingService'

// Nodal load for analysis
export interface NodalLoadInput {
  node_id: number
  Fx: number
  Fy: number
  Fz: number
  Mx: number
  My: number
  Mz: number
}

// Re-export for convenience
export type { DistributedLoadInput, LoadDirection }

// Unit system
export type LengthUnit = 'm' | 'cm' | 'mm' | 'ft' | 'in'
export type ForceUnit = 'kN' | 'N' | 'kgf' | 'tonf' | 'kip' | 'lbf'

export interface UnitSystem {
  length: LengthUnit
  force: ForceUnit
}

export const UNIT_PRESETS = {
  SI: { length: 'm' as LengthUnit, force: 'kN' as ForceUnit },
  Imperial: { length: 'ft' as LengthUnit, force: 'kip' as ForceUnit },
  Metric_tonf: { length: 'm' as LengthUnit, force: 'tonf' as ForceUnit },
}

// App mode - draw (edit) or analysis (view results)
export type AppMode = 'draw' | 'analysis'

// Visualization options
export type DiagramType = 'none' | 'axial' | 'shear' | 'moment'

export interface GridSettings {
  visible: boolean
  spacing: number
  snap: boolean
  size: number
}

// Snap settings for object snap system
export interface SnapSettings {
  enabled: boolean
  activeSnaps: Record<SnapType, boolean>
  threshold: number
  gridSpacing: number
}

export interface ViewOptions {
  showExtrudedProfiles: boolean
  diagramType: DiagramType
  diagramScale: number
  showReactions: boolean
}

// Drawing state for frame drawing mode
export interface DrawingModeState {
  isActive: boolean
  state: DrawingState
  startPoint: { x: number; y: number; z: number } | null
  startNodeId: number | null
  currentPoint: { x: number; y: number; z: number } | null
  config: DrawingConfig
}

interface AppState {
  // Current project
  project: ProjectResponse | null
  projectId: string | null

  // Model data
  nodes: NodeResponse[]
  frames: FrameResponse[]
  shells: ShellResponse[]
  groups: GroupResponse[]

  // Selection
  selectedNodeId: number | null
  selectedFrameId: number | null
  selectedShellId: number | null
  selectedGroupId: number | null

  // Analysis state
  nodalLoads: NodalLoadInput[]
  distributedLoads: DistributedLoadInput[]
  analysisResults: AnalysisResponse | null
  isAnalyzing: boolean
  massInfo: MassResponse | null

  // Unit system
  units: UnitSystem

  // Visualization options
  viewOptions: ViewOptions
  gridSettings: GridSettings

  // UI state
  isLoading: boolean
  error: string | null

  // App mode
  mode: AppMode
  modelModified: boolean // Track if model changed since last analysis

  // Snap settings
  snapSettings: SnapSettings
  activeSnapPoint: SnapResult | null // Current snap point under cursor

  // Drawing mode
  drawingMode: DrawingModeState

  // Actions
  createProject: (name: string) => Promise<void>
  loadProject: (projectId: string) => Promise<void>

  // Node actions
  addNode: (x: number, y: number, z: number, restraintType?: RestraintType) => Promise<void>
  updateNode: (nodeId: number, data: Partial<NodeResponse>) => Promise<void>
  updateNodeRestraint: (nodeId: number, restraintType: RestraintType) => Promise<void>
  deleteNode: (nodeId: number) => Promise<void>
  selectNode: (nodeId: number | null) => void

  // Frame actions
  addFrame: (nodeI: number, nodeJ: number) => Promise<void>
  updateFrame: (frameId: number, data: { releases?: Partial<FrameReleases>; material_name?: string; section_name?: string; rotation?: number }) => Promise<void>
  deleteFrame: (frameId: number) => Promise<void>
  selectFrame: (frameId: number | null) => void

  // Shell actions
  addShell: (nodeIds: number[], thickness: number, shellType?: ShellType) => Promise<void>
  updateShell: (shellId: number, data: Partial<ShellResponse>) => Promise<void>
  deleteShell: (shellId: number) => Promise<void>
  selectShell: (shellId: number | null) => void

  // Group actions
  addGroup: (name: string, nodeIds?: number[], frameIds?: number[], shellIds?: number[]) => Promise<void>
  updateGroup: (groupId: number, data: { name?: string; node_ids?: number[]; frame_ids?: number[]; shell_ids?: number[]; color?: string; description?: string }) => Promise<void>
  deleteGroup: (groupId: number) => Promise<void>
  selectGroup: (groupId: number | null) => void
  addSelectionToGroup: (groupId: number) => Promise<void>

  // Analysis actions - nodal loads
  setNodalLoad: (load: NodalLoadInput) => void
  removeNodalLoad: (nodeId: number) => void
  clearNodalLoads: () => void

  // Analysis actions - distributed loads
  setDistributedLoad: (load: DistributedLoadInput) => void
  removeDistributedLoad: (frameId: number) => void
  clearDistributedLoads: () => void

  runAnalysis: () => Promise<void>
  clearResults: () => void
  getMass: () => Promise<void>

  // Mode actions
  setMode: (mode: AppMode) => void
  runAnalysisAndSwitchMode: () => Promise<void>
  switchToDrawMode: () => void

  // Unit actions
  setUnits: (units: UnitSystem) => void

  // View options actions
  setViewOptions: (options: Partial<ViewOptions>) => void
  setGridSettings: (settings: Partial<GridSettings>) => void

  // Snap actions
  setSnapSettings: (settings: Partial<SnapSettings>) => void
  toggleSnap: () => void
  toggleSnapType: (type: SnapType) => void
  setActiveSnapPoint: (snap: SnapResult | null) => void

  // Drawing mode actions
  toggleDrawingMode: () => void
  startDrawing: (point: { x: number; y: number; z: number }, nodeId?: number) => void
  updateDrawingPoint: (point: { x: number; y: number; z: number }) => void
  completeDrawing: (endPoint: { x: number; y: number; z: number }, endNodeId?: number) => Promise<void>
  cancelDrawing: () => void
  setDrawingConfig: (config: Partial<DrawingConfig>) => void

  // Refresh
  refreshModel: () => Promise<void>
}

export const useStore = create<AppState>((set, get) => ({
  // Initial state
  project: null,
  projectId: null,
  nodes: [],
  frames: [],
  shells: [],
  groups: [],
  selectedNodeId: null,
  selectedFrameId: null,
  selectedShellId: null,
  selectedGroupId: null,
  nodalLoads: [],
  distributedLoads: [],
  analysisResults: null,
  isAnalyzing: false,
  massInfo: null,
  units: UNIT_PRESETS.SI,
  viewOptions: {
    showExtrudedProfiles: false,
    diagramType: 'none',
    diagramScale: 1.0,
    showReactions: true,
  },
  gridSettings: {
    visible: true,
    spacing: 1,
    snap: false,
    size: 20,
  },
  isLoading: false,
  error: null,
  mode: 'draw',
  modelModified: false,
  snapSettings: DEFAULT_SNAP_SETTINGS,
  activeSnapPoint: null,
  drawingMode: {
    isActive: false,
    state: 'idle' as DrawingState,
    startPoint: null,
    startNodeId: null,
    currentPoint: null,
    config: DEFAULT_DRAWING_CONFIG,
  },

  // Create new project
  createProject: async (name: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.projects.create({ name })
      set({
        project: response.data,
        projectId: response.data.id,
        nodes: [],
        frames: [],
        shells: [],
        isLoading: false,
      })
    } catch (err) {
      set({ error: 'Failed to create project', isLoading: false })
    }
  },

  // Load existing project
  loadProject: async (projectId: string) => {
    set({ isLoading: true, error: null })
    try {
      const [projectRes, nodesRes, framesRes, shellsRes, groupsRes] = await Promise.all([
        api.projects.get(projectId),
        api.nodes.list(projectId),
        api.frames.list(projectId),
        api.shells.list(projectId),
        api.groups.list(projectId),
      ])
      set({
        project: projectRes.data,
        projectId,
        nodes: nodesRes.data,
        frames: framesRes.data,
        shells: shellsRes.data,
        groups: groupsRes.data,
        isLoading: false,
      })
    } catch (err) {
      set({ error: 'Failed to load project', isLoading: false })
    }
  },

  // Add node
  addNode: async (x: number, y: number, z: number, restraintType?: RestraintType) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.nodes.create(projectId, {
        x,
        y,
        z,
        restraint_type: restraintType,
      })
      set((state) => ({
        nodes: [...state.nodes, response.data],
        project: state.project
          ? { ...state.project, node_count: state.project.node_count + 1 }
          : null,
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to add node' })
    }
  },

  // Update node
  updateNode: async (nodeId: number, data: Partial<NodeResponse>) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.nodes.update(projectId, nodeId, data)
      set((state) => ({
        nodes: state.nodes.map((n) =>
          n.id === nodeId ? response.data : n
        ),
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to update node' })
    }
  },

  // Update node restraint type
  updateNodeRestraint: async (nodeId: number, restraintType: RestraintType) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.nodes.update(projectId, nodeId, {
        restraint_type: restraintType,
      })
      set((state) => ({
        nodes: state.nodes.map((n) =>
          n.id === nodeId ? response.data : n
        ),
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to update node restraint' })
    }
  },

  // Delete node
  deleteNode: async (nodeId: number) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      await api.nodes.delete(projectId, nodeId)
      set((state) => ({
        nodes: state.nodes.filter((n) => n.id !== nodeId),
        selectedNodeId:
          state.selectedNodeId === nodeId ? null : state.selectedNodeId,
        project: state.project
          ? { ...state.project, node_count: state.project.node_count - 1 }
          : null,
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to delete node' })
    }
  },

  // Select node
  selectNode: (nodeId: number | null) => {
    set({ selectedNodeId: nodeId, selectedFrameId: null, selectedShellId: null, selectedGroupId: null })
  },

  // Add frame
  addFrame: async (nodeI: number, nodeJ: number) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.frames.create(projectId, {
        node_i_id: nodeI,
        node_j_id: nodeJ,
      })
      set((state) => ({
        frames: [...state.frames, response.data],
        project: state.project
          ? { ...state.project, frame_count: state.project.frame_count + 1 }
          : null,
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to add frame' })
    }
  },

  // Update frame (releases, material, section, rotation)
  updateFrame: async (frameId: number, data: { releases?: Partial<FrameReleases>; material_name?: string; section_name?: string; rotation?: number }) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.frames.update(projectId, frameId, data)
      set((state) => ({
        frames: state.frames.map((f) =>
          f.id === frameId ? response.data : f
        ),
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to update frame' })
    }
  },

  // Delete frame
  deleteFrame: async (frameId: number) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      await api.frames.delete(projectId, frameId)
      set((state) => ({
        frames: state.frames.filter((f) => f.id !== frameId),
        selectedFrameId:
          state.selectedFrameId === frameId ? null : state.selectedFrameId,
        project: state.project
          ? { ...state.project, frame_count: state.project.frame_count - 1 }
          : null,
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to delete frame' })
    }
  },

  // Select frame
  selectFrame: (frameId: number | null) => {
    set({ selectedFrameId: frameId, selectedNodeId: null, selectedShellId: null, selectedGroupId: null })
  },

  // Add shell
  addShell: async (nodeIds: number[], thickness: number, shellType?: ShellType) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.shells.create(projectId, {
        node_ids: nodeIds,
        thickness,
        shell_type: shellType,
      })
      set((state) => ({
        shells: [...state.shells, response.data],
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to add shell' })
    }
  },

  // Update shell
  updateShell: async (shellId: number, data: Partial<ShellResponse>) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.shells.update(projectId, shellId, data)
      set((state) => ({
        shells: state.shells.map((s) =>
          s.id === shellId ? response.data : s
        ),
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to update shell' })
    }
  },

  // Delete shell
  deleteShell: async (shellId: number) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      await api.shells.delete(projectId, shellId)
      set((state) => ({
        shells: state.shells.filter((s) => s.id !== shellId),
        selectedShellId:
          state.selectedShellId === shellId ? null : state.selectedShellId,
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to delete shell' })
    }
  },

  // Select shell
  selectShell: (shellId: number | null) => {
    set({ selectedShellId: shellId, selectedNodeId: null, selectedFrameId: null, selectedGroupId: null })
  },

  // Add group
  addGroup: async (name: string, nodeIds?: number[], frameIds?: number[], shellIds?: number[]) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.groups.create(projectId, {
        name,
        node_ids: nodeIds,
        frame_ids: frameIds,
        shell_ids: shellIds,
      })
      set((state) => ({
        groups: [...state.groups, response.data],
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to add group' })
    }
  },

  // Update group
  updateGroup: async (groupId: number, data: { name?: string; node_ids?: number[]; frame_ids?: number[]; shell_ids?: number[]; color?: string; description?: string }) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      const response = await api.groups.update(projectId, groupId, data)
      set((state) => ({
        groups: state.groups.map((g) =>
          g.id === groupId ? response.data : g
        ),
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to update group' })
    }
  },

  // Delete group
  deleteGroup: async (groupId: number) => {
    const { projectId, mode } = get()
    if (!projectId || mode === 'analysis') return

    try {
      await api.groups.delete(projectId, groupId)
      set((state) => ({
        groups: state.groups.filter((g) => g.id !== groupId),
        selectedGroupId:
          state.selectedGroupId === groupId ? null : state.selectedGroupId,
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to delete group' })
    }
  },

  // Select group
  selectGroup: (groupId: number | null) => {
    set({ selectedGroupId: groupId, selectedNodeId: null, selectedFrameId: null, selectedShellId: null })
  },

  // Add current selection to a group
  addSelectionToGroup: async (groupId: number) => {
    const { projectId, mode, selectedNodeId, selectedFrameId, selectedShellId, groups } = get()
    if (!projectId || mode === 'analysis') return

    const group = groups.find((g) => g.id === groupId)
    if (!group) return

    const newNodeIds = selectedNodeId ? [...group.node_ids, selectedNodeId] : group.node_ids
    const newFrameIds = selectedFrameId ? [...group.frame_ids, selectedFrameId] : group.frame_ids
    const newShellIds = selectedShellId ? [...group.shell_ids, selectedShellId] : group.shell_ids

    try {
      const response = await api.groups.update(projectId, groupId, {
        node_ids: [...new Set(newNodeIds)],
        frame_ids: [...new Set(newFrameIds)],
        shell_ids: [...new Set(newShellIds)],
      })
      set((state) => ({
        groups: state.groups.map((g) =>
          g.id === groupId ? response.data : g
        ),
        modelModified: true,
      }))
    } catch (err) {
      set({ error: 'Failed to add to group' })
    }
  },

  // Set or update nodal load
  setNodalLoad: (load: NodalLoadInput) => {
    set((state) => {
      const existing = state.nodalLoads.findIndex((l) => l.node_id === load.node_id)
      if (existing >= 0) {
        const updated = [...state.nodalLoads]
        updated[existing] = load
        return { nodalLoads: updated }
      }
      return { nodalLoads: [...state.nodalLoads, load] }
    })
  },

  // Remove nodal load
  removeNodalLoad: (nodeId: number) => {
    set((state) => ({
      nodalLoads: state.nodalLoads.filter((l) => l.node_id !== nodeId),
    }))
  },

  // Clear all nodal loads
  clearNodalLoads: () => {
    set({ nodalLoads: [] })
  },

  // Set or update distributed load on frame
  setDistributedLoad: (load: DistributedLoadInput) => {
    set((state) => {
      const existing = state.distributedLoads.findIndex((l) => l.frame_id === load.frame_id)
      if (existing >= 0) {
        const updated = [...state.distributedLoads]
        updated[existing] = load
        return { distributedLoads: updated }
      }
      return { distributedLoads: [...state.distributedLoads, load] }
    })
  },

  // Remove distributed load from frame
  removeDistributedLoad: (frameId: number) => {
    set((state) => ({
      distributedLoads: state.distributedLoads.filter((l) => l.frame_id !== frameId),
    }))
  },

  // Clear all distributed loads
  clearDistributedLoads: () => {
    set({ distributedLoads: [] })
  },

  // Run structural analysis
  runAnalysis: async () => {
    const { projectId, nodalLoads, distributedLoads } = get()
    if (!projectId) return

    set({ isAnalyzing: true, error: null, analysisResults: null })
    try {
      const response = await api.analysis.run(projectId, {
        load_case: {
          name: 'LC1',
          load_type: 'Dead',
          self_weight_multiplier: 0,
        },
        nodal_loads: nodalLoads,
        distributed_loads: distributedLoads.length > 0 ? distributedLoads : undefined,
      })
      set({ analysisResults: response.data, isAnalyzing: false })
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Analysis failed'
      set({ error: errorMsg, isAnalyzing: false })
    }
  },

  // Clear analysis results
  clearResults: () => {
    set({ analysisResults: null })
  },

  // Get mass of structure
  getMass: async () => {
    const { projectId } = get()
    if (!projectId) return

    try {
      const response = await api.analysis.getMass(projectId)
      set({ massInfo: response.data })
    } catch (err) {
      console.error('Failed to get mass:', err)
    }
  },

  // Set mode
  setMode: (mode: AppMode) => {
    set({ mode })
  },

  // Run analysis and switch to analysis mode
  runAnalysisAndSwitchMode: async () => {
    const { projectId, nodalLoads, distributedLoads } = get()
    if (!projectId) return

    set({ isAnalyzing: true, error: null, analysisResults: null })
    try {
      const response = await api.analysis.run(projectId, {
        load_case: {
          name: 'LC1',
          load_type: 'Dead',
          self_weight_multiplier: 0,
        },
        nodal_loads: nodalLoads,
        distributed_loads: distributedLoads.length > 0 ? distributedLoads : undefined,
      })
      set({
        analysisResults: response.data,
        isAnalyzing: false,
        mode: 'analysis',
        modelModified: false,
      })
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Analysis failed'
      set({ error: errorMsg, isAnalyzing: false })
    }
  },

  // Switch back to draw mode (clears results)
  switchToDrawMode: () => {
    set({
      mode: 'draw',
      analysisResults: null,
    })
  },

  // Set unit system
  setUnits: (units: UnitSystem) => {
    set({ units })
  },

  // Set view options
  setViewOptions: (options: Partial<ViewOptions>) => {
    set((state) => ({
      viewOptions: { ...state.viewOptions, ...options },
    }))
  },

  // Set grid settings
  setGridSettings: (settings: Partial<GridSettings>) => {
    set((state) => ({
      gridSettings: { ...state.gridSettings, ...settings },
    }))
  },

  // Set snap settings
  setSnapSettings: (settings: Partial<SnapSettings>) => {
    set((state) => ({
      snapSettings: { ...state.snapSettings, ...settings },
    }))
  },

  // Toggle snap enabled
  toggleSnap: () => {
    set((state) => ({
      snapSettings: { ...state.snapSettings, enabled: !state.snapSettings.enabled },
    }))
  },

  // Toggle specific snap type
  toggleSnapType: (type: SnapType) => {
    set((state) => ({
      snapSettings: {
        ...state.snapSettings,
        activeSnaps: {
          ...state.snapSettings.activeSnaps,
          [type]: !state.snapSettings.activeSnaps[type],
        },
      },
    }))
  },

  // Set active snap point (under cursor)
  setActiveSnapPoint: (snap: SnapResult | null) => {
    set({ activeSnapPoint: snap })
  },

  // Toggle drawing mode on/off
  toggleDrawingMode: () => {
    set((state) => {
      if (state.drawingMode.isActive) {
        // Deactivate - cancel any drawing in progress
        return {
          drawingMode: {
            ...state.drawingMode,
            isActive: false,
            state: 'idle' as DrawingState,
            startPoint: null,
            startNodeId: null,
            currentPoint: null,
          },
        }
      } else {
        // Activate
        return {
          drawingMode: {
            ...state.drawingMode,
            isActive: true,
            state: 'idle' as DrawingState,
          },
        }
      }
    })
  },

  // Start drawing - first click
  startDrawing: (point: { x: number; y: number; z: number }, nodeId?: number) => {
    set((state) => ({
      drawingMode: {
        ...state.drawingMode,
        state: 'drawing' as DrawingState,
        startPoint: point,
        startNodeId: nodeId ?? null,
        currentPoint: point,
      },
    }))
  },

  // Update current point during drawing (mouse move)
  updateDrawingPoint: (point: { x: number; y: number; z: number }) => {
    set((state) => {
      if (state.drawingMode.state !== 'drawing') return state
      return {
        drawingMode: {
          ...state.drawingMode,
          currentPoint: point,
        },
      }
    })
  },

  // Complete drawing - second click creates node(s) and frame
  completeDrawing: async (endPoint: { x: number; y: number; z: number }, endNodeId?: number) => {
    const { projectId, drawingMode } = get()
    if (!projectId || drawingMode.state !== 'drawing' || !drawingMode.startPoint) return

    const startPoint = drawingMode.startPoint
    let startNodeId = drawingMode.startNodeId
    let finalEndNodeId = endNodeId

    try {
      // Create start node if needed
      if (startNodeId === null) {
        const response = await api.nodes.create(projectId, {
          x: startPoint.x,
          y: startPoint.y,
          z: startPoint.z,
        })
        startNodeId = response.data.id
        set((state) => ({
          nodes: [...state.nodes, response.data],
          project: state.project
            ? { ...state.project, node_count: state.project.node_count + 1 }
            : null,
          modelModified: true,
        }))
      }

      // Create end node if needed
      if (finalEndNodeId === null || finalEndNodeId === undefined) {
        const response = await api.nodes.create(projectId, {
          x: endPoint.x,
          y: endPoint.y,
          z: endPoint.z,
        })
        finalEndNodeId = response.data.id
        set((state) => ({
          nodes: [...state.nodes, response.data],
          project: state.project
            ? { ...state.project, node_count: state.project.node_count + 1 }
            : null,
          modelModified: true,
        }))
      }

      // Create frame between nodes
      const frameResponse = await api.frames.create(projectId, {
        node_i_id: startNodeId,
        node_j_id: finalEndNodeId,
      })
      set((state) => ({
        frames: [...state.frames, frameResponse.data],
        project: state.project
          ? { ...state.project, frame_count: state.project.frame_count + 1 }
          : null,
        modelModified: true,
      }))

      // Continue drawing: end point becomes new start point
      if (drawingMode.config.continuousMode) {
        set((state) => ({
          drawingMode: {
            ...state.drawingMode,
            startPoint: endPoint,
            startNodeId: finalEndNodeId ?? null,
            currentPoint: endPoint,
          },
        }))
      } else {
        // Reset to idle
        set((state) => ({
          drawingMode: {
            ...state.drawingMode,
            state: 'idle' as DrawingState,
            startPoint: null,
            startNodeId: null,
            currentPoint: null,
          },
        }))
      }
    } catch (err) {
      set({ error: 'Failed to create frame' })
    }
  },

  // Cancel current drawing
  cancelDrawing: () => {
    set((state) => ({
      drawingMode: {
        ...state.drawingMode,
        state: 'idle' as DrawingState,
        startPoint: null,
        startNodeId: null,
        currentPoint: null,
      },
    }))
  },

  // Update drawing config
  setDrawingConfig: (config: Partial<DrawingConfig>) => {
    set((state) => ({
      drawingMode: {
        ...state.drawingMode,
        config: { ...state.drawingMode.config, ...config },
      },
    }))
  },

  // Refresh model data
  refreshModel: async () => {
    const { projectId } = get()
    if (!projectId) return

    try {
      const [nodesRes, framesRes, shellsRes, groupsRes] = await Promise.all([
        api.nodes.list(projectId),
        api.frames.list(projectId),
        api.shells.list(projectId),
        api.groups.list(projectId),
      ])
      set({
        nodes: nodesRes.data,
        frames: framesRes.data,
        shells: shellsRes.data,
        groups: groupsRes.data,
      })
    } catch (err) {
      set({ error: 'Failed to refresh model' })
    }
  },
}))

export default useStore
