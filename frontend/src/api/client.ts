import axios from 'axios'

/**
 * API Client for PAZ Backend.
 * Configured to work with FastAPI backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error('API Error:', error.response.data)
    } else if (error.request) {
      console.error('Network Error:', error.request)
    } else {
      console.error('Request Error:', error.message)
    }
    return Promise.reject(error)
  }
)

// Restraint types
export type RestraintType =
  | 'free'
  | 'fixed'
  | 'pinned'
  | 'roller_x'
  | 'roller_y'
  | 'roller_z'
  | 'vertical_only'
  | 'custom'

export const RESTRAINT_TYPE_LABELS: Record<RestraintType, string> = {
  free: 'Libre',
  fixed: 'Empotrado',
  pinned: 'Articulado',
  roller_x: 'Rodillo X',
  roller_y: 'Rodillo Y',
  roller_z: 'Rodillo Z',
  vertical_only: 'Fijo Vertical',
  custom: 'Personalizado',
}

export const RESTRAINT_TYPE_DESCRIPTIONS: Record<RestraintType, string> = {
  free: 'Todos los DOF libres',
  fixed: 'Todos los DOF restringidos (empotrado)',
  pinned: 'Traslaciones restringidas, rotaciones libres',
  roller_x: 'Libre en X, fijo en Y/Z',
  roller_y: 'Libre en Y, fijo en X/Z',
  roller_z: 'Libre en Z, fijo en X/Y',
  vertical_only: 'Solo Uz restringido',
  custom: 'Configuración manual por DOF',
}

// Load direction types
export type LoadDirection =
  | 'Gravity'
  | 'Local X'
  | 'Local Y'
  | 'Local Z'
  | 'Global X'
  | 'Global Y'
  | 'Global Z'

export const LOAD_DIRECTION_LABELS: Record<LoadDirection, string> = {
  'Gravity': 'Gravedad (-Z)',
  'Local X': 'Local X',
  'Local Y': 'Local Y',
  'Local Z': 'Local Z',
  'Global X': 'Global X',
  'Global Y': 'Global Y',
  'Global Z': 'Global Z',
}

// Distributed load on frame
export interface DistributedLoadInput {
  frame_id: number
  direction?: LoadDirection
  w_start: number
  w_end?: number
  start_loc?: number
  end_loc?: number
}

// Point load on frame
export interface PointLoadOnFrameInput {
  frame_id: number
  location: number
  P: number
  direction?: LoadDirection
  M?: number
}

// Types for API responses
export interface ProjectResponse {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  node_count: number
  frame_count: number
}

export interface NodeResponse {
  id: number
  x: number
  y: number
  z: number
  restraint: {
    ux: boolean
    uy: boolean
    uz: boolean
    rx: boolean
    ry: boolean
    rz: boolean
    restraint_type?: RestraintType
  }
  restraint_type: RestraintType
  is_supported: boolean
}

// Frame releases configuration
export interface FrameReleases {
  P_i: boolean
  V2_i: boolean
  V3_i: boolean
  T_i: boolean
  M2_i: boolean
  M3_i: boolean
  P_j: boolean
  V2_j: boolean
  V3_j: boolean
  T_j: boolean
  M2_j: boolean
  M3_j: boolean
}

// Default releases (all fixed)
export const DEFAULT_RELEASES: FrameReleases = {
  P_i: false, V2_i: false, V3_i: false, T_i: false, M2_i: false, M3_i: false,
  P_j: false, V2_j: false, V3_j: false, T_j: false, M2_j: false, M3_j: false,
}

// Preset release configurations
export type ReleasePreset = 'fixed_fixed' | 'pinned_pinned' | 'fixed_pinned' | 'pinned_fixed' | 'custom'

export const RELEASE_PRESETS: Record<ReleasePreset, { label: string; releases: FrameReleases }> = {
  fixed_fixed: {
    label: 'Fijo-Fijo',
    releases: { ...DEFAULT_RELEASES },
  },
  pinned_pinned: {
    label: 'Articulado-Articulado',
    releases: {
      ...DEFAULT_RELEASES,
      M2_i: true, M3_i: true, M2_j: true, M3_j: true,
    },
  },
  fixed_pinned: {
    label: 'Fijo-Articulado',
    releases: {
      ...DEFAULT_RELEASES,
      M2_j: true, M3_j: true,
    },
  },
  pinned_fixed: {
    label: 'Articulado-Fijo',
    releases: {
      ...DEFAULT_RELEASES,
      M2_i: true, M3_i: true,
    },
  },
  custom: {
    label: 'Personalizado',
    releases: { ...DEFAULT_RELEASES },
  },
}

export interface FrameResponse {
  id: number
  node_i_id: number
  node_j_id: number
  material_name: string
  section_name: string
  rotation: number
  releases: FrameReleases
  label: string
}

// Shell types
export type ShellType = 'plate' | 'membrane' | 'shell'

export const SHELL_TYPE_LABELS: Record<ShellType, string> = {
  plate: 'Placa (solo flexión)',
  membrane: 'Membrana (solo en plano)',
  shell: 'Shell (general)',
}

export interface ShellResponse {
  id: number
  node_ids: number[]
  material_name: string
  thickness: number
  shell_type: ShellType
  label: string
}

// Element group
export interface GroupResponse {
  id: number
  name: string
  node_ids: number[]
  frame_ids: number[]
  shell_ids: number[]
  color: string
  parent_id: number | null
  description: string
  element_count: number
}

export interface FrameForceResult {
  location: number
  P: number
  V2: number
  V3: number
  T: number
  M2: number
  M3: number
}

export interface FrameResult {
  frame_id: number
  forces: FrameForceResult[]
  P_max: number
  P_min: number
  V2_max: number
  V3_max: number
  M2_max: number
  M3_max: number
  V_max: number  // Max of V2 and V3
  M_max: number  // Max of M2 and M3
}

export interface AnalysisResponse {
  success: boolean
  error_message?: string
  load_case_id: string
  load_case_name: string
  displacements: Array<{
    node_id: number
    Ux: number
    Uy: number
    Uz: number
    Rx: number
    Ry: number
    Rz: number
  }>
  reactions: Array<{
    node_id: number
    Fx: number
    Fy: number
    Fz: number
    Mx: number
    My: number
    Mz: number
  }>
  frame_results: FrameResult[]
  max_displacement: number
}

// Mass calculation response
export interface FrameMassResult {
  frame_id: number
  mass_kg: number
  weight_kN: number
}

export interface MassResponse {
  total_mass_kg: number
  total_weight_kN: number
  frame_masses: FrameMassResult[]
}

// API endpoints
export const api = {
  // Health check
  health: () => apiClient.get('/health'),

  // Projects
  projects: {
    list: () => apiClient.get<ProjectResponse[]>('/api/projects/'),
    get: (id: string) => apiClient.get<ProjectResponse>(`/api/projects/${id}`),
    create: (data: { name: string; description?: string }) =>
      apiClient.post<ProjectResponse>('/api/projects/', data),
    update: (id: string, data: { name?: string; description?: string }) =>
      apiClient.patch<ProjectResponse>(`/api/projects/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/projects/${id}`),
    exportDXF: (id: string) =>
      apiClient.get(`/api/projects/${id}/export/dxf`, { responseType: 'blob' }),
    exportCSV: (id: string) =>
      apiClient.get(`/api/projects/${id}/export/csv`, { responseType: 'blob' }),
  },

  // Model - Nodes
  nodes: {
    list: (projectId: string) =>
      apiClient.get<NodeResponse[]>(`/api/model/${projectId}/nodes`),
    get: (projectId: string, nodeId: number) =>
      apiClient.get<NodeResponse>(`/api/model/${projectId}/nodes/${nodeId}`),
    create: (projectId: string, data: {
      x: number
      y: number
      z?: number
      restraint?: {
        ux?: boolean
        uy?: boolean
        uz?: boolean
        rx?: boolean
        ry?: boolean
        rz?: boolean
      }
      restraint_type?: RestraintType
    }) => apiClient.post<NodeResponse>(`/api/model/${projectId}/nodes`, data),
    update: (projectId: string, nodeId: number, data: {
      x?: number
      y?: number
      z?: number
      restraint?: {
        ux?: boolean
        uy?: boolean
        uz?: boolean
        rx?: boolean
        ry?: boolean
        rz?: boolean
      }
      restraint_type?: RestraintType
    }) => apiClient.patch<NodeResponse>(`/api/model/${projectId}/nodes/${nodeId}`, data),
    delete: (projectId: string, nodeId: number) =>
      apiClient.delete(`/api/model/${projectId}/nodes/${nodeId}`),
  },

  // Model - Frames
  frames: {
    list: (projectId: string) =>
      apiClient.get<FrameResponse[]>(`/api/model/${projectId}/frames`),
    get: (projectId: string, frameId: number) =>
      apiClient.get<FrameResponse>(`/api/model/${projectId}/frames/${frameId}`),
    create: (projectId: string, data: {
      node_i_id: number
      node_j_id: number
      material_name?: string
      section_name?: string
      rotation?: number
      releases?: Partial<FrameReleases>
      label?: string
    }) => apiClient.post<FrameResponse>(`/api/model/${projectId}/frames`, data),
    update: (projectId: string, frameId: number, data: {
      material_name?: string
      section_name?: string
      rotation?: number
      releases?: Partial<FrameReleases>
      label?: string
    }) => apiClient.patch<FrameResponse>(`/api/model/${projectId}/frames/${frameId}`, data),
    delete: (projectId: string, frameId: number) =>
      apiClient.delete(`/api/model/${projectId}/frames/${frameId}`),
  },

  // Model - Shells
  shells: {
    list: (projectId: string) =>
      apiClient.get<ShellResponse[]>(`/api/model/${projectId}/shells`),
    get: (projectId: string, shellId: number) =>
      apiClient.get<ShellResponse>(`/api/model/${projectId}/shells/${shellId}`),
    create: (projectId: string, data: {
      node_ids: number[]
      material_name?: string
      thickness: number
      shell_type?: ShellType
      label?: string
    }) => apiClient.post<ShellResponse>(`/api/model/${projectId}/shells`, data),
    update: (projectId: string, shellId: number, data: {
      material_name?: string
      thickness?: number
      shell_type?: ShellType
      label?: string
    }) => apiClient.patch<ShellResponse>(`/api/model/${projectId}/shells/${shellId}`, data),
    delete: (projectId: string, shellId: number) =>
      apiClient.delete(`/api/model/${projectId}/shells/${shellId}`),
  },

  // Model - Groups
  groups: {
    list: (projectId: string) =>
      apiClient.get<GroupResponse[]>(`/api/model/${projectId}/groups`),
    get: (projectId: string, groupId: number) =>
      apiClient.get<GroupResponse>(`/api/model/${projectId}/groups/${groupId}`),
    create: (projectId: string, data: {
      name: string
      node_ids?: number[]
      frame_ids?: number[]
      shell_ids?: number[]
      color?: string
      parent_id?: number | null
      description?: string
    }) => apiClient.post<GroupResponse>(`/api/model/${projectId}/groups`, data),
    update: (projectId: string, groupId: number, data: {
      name?: string
      node_ids?: number[]
      frame_ids?: number[]
      shell_ids?: number[]
      color?: string
      parent_id?: number | null
      description?: string
    }) => apiClient.patch<GroupResponse>(`/api/model/${projectId}/groups/${groupId}`, data),
    delete: (projectId: string, groupId: number) =>
      apiClient.delete(`/api/model/${projectId}/groups/${groupId}`),
  },

  // Library
  library: {
    materials: () => apiClient.get<Array<{
      name: string
      material_type: string
      E: number
      nu: number
      rho: number
    }>>('/api/library/materials'),
    getMaterial: (name: string) =>
      apiClient.get(`/api/library/materials/${name}`),
    sections: (params?: { shape?: string; limit?: number }) =>
      apiClient.get<Array<{
        name: string
        shape: string
        A: number
        Ix: number
        Iy: number
        J: number
      }>>('/api/library/sections', { params }),
    getSection: (name: string) =>
      apiClient.get(`/api/library/sections/${name}`),
    createParametricSection: (data: {
      name: string
      shape: 'Rectangular' | 'Circular' | 'IShape'
      width?: number
      height?: number
      radius?: number
      inner_radius?: number
      d?: number
      bf?: number
      tf?: number
      tw?: number
    }) => apiClient.post<{
      name: string
      shape: string
      A: number
      Ix: number
      Iy: number
      J: number
    }>('/api/library/sections/parametric', data),
  },

  // Analysis
  analysis: {
    run: (projectId: string, data?: {
      load_case?: {
        name?: string
        load_type?: string
        self_weight_multiplier?: number
      }
      nodal_loads?: Array<{
        node_id: number
        Fx?: number
        Fy?: number
        Fz?: number
        Mx?: number
        My?: number
        Mz?: number
      }>
      distributed_loads?: DistributedLoadInput[]
      point_loads?: PointLoadOnFrameInput[]
    }) => apiClient.post<AnalysisResponse>(`/api/analysis/${projectId}/run`, data || {}),

    getMass: (projectId: string) =>
      apiClient.get<MassResponse>(`/api/analysis/${projectId}/mass`),
  },
}

export default apiClient
