/**
 * Unit conversion service.
 * All internal values are stored in SI base units (m, kN).
 * This service converts to/from display units.
 */

export type LengthUnit = 'm' | 'cm' | 'mm' | 'ft' | 'in'
export type ForceUnit = 'kN' | 'N' | 'kgf' | 'tonf' | 'kip' | 'lbf'

export interface UnitSystem {
  length: LengthUnit
  force: ForceUnit
}

// Conversion factors TO base units (m, kN)
const LENGTH_TO_M: Record<LengthUnit, number> = {
  m: 1,
  cm: 0.01,
  mm: 0.001,
  ft: 0.3048,
  in: 0.0254,
}

const FORCE_TO_KN: Record<ForceUnit, number> = {
  kN: 1,
  N: 0.001,
  kgf: 0.00980665,
  tonf: 9.80665,
  kip: 4.44822,
  lbf: 0.00444822,
}

// Conversion factors FROM base units (m, kN)
const M_TO_LENGTH: Record<LengthUnit, number> = {
  m: 1,
  cm: 100,
  mm: 1000,
  ft: 3.28084,
  in: 39.3701,
}

const KN_TO_FORCE: Record<ForceUnit, number> = {
  kN: 1,
  N: 1000,
  kgf: 101.972,
  tonf: 0.101972,
  kip: 0.224809,
  lbf: 224.809,
}

/**
 * Convert length from display units to base units (m).
 */
export function lengthToBase(value: number, unit: LengthUnit): number {
  return value * LENGTH_TO_M[unit]
}

/**
 * Convert length from base units (m) to display units.
 */
export function lengthFromBase(value: number, unit: LengthUnit): number {
  return value * M_TO_LENGTH[unit]
}

/**
 * Convert force from display units to base units (kN).
 */
export function forceToBase(value: number, unit: ForceUnit): number {
  return value * FORCE_TO_KN[unit]
}

/**
 * Convert force from base units (kN) to display units.
 */
export function forceFromBase(value: number, unit: ForceUnit): number {
  return value * KN_TO_FORCE[unit]
}

/**
 * Convert distributed load from display units to base units (kN/m).
 */
export function distLoadToBase(value: number, forceUnit: ForceUnit, lengthUnit: LengthUnit): number {
  // kN/m = (force in kN) / (length in m)
  const forceInKN = forceToBase(value, forceUnit)
  const lengthFactor = LENGTH_TO_M[lengthUnit] // 1m in display units
  return forceInKN / lengthFactor
}

/**
 * Convert distributed load from base units (kN/m) to display units.
 */
export function distLoadFromBase(value: number, forceUnit: ForceUnit, lengthUnit: LengthUnit): number {
  const forceInDisplay = forceFromBase(value, forceUnit)
  const lengthFactor = LENGTH_TO_M[lengthUnit]
  return forceInDisplay * lengthFactor
}

/**
 * Convert moment from display units to base units (kN·m).
 */
export function momentToBase(value: number, forceUnit: ForceUnit, lengthUnit: LengthUnit): number {
  return forceToBase(value, forceUnit) * LENGTH_TO_M[lengthUnit]
}

/**
 * Convert moment from base units (kN·m) to display units.
 */
export function momentFromBase(value: number, forceUnit: ForceUnit, lengthUnit: LengthUnit): number {
  return forceFromBase(value, forceUnit) * M_TO_LENGTH[lengthUnit]
}

/**
 * Convert stress/pressure from display units to base units (kPa = kN/m²).
 */
export function stressToBase(value: number, forceUnit: ForceUnit, lengthUnit: LengthUnit): number {
  const forceInKN = forceToBase(value, forceUnit)
  const lengthInM = LENGTH_TO_M[lengthUnit]
  return forceInKN / (lengthInM * lengthInM)
}

/**
 * Convert stress/pressure from base units (kPa) to display units.
 */
export function stressFromBase(value: number, forceUnit: ForceUnit, lengthUnit: LengthUnit): number {
  const forceInDisplay = forceFromBase(value, forceUnit)
  const lengthInM = LENGTH_TO_M[lengthUnit]
  return forceInDisplay * (lengthInM * lengthInM)
}

/**
 * Format a number with appropriate precision.
 */
export function formatValue(value: number, decimals: number = 3): string {
  if (Math.abs(value) < 0.0001) return '0'
  if (Math.abs(value) >= 1000) return value.toFixed(1)
  if (Math.abs(value) >= 1) return value.toFixed(decimals)
  return value.toFixed(decimals + 1)
}

/**
 * Get display label for combined units.
 */
export function getDistLoadLabel(forceUnit: ForceUnit, lengthUnit: LengthUnit): string {
  return `${forceUnit}/${lengthUnit}`
}

export function getMomentLabel(forceUnit: ForceUnit, lengthUnit: LengthUnit): string {
  return `${forceUnit}·${lengthUnit}`
}

export function getStressLabel(forceUnit: ForceUnit, lengthUnit: LengthUnit): string {
  return `${forceUnit}/${lengthUnit}²`
}

/**
 * Unit presets.
 */
export const UNIT_PRESETS = {
  SI: { length: 'm' as LengthUnit, force: 'kN' as ForceUnit },
  SI_N: { length: 'm' as LengthUnit, force: 'N' as ForceUnit },
  Metric_tonf: { length: 'm' as LengthUnit, force: 'tonf' as ForceUnit },
  Imperial: { length: 'ft' as LengthUnit, force: 'kip' as ForceUnit },
  Imperial_lbf: { length: 'in' as LengthUnit, force: 'lbf' as ForceUnit },
}
