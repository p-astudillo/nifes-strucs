# RETOMAR.md

> Lee este archivo primero si eres una IA nueva retomando este proyecto.

---

## PROYECTO
**Nombre**: PAZ (Software Profesional de Análisis Estructural)
**Estado**: en progreso
**Última actividad**: 2026-01-10 18:30

---

## LEER PRIMERO

1. `CLAUDE.md` - Instrucciones y reglas del proyecto
2. `ARQUITECTURA.md` - Stack técnico y estructura
3. `BRIEF.md` - Visión y objetivos

---

## ESTADO ACTUAL

**Modo**: automático (feature_list.json)
**Progreso**: 16/18 features completadas (89%)
**Tests**: ~500 tests pasando

| Feature | Nombre | Estado |
|---------|--------|--------|
| F00 | Setup del Proyecto | ✅ |
| F31 | Gestión de Proyectos | ✅ |
| F01 | Modelación de Nodos | ✅ |
| F08 | Librería de Materiales | ✅ |
| F09 | Librería de Secciones AISC | ✅ |
| F12 | Perfiles Parametrizados | ✅ |
| F02 | Modelación de Frames | ✅ |
| F13 | Análisis Estático Lineal | ✅ |
| F18 | Visualización Desplazamientos | ✅ |
| F19 | Visualización Esfuerzos | ✅ |
| F21 | Perfiles Extruidos | ✅ |
| F35 | Sistema de Grillas | ✅ |
| F33 | Export/Import | ✅ |
| F36 | Section Designer | ✅ |
| F37 | Conversor de Unidades | ✅ |
| F38 | Compatibilidad macOS | ✅ |
| F-UI | Interfaz Usuario | 🔄 en progreso |
| F-FINAL | Integración Final | ❌ pendiente |

### Última sesión (2026-01-10)

**4 Features completadas:**

1. **F33 - Export/Import** (34 tests)
   - `infrastructure/exporters/csv_exporter.py` - CSVExporter, ResultsExporter
   - `infrastructure/importers/csv_importer.py` - CSVImporter
   - `infrastructure/importers/dxf_importer.py` - DXFImporter (AutoCAD)
   - Dependencia agregada: `ezdxf>=1.0.0`

2. **F36 - Section Designer** (20 tests)
   - `domain/sections/section_designer.py` - SectionDesigner, SectionRegion
   - Funciones: `create_double_angle()`, `create_built_up_section()`
   - Soporta: rectangles, circles, I-shapes, polygons, composites

3. **F37 - Conversor de Unidades** (35 tests)
   - `core/units.py` ampliado con: area, inertia, section_modulus, linear_load
   - Funciones rápidas: `m_to_ft()`, `kN_to_kip()`, `deg_to_rad()`, etc.

4. **F38 - Compatibilidad macOS** (19 tests)
   - `core/platform.py` - Detección de plataforma y dependencias
   - Soporta: macOS (Intel + Apple Silicon), Windows, Linux
   - Verifica: OpenSees, Qt, PyVista, NumPy

**También iniciado: F-UI**
   - `presentation/main_window.py` - MainWindow con toolbar y viewport
   - Herramientas: Select (V), Node (N), Frame (F)
   - Undo/Redo funcional

### Próxima tarea
- **F-UI (continuar)**: Diálogos de materiales/secciones, guardar/cargar
- **F-FINAL**: Integración final del MVP

---

## DECISIONES IMPORTANTES

| Decisión | Valor | Razón |
|----------|-------|-------|
| Arquitectura | Cloud-first (SaaS) | Sin instalación, suscripción |
| Motor de cálculo | OpenSees (binario) | Mac ARM compatible via subprocess |
| Backend | Python 3.12 + FastAPI | Compatible con openseespy |
| Desktop UI | PySide6 + PyVista | Visualización 3D robusta |
| Unidades internas | SI (m, kN, kPa) | Consistencia |
| Ejes locales frames | Convención SAP2000 | Estándar industria |
| Formato proyecto | .paz (JSON + gzip) | Portabilidad |

---

## ARCHIVOS MODIFICADOS (SESIÓN ACTUAL)

```
backend/src/paz/
├── core/
│   ├── units.py              # Ampliado - conversiones adicionales
│   └── platform.py           # NUEVO - detección plataforma
├── domain/
│   └── sections/
│       └── section_designer.py  # NUEVO - secciones custom
├── infrastructure/
│   ├── exporters/
│   │   └── csv_exporter.py   # NUEVO - export CSV
│   └── importers/
│       ├── csv_importer.py   # NUEVO - import CSV
│       └── dxf_importer.py   # NUEVO - import DXF
└── presentation/
    └── main_window.py        # NUEVO - MainWindow GUI

backend/tests/unit/
├── core/
│   ├── test_units.py         # Ampliado - 35 tests
│   └── test_platform.py      # NUEVO - 19 tests
├── domain/
│   └── test_section_designer.py  # NUEVO - 20 tests
└── infrastructure/
    ├── test_csv_exporter.py  # NUEVO - 7 tests
    ├── test_csv_importer.py  # NUEVO - 10 tests
    └── test_dxf_importer.py  # NUEVO - 17 tests
```

---

## CÓMO CONTINUAR

### Ejecutar la aplicación:
```bash
cd backend
source .venv/bin/activate
python -m paz          # GUI desktop (defecto)
python -m paz --api    # Solo servidor API
```

### Verificar estado:
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Para siguiente feature:
1. Continuar con F-UI o F-FINAL
2. Implementar según criterios de aceptación
3. Crear tests unitarios
4. Actualizar RETOMAR.md

---

## REPOSITORIO

- **GitHub**: https://github.com/kcortes765/strux
- **Branch**: main

---

*Generado: 2026-01-10 18:30*
