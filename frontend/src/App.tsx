import { useState, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import Viewport from './components/Viewport'
import { useStore, DiagramType, LoadDirection } from './store/useStore'
import { api, RestraintType, RESTRAINT_TYPE_LABELS, LOAD_DIRECTION_LABELS, ShellType, SHELL_TYPE_LABELS, ReleasePreset, RELEASE_PRESETS, DEFAULT_RELEASES } from './api/client'
import SnapSettingsPanel from './components/SnapSettingsPanel'
import {
  lengthFromBase,
  lengthToBase,
  forceFromBase,
  forceToBase,
  distLoadFromBase,
  distLoadToBase,
  momentFromBase,
  formatValue,
  getDistLoadLabel,
  getMomentLabel,
} from './services/UnitService'

function App() {
  const {
    project,
    nodes,
    frames,
    shells,
    groups,
    selectedNodeId,
    selectedFrameId,
    selectedShellId,
    selectedGroupId,
    nodalLoads,
    analysisResults,
    units,
    viewOptions,
    gridSettings,
    isLoading,
    isAnalyzing,
    error,
    createProject,
    addNode,
    addFrame,
    addShell,
    deleteNode,
    deleteFrame,
    deleteShell,
    updateNodeRestraint,
    updateFrame,
    setNodalLoad,
    removeNodalLoad,
    setDistributedLoad,
    clearResults,
    massInfo,
    getMass,
    mode,
    modelModified,
    runAnalysisAndSwitchMode,
    switchToDrawMode,
    setUnits,
    setViewOptions,
    setGridSettings,
    snapSettings,
    toggleSnap,
    drawingMode,
    toggleDrawingMode,
    cancelDrawing,
    addGroup,
    // updateGroup - reserved for future use
    deleteGroup,
    selectGroup,
    addSelectionToGroup,
  } = useStore()

  const [showNewProject, setShowNewProject] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [showAddNode, setShowAddNode] = useState(false)
  const [nodeX, setNodeX] = useState('0')
  const [nodeY, setNodeY] = useState('0')
  const [nodeZ, setNodeZ] = useState('0')
  const [nodeRestraintType, setNodeRestraintType] = useState<RestraintType>('free')
  const [showAddFrame, setShowAddFrame] = useState(false)
  const [frameNodeI, setFrameNodeI] = useState('')
  const [frameNodeJ, setFrameNodeJ] = useState('')
  const [showAddLoad, setShowAddLoad] = useState(false)
  const [loadNodeId, setLoadNodeId] = useState('')
  const [loadFx, setLoadFx] = useState('0')
  const [loadFy, setLoadFy] = useState('0')
  const [loadFz, setLoadFz] = useState('-10')
  const [showAddDistLoad, setShowAddDistLoad] = useState(false)
  const [distLoadFrameId, setDistLoadFrameId] = useState('')
  const [distLoadType, setDistLoadType] = useState<'uniform' | 'triangular' | 'trapezoidal'>('uniform')
  const [distLoadW, setDistLoadW] = useState('10')
  const [distLoadWEnd, setDistLoadWEnd] = useState('10')
  const [distLoadDirection, setDistLoadDirection] = useState<LoadDirection>('Gravity')
  const [showResults, setShowResults] = useState(false)
  const [showCreateSection, setShowCreateSection] = useState(false)
  const [showViewSettings, setShowViewSettings] = useState(false)
  const [showSnapSettings, setShowSnapSettings] = useState(false)
  const [sectionName, setSectionName] = useState('')
  const [sectionShape, setSectionShape] = useState<'Rectangular' | 'Circular' | 'IShape'>('Rectangular')
  const [sectionWidth, setSectionWidth] = useState('0.3')
  const [sectionHeight, setSectionHeight] = useState('0.5')
  const [sectionRadius, setSectionRadius] = useState('0.15')
  const [sectionD, setSectionD] = useState('0.4')
  const [sectionBf, setSectionBf] = useState('0.2')
  const [sectionTf, setSectionTf] = useState('0.02')
  const [sectionTw, setSectionTw] = useState('0.01')
  const [showAddShell, setShowAddShell] = useState(false)
  const [shellNodes, setShellNodes] = useState<string[]>(['', '', '', ''])
  const [shellThickness, setShellThickness] = useState('0.2')
  const [shellType, setShellType] = useState<ShellType>('shell')
  const [showAddGroup, setShowAddGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  // const [showGroups, setShowGroups] = useState(false) // Reserved for future group panel
  const [availableMaterials, setAvailableMaterials] = useState<string[]>(['A36', 'A572Gr50', 'Concrete'])
  const [availableSections, setAvailableSections] = useState<string[]>(['W14X22', 'W14X30', 'W14X48', 'W21X44', 'W21X62'])

  // Load available materials and sections
  useEffect(() => {
    const loadLibrary = async () => {
      try {
        const [matResponse, secResponse] = await Promise.all([
          api.library.materials(),
          api.library.sections({ limit: 50 }),
        ])
        if (matResponse.data) {
          setAvailableMaterials(matResponse.data.map((m) => m.name))
        }
        if (secResponse.data) {
          setAvailableSections(secResponse.data.map((s) => s.name))
        }
      } catch (err) {
        console.error('Failed to load library:', err)
      }
    }
    loadLibrary()
  }, [])

  const selectedNode = nodes.find((n) => n.id === selectedNodeId)
  const selectedFrame = frames.find((f) => f.id === selectedFrameId)
  const selectedShell = shells.find((s) => s.id === selectedShellId)
  const selectedGroup = groups.find((g) => g.id === selectedGroupId)

  const handleCreateProject = async () => {
    if (newProjectName.trim()) {
      await createProject(newProjectName.trim())
      setNewProjectName('')
      setShowNewProject(false)
    }
  }

  const handleAddNode = async () => {
    // Convert from display units to base units (m)
    await addNode(
      lengthToBase(parseFloat(nodeX), units.length),
      lengthToBase(parseFloat(nodeY), units.length),
      lengthToBase(parseFloat(nodeZ), units.length),
      nodeRestraintType !== 'free' ? nodeRestraintType : undefined
    )
    setShowAddNode(false)
    setNodeX('0')
    setNodeY('0')
    setNodeZ('0')
    setNodeRestraintType('free')
  }

  const handleAddFrame = async () => {
    const i = parseInt(frameNodeI)
    const j = parseInt(frameNodeJ)
    if (!isNaN(i) && !isNaN(j) && i !== j) {
      await addFrame(i, j)
      setShowAddFrame(false)
      setFrameNodeI('')
      setFrameNodeJ('')
    }
  }

  const handleAddLoad = () => {
    const nodeId = parseInt(loadNodeId)
    if (!isNaN(nodeId)) {
      // Convert from display units to base units (kN)
      setNodalLoad({
        node_id: nodeId,
        Fx: forceToBase(parseFloat(loadFx) || 0, units.force),
        Fy: forceToBase(parseFloat(loadFy) || 0, units.force),
        Fz: forceToBase(parseFloat(loadFz) || 0, units.force),
        Mx: 0,
        My: 0,
        Mz: 0,
      })
      setShowAddLoad(false)
      setLoadNodeId('')
      setLoadFx('0')
      setLoadFy('0')
      setLoadFz('-10')
    }
  }

  const handleAddDistLoad = () => {
    const frameId = parseInt(distLoadFrameId)
    const wStart = parseFloat(distLoadW)
    const wEnd = parseFloat(distLoadWEnd)

    if (!isNaN(frameId) && !isNaN(wStart)) {
      // Convert from display units to base units (kN/m)
      let w_start = distLoadToBase(wStart, units.force, units.length)
      let w_end = distLoadToBase(wStart, units.force, units.length)

      if (distLoadType === 'triangular') {
        // Triangular: 0 to w_start
        w_start = 0
        w_end = distLoadToBase(wStart, units.force, units.length)
      } else if (distLoadType === 'trapezoidal') {
        // Trapezoidal: w_start to w_end
        w_end = isNaN(wEnd) ? w_start : distLoadToBase(wEnd, units.force, units.length)
      }

      setDistributedLoad({
        frame_id: frameId,
        w_start,
        w_end,
        direction: distLoadDirection,
      })
      setShowAddDistLoad(false)
      setDistLoadFrameId('')
      setDistLoadW('10')
      setDistLoadWEnd('10')
      setDistLoadType('uniform')
      setDistLoadDirection('Gravity')
    }
  }

  const handleAddShell = async () => {
    const nodeIds = shellNodes
      .filter((n) => n.trim() !== '')
      .map((n) => parseInt(n))
      .filter((n) => !isNaN(n))

    if (nodeIds.length >= 3 && nodeIds.length <= 4) {
      await addShell(nodeIds, parseFloat(shellThickness), shellType)
      setShowAddShell(false)
      setShellNodes(['', '', '', ''])
      setShellThickness('0.2')
      setShellType('shell')
    }
  }

  const handleExportDXF = async () => {
    const { projectId, project } = useStore.getState()
    if (!projectId) return
    try {
      const response = await api.projects.exportDXF(projectId)
      const blob = new Blob([response.data], { type: 'application/dxf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${project?.name || 'model'}.dxf`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to export DXF:', err)
    }
  }

  const handleCreateSection = async () => {
    if (!sectionName.trim()) return
    try {
      const data: Parameters<typeof api.library.createParametricSection>[0] = {
        name: sectionName,
        shape: sectionShape,
      }
      if (sectionShape === 'Rectangular') {
        data.width = parseFloat(sectionWidth)
        data.height = parseFloat(sectionHeight)
      } else if (sectionShape === 'Circular') {
        data.radius = parseFloat(sectionRadius)
      } else if (sectionShape === 'IShape') {
        data.d = parseFloat(sectionD)
        data.bf = parseFloat(sectionBf)
        data.tf = parseFloat(sectionTf)
        data.tw = parseFloat(sectionTw)
      }
      await api.library.createParametricSection(data)
      setShowCreateSection(false)
      setSectionName('')
    } catch (err) {
      console.error('Failed to create section:', err)
    }
  }

  const canRunAnalysis = nodes.length >= 2 && frames.length >= 1 && nodes.some((n) => n.is_supported)

  // Auto-fetch mass when frames change
  useEffect(() => {
    if (frames.length > 0) {
      getMass()
    }
  }, [frames.length, getMass])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // F3 - toggle snap
      if (e.key === 'F3') {
        e.preventDefault()
        toggleSnap()
      }
      // D - toggle drawing mode (only in draw mode, not analysis)
      if (e.key === 'd' || e.key === 'D') {
        if (mode === 'draw' && !e.ctrlKey && !e.metaKey) {
          // Don't trigger if typing in input
          if (document.activeElement?.tagName !== 'INPUT' &&
              document.activeElement?.tagName !== 'TEXTAREA') {
            e.preventDefault()
            toggleDrawingMode()
          }
        }
      }
      // ESC - cancel drawing
      if (e.key === 'Escape') {
        if (drawingMode.isActive) {
          cancelDrawing()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleSnap, toggleDrawingMode, cancelDrawing, mode, drawingMode.isActive])

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-900">
      {/* Header */}
      <header className={`h-12 border-b flex items-center px-4 ${
        mode === 'analysis' ? 'bg-purple-900 border-purple-700' : 'bg-gray-800 border-gray-700'
      }`}>
        <h1 className="text-white font-bold text-lg">PAZ</h1>
        <span className="text-gray-400 text-sm ml-2">v1.0.0-mvp</span>
        {project && (
          <span className="text-blue-400 text-sm ml-4">{project.name}</span>
        )}
        {/* Mode Indicator */}
        {project && (
          <span className={`ml-4 px-2 py-0.5 text-xs font-medium rounded ${
            mode === 'analysis'
              ? 'bg-purple-600 text-white'
              : 'bg-green-600 text-white'
          }`}>
            {mode === 'analysis' ? 'ANÁLISIS' : 'DIBUJO'}
            {mode === 'draw' && modelModified && ' •'}
          </span>
        )}
        <div className="ml-auto flex gap-2">
          {!project ? (
            <button
              onClick={() => setShowNewProject(true)}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Nuevo Proyecto
            </button>
          ) : mode === 'draw' ? (
            <>
              <button
                onClick={toggleDrawingMode}
                className={`px-3 py-1 text-sm rounded ${
                  drawingMode.isActive
                    ? 'bg-cyan-500 text-white'
                    : 'bg-cyan-700 text-white hover:bg-cyan-600'
                }`}
                title="D para activar/desactivar"
              >
                {drawingMode.isActive ? '✓ Dibujando' : '✏ Dibujar'}
              </button>
              <button
                onClick={() => setShowAddNode(true)}
                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                disabled={drawingMode.isActive}
              >
                + Nodo
              </button>
              <button
                onClick={() => setShowAddFrame(true)}
                className="px-3 py-1 text-sm bg-orange-600 text-white rounded hover:bg-orange-700"
                disabled={nodes.length < 2}
              >
                + Frame
              </button>
              <button
                onClick={() => setShowAddShell(true)}
                className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                disabled={nodes.length < 3}
                title="Crear shell (losa/muro)"
              >
                + Shell
              </button>
              <button
                onClick={() => setShowAddLoad(true)}
                className="px-3 py-1 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700"
                disabled={nodes.length < 1}
                title="Carga puntual en nodo"
              >
                + Carga
              </button>
              <button
                onClick={() => setShowAddDistLoad(true)}
                className="px-3 py-1 text-sm bg-orange-500 text-white rounded hover:bg-orange-600"
                disabled={frames.length < 1}
                title="Carga distribuida en frame"
              >
                + Dist.
              </button>
              <button
                onClick={runAnalysisAndSwitchMode}
                className="px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                disabled={!canRunAnalysis || isAnalyzing}
                title="Ejecutar análisis"
              >
                {isAnalyzing ? 'Analizando...' : '▶ Analizar'}
              </button>
              <button
                onClick={() => setShowCreateSection(true)}
                className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-500"
              >
                + Sección
              </button>
              <button
                onClick={handleExportDXF}
                className="px-3 py-1 text-sm bg-teal-600 text-white rounded hover:bg-teal-700"
                disabled={nodes.length === 0}
              >
                Export DXF
              </button>
              <button
                onClick={() => setShowViewSettings(true)}
                className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-500"
              >
                Vista
              </button>
            </>
          ) : (
            // Analysis mode buttons
            <>
              <button
                onClick={() => setShowResults(true)}
                className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Ver Resultados
              </button>
              <button
                onClick={() => setShowViewSettings(true)}
                className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-500"
              >
                Vista
              </button>
              <button
                onClick={switchToDrawMode}
                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"
              >
                ✏ Volver a Dibujo
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Model Tree */}
        <aside className="w-64 bg-gray-800 border-r border-gray-700 p-4 overflow-y-auto">
          <h2 className="text-white font-semibold mb-4">Modelo</h2>
          {project ? (
            <div className="text-sm space-y-4">
              {/* Nodes */}
              <div>
                <h3 className="text-gray-400 font-medium mb-2">
                  Nodos ({nodes.length})
                </h3>
                <ul className="space-y-1">
                  {nodes.map((node) => (
                    <li
                      key={node.id}
                      className={`px-2 py-1 rounded cursor-pointer ${
                        node.id === selectedNodeId
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-300 hover:bg-gray-700'
                      }`}
                      onClick={() => useStore.getState().selectNode(node.id)}
                    >
                      Node {node.id}
                      {node.is_supported && ' [S]'}
                      <span className="text-xs text-gray-400 ml-2">
                        ({formatValue(lengthFromBase(node.x, units.length), 1)}, {formatValue(lengthFromBase(node.y, units.length), 1)}, {formatValue(lengthFromBase(node.z, units.length), 1)})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Frames */}
              <div>
                <h3 className="text-gray-400 font-medium mb-2">
                  Frames ({frames.length})
                </h3>
                <ul className="space-y-1">
                  {frames.map((frame) => (
                    <li
                      key={frame.id}
                      className={`px-2 py-1 rounded cursor-pointer ${
                        frame.id === selectedFrameId
                          ? 'bg-orange-600 text-white'
                          : 'text-gray-300 hover:bg-gray-700'
                      }`}
                      onClick={() => useStore.getState().selectFrame(frame.id)}
                    >
                      Frame {frame.id}
                      <span className="text-xs text-gray-400 ml-2">
                        ({frame.node_i_id} → {frame.node_j_id})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Shells */}
              {shells.length > 0 && (
                <div>
                  <h3 className="text-gray-400 font-medium mb-2">
                    Shells ({shells.length})
                  </h3>
                  <ul className="space-y-1">
                    {shells.map((shell) => (
                      <li
                        key={shell.id}
                        className={`px-2 py-1 rounded cursor-pointer ${
                          shell.id === selectedShellId
                            ? 'bg-blue-500 text-white'
                            : 'text-gray-300 hover:bg-gray-700'
                        }`}
                        onClick={() => useStore.getState().selectShell(shell.id)}
                      >
                        Shell {shell.id}
                        <span className="text-xs text-gray-400 ml-2">
                          ({shell.node_ids.length} nodos, t={shell.thickness}m)
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Grupos */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-gray-400 font-medium">
                    Grupos ({groups.length})
                  </h3>
                  <button
                    onClick={() => setShowAddGroup(true)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                    disabled={mode === 'analysis'}
                  >
                    + Nuevo
                  </button>
                </div>
                {groups.length > 0 && (
                  <ul className="space-y-1">
                    {groups.map((group) => (
                      <li
                        key={group.id}
                        className={`px-2 py-1 rounded cursor-pointer ${
                          group.id === selectedGroupId
                            ? 'bg-purple-500 text-white'
                            : 'text-gray-300 hover:bg-gray-700'
                        }`}
                        onClick={() => selectGroup(group.id)}
                      >
                        <div className="flex justify-between items-center">
                          <span className="flex items-center gap-1">
                            <span
                              className="w-2 h-2 rounded-full"
                              style={{ backgroundColor: group.color }}
                            ></span>
                            {group.name}
                          </span>
                          <span className="text-xs text-gray-400">
                            {group.element_count}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Cargas */}
              <div>
                <h3 className="text-gray-400 font-medium mb-2">
                  Cargas ({nodalLoads.length + useStore.getState().distributedLoads.length})
                </h3>
                {/* Cargas nodales */}
                {nodalLoads.length > 0 && (
                  <div className="mb-2">
                    <p className="text-xs text-gray-500 mb-1">Puntuales</p>
                    <ul className="space-y-1">
                      {nodalLoads.map((load) => (
                        <li
                          key={load.node_id}
                          className="px-2 py-1 rounded text-gray-300 hover:bg-gray-700 flex justify-between items-center"
                        >
                          <span>
                            N{load.node_id}
                            <span className="text-xs text-yellow-400 ml-2">
                              ({formatValue(forceFromBase(load.Fx, units.force))}, {formatValue(forceFromBase(load.Fy, units.force))}, {formatValue(forceFromBase(load.Fz, units.force))}) {units.force}
                            </span>
                          </span>
                          <button
                            onClick={() => removeNodalLoad(load.node_id)}
                            className="text-red-400 hover:text-red-300 text-xs"
                            disabled={mode === 'analysis'}
                          >
                            ×
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* Cargas distribuidas */}
                {useStore.getState().distributedLoads.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Distribuidas</p>
                    <ul className="space-y-1">
                      {useStore.getState().distributedLoads.map((load, idx) => (
                        <li
                          key={`dist-${load.frame_id}-${idx}`}
                          className="px-2 py-1 rounded text-gray-300 hover:bg-gray-700 flex justify-between items-center"
                        >
                          <span>
                            F{load.frame_id}
                            <span className="text-xs text-orange-400 ml-2">
                              {load.w_start === load.w_end
                                ? `${formatValue(distLoadFromBase(load.w_start, units.force, units.length))} ${getDistLoadLabel(units.force, units.length)}`
                                : `${formatValue(distLoadFromBase(load.w_start, units.force, units.length))}→${formatValue(distLoadFromBase(load.w_end || 0, units.force, units.length))} ${getDistLoadLabel(units.force, units.length)}`}
                            </span>
                          </span>
                          <button
                            onClick={() => useStore.getState().removeDistributedLoad(load.frame_id)}
                            className="text-red-400 hover:text-red-300 text-xs"
                            disabled={mode === 'analysis'}
                          >
                            ×
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Mass Info */}
              {massInfo && massInfo.total_mass_kg > 0 && (
                <div className="border-t border-gray-700 pt-4">
                  <h3 className="text-gray-400 font-medium mb-2">Masa Total</h3>
                  <div className="text-gray-300 space-y-1">
                    <p>
                      <span className="text-cyan-400">{massInfo.total_mass_kg.toFixed(1)}</span> kg
                    </p>
                    <p>
                      <span className="text-cyan-400">{massInfo.total_weight_kN.toFixed(2)}</span> kN
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      ({massInfo.frame_masses.length} frames)
                    </p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">
              Crea un proyecto para empezar
            </p>
          )}
        </aside>

        {/* 3D Viewport */}
        <main className="flex-1 relative">
          <Canvas
            camera={{ position: [10, 10, 10], fov: 50 }}
            className="bg-gray-950"
          >
            <Viewport />
          </Canvas>

          {/* Snap Settings Panel (overlay) */}
          {showSnapSettings && (
            <div className="absolute top-4 left-4 z-10">
              <SnapSettingsPanel />
              <button
                onClick={() => setShowSnapSettings(false)}
                className="mt-2 px-3 py-1 text-xs bg-gray-700 text-gray-300 rounded hover:bg-gray-600 w-full"
              >
                Cerrar
              </button>
            </div>
          )}
        </main>

        {/* Properties Panel */}
        <aside className="w-72 bg-gray-800 border-l border-gray-700 p-4 overflow-y-auto">
          <h2 className="text-white font-semibold mb-4">Propiedades</h2>
          {selectedNode ? (
            <div className="text-sm space-y-3">
              <h3 className="text-blue-400 font-medium">Node {selectedNode.id}</h3>
              <div className="space-y-2 text-gray-300">
                <p>X: {formatValue(lengthFromBase(selectedNode.x, units.length), 4)} {units.length}</p>
                <p>Y: {formatValue(lengthFromBase(selectedNode.y, units.length), 4)} {units.length}</p>
                <p>Z: {formatValue(lengthFromBase(selectedNode.z, units.length), 4)} {units.length}</p>
                <div className="pt-2 border-t border-gray-700">
                  <label className="text-gray-400 text-xs block mb-1">Tipo de Apoyo</label>
                  <select
                    value={selectedNode.restraint_type || 'free'}
                    onChange={(e) => updateNodeRestraint(selectedNode.id, e.target.value as RestraintType)}
                    className="w-full px-2 py-1 bg-gray-700 text-white rounded text-sm"
                  >
                    {(Object.keys(RESTRAINT_TYPE_LABELS) as RestraintType[]).map((type) => (
                      <option key={type} value={type}>
                        {RESTRAINT_TYPE_LABELS[type]}
                      </option>
                    ))}
                  </select>
                </div>
                {selectedNode.is_supported && (
                  <ul className="text-xs text-gray-400 ml-2 mt-2">
                    {selectedNode.restraint.ux && <li>Ux: Fixed</li>}
                    {selectedNode.restraint.uy && <li>Uy: Fixed</li>}
                    {selectedNode.restraint.uz && <li>Uz: Fixed</li>}
                    {selectedNode.restraint.rx && <li>Rx: Fixed</li>}
                    {selectedNode.restraint.ry && <li>Ry: Fixed</li>}
                    {selectedNode.restraint.rz && <li>Rz: Fixed</li>}
                  </ul>
                )}
              </div>
              <button
                onClick={() => deleteNode(selectedNode.id)}
                className="mt-4 px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Eliminar
              </button>
            </div>
          ) : selectedFrame ? (
            <div className="text-sm space-y-3">
              <h3 className="text-orange-400 font-medium">Frame {selectedFrame.id}</h3>
              <div className="space-y-2 text-gray-300">
                <p>Node I: {selectedFrame.node_i_id}</p>
                <p>Node J: {selectedFrame.node_j_id}</p>

                {/* Material selector */}
                <div>
                  <label className="text-gray-400 text-xs block mb-1">Material</label>
                  <select
                    value={selectedFrame.material_name}
                    onChange={(e) => updateFrame(selectedFrame.id, { material_name: e.target.value })}
                    className="w-full px-2 py-1 bg-gray-700 text-white rounded text-sm"
                    disabled={mode === 'analysis'}
                  >
                    {availableMaterials.map((mat) => (
                      <option key={mat} value={mat}>{mat}</option>
                    ))}
                  </select>
                </div>

                {/* Section selector */}
                <div>
                  <label className="text-gray-400 text-xs block mb-1">Sección</label>
                  <select
                    value={selectedFrame.section_name}
                    onChange={(e) => updateFrame(selectedFrame.id, { section_name: e.target.value })}
                    className="w-full px-2 py-1 bg-gray-700 text-white rounded text-sm"
                    disabled={mode === 'analysis'}
                  >
                    {availableSections.map((sec) => (
                      <option key={sec} value={sec}>{sec}</option>
                    ))}
                  </select>
                </div>

                <p>Rotation: {(selectedFrame.rotation * 180 / Math.PI).toFixed(1)}°</p>
              </div>

              {/* Releases Section */}
              <div className="pt-3 border-t border-gray-700">
                <h4 className="text-gray-400 text-xs font-medium mb-2">Releases (Articulaciones)</h4>

                {/* Preset selector */}
                <div className="mb-2">
                  <select
                    value={(() => {
                      const r = selectedFrame.releases || DEFAULT_RELEASES
                      if (!r.M2_i && !r.M3_i && !r.M2_j && !r.M3_j) return 'fixed_fixed'
                      if (r.M2_i && r.M3_i && r.M2_j && r.M3_j && !r.P_i && !r.P_j) return 'pinned_pinned'
                      if (!r.M2_i && !r.M3_i && r.M2_j && r.M3_j) return 'fixed_pinned'
                      if (r.M2_i && r.M3_i && !r.M2_j && !r.M3_j) return 'pinned_fixed'
                      return 'custom'
                    })()}
                    onChange={(e) => {
                      const preset = e.target.value as ReleasePreset
                      if (preset !== 'custom') {
                        updateFrame(selectedFrame.id, { releases: RELEASE_PRESETS[preset].releases })
                      }
                    }}
                    className="w-full px-2 py-1 bg-gray-700 text-white rounded text-xs"
                    disabled={mode === 'analysis'}
                  >
                    {(Object.keys(RELEASE_PRESETS) as ReleasePreset[]).map((preset) => (
                      <option key={preset} value={preset}>
                        {RELEASE_PRESETS[preset].label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Individual DOF releases */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {/* End i */}
                  <div className="bg-gray-700/50 p-2 rounded">
                    <p className="text-gray-400 font-medium mb-1">Extremo I</p>
                    {(['M2_i', 'M3_i', 'T_i'] as const).map((dof) => (
                      <label key={dof} className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedFrame.releases?.[dof] || false}
                          onChange={(e) => {
                            updateFrame(selectedFrame.id, {
                              releases: { ...selectedFrame.releases, [dof]: e.target.checked }
                            })
                          }}
                          disabled={mode === 'analysis'}
                          className="w-3 h-3"
                        />
                        <span className="text-gray-300">{dof.replace('_i', '')}</span>
                      </label>
                    ))}
                  </div>
                  {/* End j */}
                  <div className="bg-gray-700/50 p-2 rounded">
                    <p className="text-gray-400 font-medium mb-1">Extremo J</p>
                    {(['M2_j', 'M3_j', 'T_j'] as const).map((dof) => (
                      <label key={dof} className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedFrame.releases?.[dof] || false}
                          onChange={(e) => {
                            updateFrame(selectedFrame.id, {
                              releases: { ...selectedFrame.releases, [dof]: e.target.checked }
                            })
                          }}
                          disabled={mode === 'analysis'}
                          className="w-3 h-3"
                        />
                        <span className="text-gray-300">{dof.replace('_j', '')}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  M2/M3: momentos, T: torsión
                </p>
              </div>

              <button
                onClick={() => deleteFrame(selectedFrame.id)}
                className="mt-4 px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Eliminar
              </button>
            </div>
          ) : selectedShell ? (
            <div className="text-sm space-y-3">
              <h3 className="text-blue-400 font-medium">Shell {selectedShell.id}</h3>
              <div className="space-y-2 text-gray-300">
                <p>Nodos: {selectedShell.node_ids.join(', ')}</p>
                <p>Material: {selectedShell.material_name}</p>
                <p>Espesor: {selectedShell.thickness} {units.length}</p>
                <p>Tipo: {SHELL_TYPE_LABELS[selectedShell.shell_type]}</p>
                {selectedShell.label && <p>Etiqueta: {selectedShell.label}</p>}
              </div>
              <button
                onClick={() => deleteShell(selectedShell.id)}
                className="mt-4 px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Eliminar
              </button>
            </div>
          ) : selectedGroup ? (
            <div className="text-sm space-y-3">
              <h3 className="text-purple-400 font-medium flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: selectedGroup.color }}
                ></span>
                {selectedGroup.name}
              </h3>
              <div className="space-y-2 text-gray-300">
                <p>Elementos: {selectedGroup.element_count}</p>
                {selectedGroup.node_ids.length > 0 && (
                  <p>Nodos: {selectedGroup.node_ids.join(', ')}</p>
                )}
                {selectedGroup.frame_ids.length > 0 && (
                  <p>Frames: {selectedGroup.frame_ids.join(', ')}</p>
                )}
                {selectedGroup.shell_ids.length > 0 && (
                  <p>Shells: {selectedGroup.shell_ids.join(', ')}</p>
                )}
                {selectedGroup.description && (
                  <p className="text-gray-400">{selectedGroup.description}</p>
                )}
              </div>
              {/* Add selection to group button */}
              {(selectedNodeId || selectedFrameId || selectedShellId) && mode !== 'analysis' && (
                <button
                  onClick={() => addSelectionToGroup(selectedGroup.id)}
                  className="w-full px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700"
                >
                  Agregar seleccion al grupo
                </button>
              )}
              <button
                onClick={() => deleteGroup(selectedGroup.id)}
                className="w-full px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                disabled={mode === 'analysis'}
              >
                Eliminar grupo
              </button>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">
              Selecciona un elemento para ver sus propiedades
            </p>
          )}
        </aside>
      </div>

      {/* Status Bar */}
      <footer className="h-8 bg-gray-800 border-t border-gray-700 flex items-center px-4 text-xs text-gray-400">
        <span>{isLoading || isAnalyzing ? 'Procesando...' : error ? `Error: ${error}` : 'Listo'}</span>
        <div className="ml-auto flex items-center gap-3">
          {/* Drawing mode indicator */}
          {drawingMode.isActive && (
            <span className="px-2 py-0.5 rounded text-xs bg-cyan-600 text-white">
              DIBUJO {drawingMode.state === 'drawing' ? '(click para completar)' : '(click para iniciar)'}
            </span>
          )}
          {/* Snap indicator */}
          <button
            onClick={() => setShowSnapSettings(!showSnapSettings)}
            className={`px-2 py-0.5 rounded text-xs ${
              snapSettings.enabled
                ? 'bg-green-600 text-white'
                : 'bg-gray-600 text-gray-300'
            }`}
            title="F3 para activar/desactivar (click para configurar)"
          >
            SNAP {snapSettings.enabled ? 'ON' : 'OFF'}
          </button>
          <span>Unidades:</span>
          <select
            value={`${units.length}/${units.force}`}
            onChange={(e) => {
              const [length, force] = e.target.value.split('/') as [string, string]
              setUnits({ length: length as 'm' | 'ft', force: force as 'kN' | 'kip' | 'tonf' })
            }}
            className="bg-gray-700 text-gray-200 px-2 py-0.5 rounded text-xs"
          >
            <option value="m/kN">SI (m, kN)</option>
            <option value="ft/kip">Imperial (ft, kip)</option>
            <option value="m/tonf">Metric (m, tonf)</option>
          </select>
        </div>
      </footer>

      {/* New Project Modal */}
      {showNewProject && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-white font-semibold mb-4">Nuevo Proyecto</h2>
            <input
              type="text"
              placeholder="Nombre del proyecto"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 text-white rounded mb-4"
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowNewProject(false)}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreateProject}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Crear
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Node Modal */}
      {showAddNode && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-white font-semibold mb-4">Agregar Nodo</h2>
            <div className="space-y-3">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-gray-400 text-sm">X ({units.length})</label>
                  <input
                    type="number"
                    value={nodeX}
                    onChange={(e) => setNodeX(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-gray-400 text-sm">Y ({units.length})</label>
                  <input
                    type="number"
                    value={nodeY}
                    onChange={(e) => setNodeY(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-gray-400 text-sm">Z ({units.length})</label>
                  <input
                    type="number"
                    value={nodeZ}
                    onChange={(e) => setNodeZ(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  />
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-sm">Tipo de Apoyo</label>
                <select
                  value={nodeRestraintType}
                  onChange={(e) => setNodeRestraintType(e.target.value as RestraintType)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  {(Object.keys(RESTRAINT_TYPE_LABELS) as RestraintType[]).map((type) => (
                    <option key={type} value={type}>
                      {RESTRAINT_TYPE_LABELS[type]}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => setShowAddNode(false)}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddNode}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Agregar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Frame Modal */}
      {showAddFrame && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-white font-semibold mb-4">Agregar Frame</h2>
            <div className="space-y-3">
              <div>
                <label className="text-gray-400 text-sm">Nodo I</label>
                <select
                  value={frameNodeI}
                  onChange={(e) => setFrameNodeI(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  <option value="">Seleccionar...</option>
                  {nodes.map((node) => (
                    <option key={node.id} value={node.id}>
                      Node {node.id} ({node.x}, {node.y}, {node.z})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-gray-400 text-sm">Nodo J</label>
                <select
                  value={frameNodeJ}
                  onChange={(e) => setFrameNodeJ(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  <option value="">Seleccionar...</option>
                  {nodes
                    .filter((n) => n.id.toString() !== frameNodeI)
                    .map((node) => (
                      <option key={node.id} value={node.id}>
                        Node {node.id} ({node.x}, {node.y}, {node.z})
                      </option>
                    ))}
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => setShowAddFrame(false)}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddFrame}
                className="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
                disabled={!frameNodeI || !frameNodeJ}
              >
                Agregar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Load Modal */}
      {showAddLoad && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-white font-semibold mb-4">Agregar Carga Nodal</h2>
            <div className="space-y-3">
              <div>
                <label className="text-gray-400 text-sm">Nodo</label>
                <select
                  value={loadNodeId}
                  onChange={(e) => setLoadNodeId(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  <option value="">Seleccionar...</option>
                  {nodes.filter((n) => !n.is_supported).map((node) => (
                    <option key={node.id} value={node.id}>
                      Node {node.id} ({node.x}, {node.y}, {node.z})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-gray-400 text-sm">Fx ({units.force})</label>
                  <input
                    type="number"
                    value={loadFx}
                    onChange={(e) => setLoadFx(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-gray-400 text-sm">Fy ({units.force})</label>
                  <input
                    type="number"
                    value={loadFy}
                    onChange={(e) => setLoadFy(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-gray-400 text-sm">Fz ({units.force})</label>
                  <input
                    type="number"
                    value={loadFz}
                    onChange={(e) => setLoadFz(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  />
                </div>
              </div>
              <p className="text-xs text-gray-500">
                Fz negativo = hacia abajo (gravedad)
              </p>
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => setShowAddLoad(false)}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddLoad}
                className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
                disabled={!loadNodeId}
              >
                Agregar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Distributed Load Modal */}
      {showAddDistLoad && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-white font-semibold mb-4">Agregar Carga Distribuida</h2>
            <div className="space-y-3">
              <div>
                <label className="text-gray-400 text-sm">Frame</label>
                <select
                  value={distLoadFrameId}
                  onChange={(e) => setDistLoadFrameId(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  <option value="">Seleccionar...</option>
                  {frames.map((frame) => (
                    <option key={frame.id} value={frame.id}>
                      Frame {frame.id} (N{frame.node_i_id} → N{frame.node_j_id})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-gray-400 text-sm">Tipo de Carga</label>
                <select
                  value={distLoadType}
                  onChange={(e) => setDistLoadType(e.target.value as 'uniform' | 'triangular' | 'trapezoidal')}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  <option value="uniform">Uniforme</option>
                  <option value="triangular">Triangular (0 → w)</option>
                  <option value="trapezoidal">Trapezoidal (w₁ → w₂)</option>
                </select>
              </div>
              <div>
                <label className="text-gray-400 text-sm">
                  {distLoadType === 'trapezoidal' ? 'w₁ (inicio)' : 'Intensidad w'} ({units.force}/{units.length})
                </label>
                <input
                  type="number"
                  value={distLoadW}
                  onChange={(e) => setDistLoadW(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  step="0.1"
                />
              </div>
              {distLoadType === 'trapezoidal' && (
                <div>
                  <label className="text-gray-400 text-sm">w₂ (final) ({units.force}/{units.length})</label>
                  <input
                    type="number"
                    value={distLoadWEnd}
                    onChange={(e) => setDistLoadWEnd(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                    step="0.1"
                  />
                </div>
              )}
              <div>
                <label className="text-gray-400 text-sm">Dirección</label>
                <select
                  value={distLoadDirection}
                  onChange={(e) => setDistLoadDirection(e.target.value as LoadDirection)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  {Object.entries(LOAD_DIRECTION_LABELS).map(([value, label]) => (
                    <option key={value} value={label}>{/* Fixed: should use value not label */}
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-gray-500">
                {distLoadType === 'uniform' && 'Carga constante sobre toda la longitud del frame'}
                {distLoadType === 'triangular' && 'Carga que varía de 0 a w (inicio a fin)'}
                {distLoadType === 'trapezoidal' && 'Carga que varía de w₁ a w₂ (inicio a fin)'}
              </p>
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => setShowAddDistLoad(false)}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddDistLoad}
                className="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
                disabled={!distLoadFrameId}
              >
                Agregar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Results Modal */}
      {showResults && analysisResults && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-[600px] max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-white font-semibold">Resultados del Análisis</h2>
              <button
                onClick={() => setShowResults(false)}
                className="text-gray-400 hover:text-white text-xl"
              >
                ×
              </button>
            </div>

            {analysisResults.success ? (
              <div className="space-y-4">
                {/* Summary */}
                <div className="bg-green-900/30 border border-green-700 rounded p-3">
                  <p className="text-green-400 font-medium">Análisis exitoso</p>
                  <p className="text-sm text-gray-300">
                    Desplazamiento máximo: {(analysisResults.max_displacement * 1000).toFixed(3)} mm
                  </p>
                </div>

                {/* Displacements */}
                <div>
                  <h3 className="text-blue-400 font-medium mb-2">Desplazamientos</h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-gray-400 border-b border-gray-700">
                        <th className="text-left py-1">Nodo</th>
                        <th className="text-right py-1">Ux ({units.length === 'm' ? 'mm' : units.length})</th>
                        <th className="text-right py-1">Uy ({units.length === 'm' ? 'mm' : units.length})</th>
                        <th className="text-right py-1">Uz ({units.length === 'm' ? 'mm' : units.length})</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysisResults.displacements.map((d) => (
                        <tr key={d.node_id} className="text-gray-300 border-b border-gray-700/50">
                          <td className="py-1">{d.node_id}</td>
                          <td className="text-right">{formatValue(lengthFromBase(d.Ux, units.length === 'm' ? 'mm' : units.length), 3)}</td>
                          <td className="text-right">{formatValue(lengthFromBase(d.Uy, units.length === 'm' ? 'mm' : units.length), 3)}</td>
                          <td className="text-right">{formatValue(lengthFromBase(d.Uz, units.length === 'm' ? 'mm' : units.length), 3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Reactions */}
                <div>
                  <h3 className="text-orange-400 font-medium mb-2">Reacciones</h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-gray-400 border-b border-gray-700">
                        <th className="text-left py-1">Nodo</th>
                        <th className="text-right py-1">Fx ({units.force})</th>
                        <th className="text-right py-1">Fy ({units.force})</th>
                        <th className="text-right py-1">Fz ({units.force})</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysisResults.reactions.map((r) => (
                        <tr key={r.node_id} className="text-gray-300 border-b border-gray-700/50">
                          <td className="py-1">{r.node_id}</td>
                          <td className="text-right">{formatValue(forceFromBase(r.Fx, units.force), 2)}</td>
                          <td className="text-right">{formatValue(forceFromBase(r.Fy, units.force), 2)}</td>
                          <td className="text-right">{formatValue(forceFromBase(r.Fz, units.force), 2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Frame Forces */}
                {analysisResults.frame_results && analysisResults.frame_results.length > 0 && (
                  <div>
                    <h3 className="text-purple-400 font-medium mb-2">Esfuerzos en Frames</h3>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-400 border-b border-gray-700">
                          <th className="text-left py-1">Frame</th>
                          <th className="text-right py-1">P max ({units.force})</th>
                          <th className="text-right py-1">P min ({units.force})</th>
                          <th className="text-right py-1">V max ({units.force})</th>
                          <th className="text-right py-1">M max ({getMomentLabel(units.force, units.length)})</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysisResults.frame_results.map((fr) => (
                          <tr key={fr.frame_id} className="text-gray-300 border-b border-gray-700/50">
                            <td className="py-1">F{fr.frame_id}</td>
                            <td className="text-right">{formatValue(forceFromBase(fr.P_max, units.force), 2)}</td>
                            <td className="text-right">{formatValue(forceFromBase(fr.P_min, units.force), 2)}</td>
                            <td className="text-right">{formatValue(forceFromBase(fr.V_max || Math.max(fr.V2_max, fr.V3_max || 0), units.force), 2)}</td>
                            <td className="text-right">{formatValue(momentFromBase(fr.M_max || Math.max(fr.M2_max || 0, fr.M3_max), units.force, units.length), 2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-red-900/30 border border-red-700 rounded p-3">
                <p className="text-red-400 font-medium">Error en el análisis</p>
                <p className="text-sm text-gray-300">{analysisResults.error_message}</p>
              </div>
            )}

            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => {
                  clearResults()
                  setShowResults(false)
                }}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Limpiar Resultados
              </button>
              <button
                onClick={() => setShowResults(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Section Modal */}
      {showCreateSection && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-white font-semibold mb-4">Crear Sección Parametrizada</h2>
            <div className="space-y-3">
              <div>
                <label className="text-gray-400 text-sm">Nombre</label>
                <input
                  type="text"
                  value={sectionName}
                  onChange={(e) => setSectionName(e.target.value)}
                  placeholder="Ej: Rect300x500"
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                />
              </div>
              <div>
                <label className="text-gray-400 text-sm">Tipo de sección</label>
                <select
                  value={sectionShape}
                  onChange={(e) => setSectionShape(e.target.value as 'Rectangular' | 'Circular' | 'IShape')}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  <option value="Rectangular">Rectangular</option>
                  <option value="Circular">Circular</option>
                  <option value="IShape">Perfil I</option>
                </select>
              </div>

              {sectionShape === 'Rectangular' && (
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="text-gray-400 text-sm">Ancho ({units.length})</label>
                    <input
                      type="number"
                      value={sectionWidth}
                      onChange={(e) => setSectionWidth(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-gray-400 text-sm">Alto ({units.length})</label>
                    <input
                      type="number"
                      value={sectionHeight}
                      onChange={(e) => setSectionHeight(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                    />
                  </div>
                </div>
              )}

              {sectionShape === 'Circular' && (
                <div>
                  <label className="text-gray-400 text-sm">Radio ({units.length})</label>
                  <input
                    type="number"
                    value={sectionRadius}
                    onChange={(e) => setSectionRadius(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  />
                </div>
              )}

              {sectionShape === 'IShape' && (
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <label className="text-gray-400 text-sm">d - Altura ({units.length})</label>
                      <input
                        type="number"
                        value={sectionD}
                        onChange={(e) => setSectionD(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-gray-400 text-sm">bf - Ancho ala ({units.length})</label>
                      <input
                        type="number"
                        value={sectionBf}
                        onChange={(e) => setSectionBf(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <label className="text-gray-400 text-sm">tf - Esp. ala ({units.length})</label>
                      <input
                        type="number"
                        value={sectionTf}
                        onChange={(e) => setSectionTf(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-gray-400 text-sm">tw - Esp. alma ({units.length})</label>
                      <input
                        type="number"
                        value={sectionTw}
                        onChange={(e) => setSectionTw(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => setShowCreateSection(false)}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreateSection}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-500"
                disabled={!sectionName.trim()}
              >
                Crear
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Settings Modal */}
      {showViewSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-white font-semibold mb-4">Configuración de Vista</h2>
            <div className="space-y-4">
              {/* Extruded Profiles Toggle */}
              <div>
                <label className="flex items-center text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={viewOptions.showExtrudedProfiles}
                    onChange={(e) => setViewOptions({ showExtrudedProfiles: e.target.checked })}
                    className="mr-3 w-4 h-4"
                  />
                  Mostrar perfiles extruidos (3D)
                </label>
              </div>

              {/* Reactions Toggle */}
              <div>
                <label className="flex items-center text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={viewOptions.showReactions}
                    onChange={(e) => setViewOptions({ showReactions: e.target.checked })}
                    className="mr-3 w-4 h-4"
                  />
                  Mostrar reacciones (flechas verdes)
                </label>
              </div>

              {/* Diagram Type */}
              <div>
                <label className="text-gray-400 text-sm block mb-2">Diagrama de Esfuerzos</label>
                <select
                  value={viewOptions.diagramType}
                  onChange={(e) => setViewOptions({ diagramType: e.target.value as DiagramType })}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  <option value="none">Sin diagrama</option>
                  <option value="axial">Fuerza Axial (P)</option>
                  <option value="shear">Corte (V)</option>
                  <option value="moment">Momento (M)</option>
                </select>
              </div>

              {/* Diagram Scale */}
              {viewOptions.diagramType !== 'none' && (
                <div>
                  <label className="text-gray-400 text-sm block mb-2">
                    Escala del Diagrama: {viewOptions.diagramScale.toFixed(1)}x
                  </label>
                  <input
                    type="range"
                    min="0.1"
                    max="5"
                    step="0.1"
                    value={viewOptions.diagramScale}
                    onChange={(e) => setViewOptions({ diagramScale: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>
              )}

              <hr className="border-gray-700" />

              {/* Grid Settings */}
              <div>
                <h3 className="text-gray-300 font-medium mb-3">Grilla</h3>

                <label className="flex items-center text-gray-300 cursor-pointer mb-3">
                  <input
                    type="checkbox"
                    checked={gridSettings.visible}
                    onChange={(e) => setGridSettings({ visible: e.target.checked })}
                    className="mr-3 w-4 h-4"
                  />
                  Mostrar grilla
                </label>

                <div className="flex gap-3 mb-3">
                  <div className="flex-1">
                    <label className="text-gray-400 text-sm">Espaciado ({units.length})</label>
                    <input
                      type="number"
                      min="0.1"
                      step="0.5"
                      value={gridSettings.spacing}
                      onChange={(e) => setGridSettings({ spacing: parseFloat(e.target.value) || 1 })}
                      className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-gray-400 text-sm">Tamaño ({units.length})</label>
                    <input
                      type="number"
                      min="5"
                      step="5"
                      value={gridSettings.size}
                      onChange={(e) => setGridSettings({ size: parseFloat(e.target.value) || 20 })}
                      className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                    />
                  </div>
                </div>

                <label className="flex items-center text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={gridSettings.snap}
                    onChange={(e) => setGridSettings({ snap: e.target.checked })}
                    className="mr-3 w-4 h-4"
                  />
                  Snap a grilla (futuro)
                </label>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <button
                onClick={() => setShowViewSettings(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Shell Modal */}
      {showAddShell && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-white font-semibold mb-4">Agregar Shell (Losa/Muro)</h2>
            <div className="space-y-3">
              <p className="text-gray-400 text-sm">
                Selecciona 3 o 4 nodos que definen las esquinas del shell.
                El orden debe ser antihorario visto desde arriba.
              </p>
              <div className="grid grid-cols-2 gap-2">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i}>
                    <label className="text-gray-400 text-sm">
                      Nodo {i + 1} {i < 3 ? '*' : '(opcional)'}
                    </label>
                    <select
                      value={shellNodes[i]}
                      onChange={(e) => {
                        const newNodes = [...shellNodes]
                        newNodes[i] = e.target.value
                        setShellNodes(newNodes)
                      }}
                      className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                    >
                      <option value="">Seleccionar...</option>
                      {nodes
                        .filter((n) => !shellNodes.filter((_, idx) => idx !== i).includes(n.id.toString()))
                        .map((node) => (
                          <option key={node.id} value={node.id}>
                            N{node.id} ({node.x}, {node.y}, {node.z})
                          </option>
                        ))}
                    </select>
                  </div>
                ))}
              </div>
              <div>
                <label className="text-gray-400 text-sm">Espesor ({units.length})</label>
                <input
                  type="number"
                  value={shellThickness}
                  onChange={(e) => setShellThickness(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  step="0.01"
                  min="0.01"
                />
              </div>
              <div>
                <label className="text-gray-400 text-sm">Tipo de Shell</label>
                <select
                  value={shellType}
                  onChange={(e) => setShellType(e.target.value as ShellType)}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                >
                  {(Object.keys(SHELL_TYPE_LABELS) as ShellType[]).map((type) => (
                    <option key={type} value={type}>
                      {SHELL_TYPE_LABELS[type]}
                    </option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-gray-500">
                * Shell: comportamiento de placa + membrana (losas, muros)
                <br />* Placa: solo flexión (losas delgadas)
                <br />* Membrana: solo fuerzas en plano (muros de corte)
              </p>
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => {
                  setShowAddShell(false)
                  setShellNodes(['', '', '', ''])
                }}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddShell}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                disabled={shellNodes.filter((n) => n !== '').length < 3}
              >
                Agregar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Group Dialog */}
      {showAddGroup && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-80">
            <h2 className="text-white font-semibold mb-4">Crear Grupo</h2>
            <div className="space-y-3">
              <div>
                <label className="text-gray-400 text-sm">Nombre del grupo</label>
                <input
                  type="text"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="Ej: Vigas principales"
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded"
                  autoFocus
                />
              </div>
              <p className="text-gray-400 text-xs">
                Despues de crear el grupo, selecciona elementos y usa "Agregar seleccion al grupo" para incluirlos.
              </p>
            </div>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => {
                  setShowAddGroup(false)
                  setNewGroupName('')
                }}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                onClick={async () => {
                  if (newGroupName.trim()) {
                    await addGroup(newGroupName.trim())
                    setNewGroupName('')
                    setShowAddGroup(false)
                  }
                }}
                className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
                disabled={!newGroupName.trim()}
              >
                Crear
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
