# RETOMAR.md

> Lee este archivo primero si eres una IA nueva retomando este proyecto.

---

## PROYECTO
**Nombre**: NIFES STRUCS (Software Profesional de Analisis Estructural)
**Estado**: en progreso (V1.0 - 9/18 features - 50%)
**Ultima actividad**: 2026-01-19 20:30

---

## LEER PRIMERO

1. `CLAUDE.md` - Instrucciones y reglas del proyecto
2. `PRD.md` - Product Requirements Document (v2.0)
3. `BRIEF.md` - Vision y objetivos del proyecto
4. `feature_list_v1.json` - Lista de 18 features V1.0

---

## ESTADO ACTUAL

**Modo**: automatico (feature_list_v1.json)
**Progreso**: 9/18 features V1.0 completadas (50%)

### Proxima tarea
**F44 - Combinaciones de Carga**: Casos de carga tipificados (DEAD, LIVE, SEISMIC), combinaciones por normativa (NCh, AISC, Eurocodigo), envolventes de resultados.

---

## BITACORA DE SESIONES

### Sesion 2026-01-19 (20:00 - 20:30)

**Problema**: Los diagramas de momento no se visualizaban correctamente.

**Diagnostico**:
1. OpenSees con `elasticBeamColumn` solo devuelve fuerzas en los **extremos** del elemento (nodo i y j)
2. La interpolacion inicial tenia errores matematicos
3. El vector perpendicular para visualizacion estaba mal calculado para frames verticales
4. Los valores de momento tenian signo incorrecto para visualizacion

**Solucion implementada**:

1. **Backend - Interpolacion analitica** (`analysis_service.py`):
   - Funcion `_enrich_frame_results_with_diagrams()` calcula 21 puntos intermedios
   - Usa la relacion fundamental: **dM/dx = V**
   - Formula: `M(x) = M_i + V_i*x + (V_j - V_i)*x²/(2L)`
   - Esto es **exacto** para analisis lineal elastico (no es aproximacion)

2. **Backend - Valores con signo** (`frame_results.py`):
   - `V_max`, `M_max` ahora devuelven el valor con signo (max por valor absoluto)
   - Antes: `max(abs(f.M2) for f in forces)` = 75
   - Ahora: `max((f.M2 for f in forces), key=abs)` = -75

3. **Frontend - Visualizacion** (`Viewport.tsx`):
   - Vector perpendicular: vertical (Y) para vigas, hacia observador (Z) para columnas
   - Momento negado para dibujar del lado de tension (convencion de ingenieria)

4. **Backend - CORS** (`main.py`):
   - Agregados puertos 3002, 3003 a origenes permitidos

**Decision tecnica importante**:
> Para analisis lineal elastico, la interpolacion matematica M = M_i + integral(V)dx es **exacta**.
> No es necesario dividir elementos o usar puntos de integracion adicionales de OpenSees.
> Esto seria diferente para analisis no-lineal donde la distribucion de fuerzas no sigue la teoria elastica.

**Archivos modificados**:
- `backend/src/paz/application/services/analysis_service.py` - Interpolacion analitica
- `backend/src/paz/infrastructure/engines/results_parser.py` - Solo extremos
- `backend/src/paz/domain/results/frame_results.py` - Valores con signo
- `backend/src/paz/api/main.py` - CORS ports
- `frontend/src/components/Viewport.tsx` - Vector perpendicular y signo momento

---

### Sesion 2026-01-18

**Features completadas:**
- F24 - Releases en Frames (TclWriter con zeroLength, UI presets, 7 tests)
- F25 - Grupos de Elementos (ElementGroup dataclass, API CRUD, store, UI, 46 tests)

**Bugs arreglados en revision 50%:**

