/**
 * SnapSettingsPanel - Panel for configuring snap options.
 * Allows users to enable/disable individual snap types.
 */

import { useStore } from '../store/useStore'
import { SnapType, SNAP_TYPE_LABELS, SNAP_TYPE_SYMBOLS } from '../services/SnapService'

// All snap types in display order
const SNAP_TYPES: SnapType[] = [
  'node',
  'endpoint',
  'midpoint',
  'grid',
  'perpendicular',
  'intersection',
]

function SnapSettingsPanel() {
  const snapSettings = useStore((state) => state.snapSettings)
  const toggleSnap = useStore((state) => state.toggleSnap)
  const toggleSnapType = useStore((state) => state.toggleSnapType)
  const setSnapSettings = useStore((state) => state.setSnapSettings)

  return (
    <div style={{
      backgroundColor: '#1a1a2e',
      border: '1px solid #333355',
      borderRadius: '8px',
      padding: '12px',
      width: '200px',
    }}>
      {/* Header with global toggle */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        paddingBottom: '8px',
        borderBottom: '1px solid #333355',
      }}>
        <span style={{
          color: '#fff',
          fontWeight: 'bold',
          fontSize: '14px',
        }}>
          Object Snap
        </span>
        <button
          onClick={toggleSnap}
          style={{
            padding: '4px 8px',
            backgroundColor: snapSettings.enabled ? '#4CAF50' : '#666',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '11px',
          }}
        >
          {snapSettings.enabled ? 'ON' : 'OFF'}
        </button>
      </div>

      {/* Shortcut hint */}
      <div style={{
        color: '#888',
        fontSize: '11px',
        marginBottom: '12px',
      }}>
        Atajo: F3 para activar/desactivar
      </div>

      {/* Snap type toggles */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        opacity: snapSettings.enabled ? 1 : 0.5,
      }}>
        {SNAP_TYPES.map((type) => (
          <label
            key={type}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: snapSettings.enabled ? 'pointer' : 'not-allowed',
              padding: '4px',
              borderRadius: '4px',
              backgroundColor: snapSettings.activeSnaps[type] ? '#2a2a4e' : 'transparent',
            }}
          >
            <input
              type="checkbox"
              checked={snapSettings.activeSnaps[type]}
              onChange={() => toggleSnapType(type)}
              disabled={!snapSettings.enabled}
              style={{ cursor: snapSettings.enabled ? 'pointer' : 'not-allowed' }}
            />
            <span style={{
              color: '#aaa',
              fontSize: '16px',
              width: '20px',
              textAlign: 'center',
            }}>
              {SNAP_TYPE_SYMBOLS[type]}
            </span>
            <span style={{
              color: '#ddd',
              fontSize: '12px',
            }}>
              {SNAP_TYPE_LABELS[type]}
            </span>
          </label>
        ))}
      </div>

      {/* Threshold slider */}
      <div style={{ marginTop: '12px', paddingTop: '8px', borderTop: '1px solid #333355' }}>
        <label style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
        }}>
          <span style={{ color: '#aaa', fontSize: '11px' }}>
            Distancia snap: {snapSettings.threshold.toFixed(2)}m
          </span>
          <input
            type="range"
            min="0.1"
            max="2"
            step="0.1"
            value={snapSettings.threshold}
            onChange={(e) => setSnapSettings({ threshold: parseFloat(e.target.value) })}
            disabled={!snapSettings.enabled}
            style={{ width: '100%' }}
          />
        </label>
      </div>
    </div>
  )
}

export default SnapSettingsPanel