| Bug | Solucion |
|-----|----------|
| Esfuerzos frames mostraban 0 | V_max y M_max ahora incluyen V2/V3 y M2/M3 (ambos ejes locales) |
| Sin visualizacion de reacciones | Agregado ReactionArrow component con flechas verdes en 3D |
| Unidades solo cambian etiquetas | Implementado UnitService.ts con conversion bidireccional real |
| Falta boton carga distribuida | Agregado boton "+ Dist." en toolbar |
| Cargas dist. no visibles en sidebar | Agregado visor de cargas distribuidas con valores |
| No se puede cambiar seccion a frames | Agregado selector material/seccion en panel propiedades |

---

## DECISIONES IMPORTANTES

1. **Nombre**: NIFES STRUCS (marca Nifes)
2. **Motor calculo**: OpenSees binario (no openseespy) - funciona en Mac ARM
3. **Arquitectura**: Cloud-first (React + FastAPI)
4. **Unidades internas**: Siempre SI (m, kN) - conversion solo para display
5. **Normativas**: NCh, AISC, Eurocodigos
6. **Diagramas de momento**: Interpolacion analitica exacta (dM/dx = V), no requiere subdividir elementos
7. **Convencion de signos**: Momento se muestra del lado de tension (negado en visualizacion)

---

## CONVERSION DE UNIDADES

El sistema soporta conversion real de unidades:

```typescript
// Unidades base (internas): m, kN
// Unidades display: configurable por usuario

// Al MOSTRAR valores:
lengthFromBase(valor_en_m, units.length)  // m -> ft/in/cm/mm
forceFromBase(valor_en_kN, units.force)   // kN -> kip/lbf/N/tonf

// Al INGRESAR valores:
lengthToBase(valor_input, units.length)   // ft/in/cm/mm -> m
forceToBase(valor_input, units.force)     // kip/lbf/N/tonf -> kN
```

Archivo: `frontend/src/services/UnitService.ts`

---

## FEATURES V1.0

### Completadas (9/18)
| ID | Feature | Fecha |
|----|---------|-------|
| F39 | Tipos de Apoyo Avanzados | 2026-01-13 |
| F40 | Cargas Avanzadas | 2026-01-16 |
| F41 | Mass Source y Masa Automatica | 2026-01-16 |
| F42 | Modo Dibujo/Analisis | 2026-01-16 |
| F43 | Object Snap | 2026-01-16 |
| F23 | Dibujo Dinamico | 2026-01-16 |
| F03 | Shells (losas, muros) | 2026-01-17 |
| F24 | Releases en Frames | 2026-01-18 |
| F25 | Grupos de Elementos | 2026-01-18 |

### Pendientes (9/18)
| # | ID | Feature | Complejidad |
|---|-----|---------|-------------|
| 10 | F44 | Combinaciones de Carga | Alta |
| 11 | F14 | Analisis Dinamico Modal | Alta |
| 12 | F17 | Visualizacion Modos | Media |
| 13 | F22 | Animacion de Modos | Media |
| 14 | F20 | Factores de Utilizacion | Alta |
| 15 | F10 | Secciones NCh | Media |
| 16 | F11 | Secciones Eurocodigo | Media |
| 17 | F45 | Import SAP2000 | Alta |
| 18 | F-V1-FINAL | Integracion V1.0 | Alta |

---

## COMO CONTINUAR

### Comandos frecuentes
```bash
# Backend
cd backend && uvicorn src.paz.api.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Tests
cd backend && python3 -m pytest
```

### Para implementar F44 (Combinaciones de Carga)
1. Crear `LoadCaseType` enum: DEAD, LIVE, WIND, SEISMIC, etc.
2. Crear presets por normativa en `code_combinations.py`
3. Actualizar AnalysisService para multiples casos
4. UI para gestionar casos y combinaciones
5. Calcular envolventes de resultados
6. Tests unitarios

### Flujo general V1.0
1. Implementar features en orden del feature_list_v1.json
2. Al 100% -> F-V1-FINAL para integracion

---

*Generado: 2026-01-19 20:30*
*Proyecto: NIFES STRUCS V1.0*
