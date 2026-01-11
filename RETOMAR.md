# RETOMAR.md

> Lee este archivo primero si eres una IA nueva retomando este proyecto.

---

## PROYECTO
**Nombre**: PAZ (Software Profesional de Análisis Estructural)
**Estado**: en progreso
**Última actividad**: 2026-01-11 11:30

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

### Última sesión (2026-01-11 11:30)

**F-UI - Interfaz de Usuario (continuación):**

1. **Diálogos de Nodos y Frames**
   - `presentation/dialogs/node_dialog.py` - NodeDialog
     - Edición de coordenadas X, Y, Z
     - Configuración de restraints con presets (Free, Fixed, Pinned, Roller)
     - Checkboxes individuales para cada DOF
   - `presentation/dialogs/frame_dialog.py` - FrameDialog
     - Selector de material (abre MaterialDialog)
     - Selector de sección (abre SectionDialog)
     - Rotación en grados
     - Releases con presets (Fixed-Fixed, Pinned-Pinned, etc.)
     - Label opcional

2. **Menús completos en MainWindow**
   - **File**: New, Open, Save, Save As, Exit
   - **Edit**: Undo, Redo, Delete, Select All
   - **View**: Reset View
   - **Model**: Add Node, Add Frame, Materials, Sections
   - **Analysis**: Run Analysis (F5), View Results

3. **Shortcuts de teclado**
   - Ctrl+Shift+N: Add Node dialog
   - Ctrl+Shift+F: Add Frame dialog
   - F5: Run Analysis
   - Delete, Ctrl+A, Ctrl+Z, Ctrl+Y, etc.

### Sesión anterior (2026-01-10 18:30)

**4 Features completadas:**

1. **F33 - Export/Import** (34 tests)
   - `infrastructure/exporters/csv_exporter.py` - CSVExporter, ResultsExporter
   - `infrastructure/importers/csv_importer.py` - CSVImporter
   - `infrastructure/importers/dxf_importer.py` - DXFImporter (AutoCAD)

2. **F36 - Section Designer** (20 tests)
   - `domain/sections/section_designer.py` - SectionDesigner, SectionRegion

3. **F37 - Conversor de Unidades** (35 tests)
   - `core/units.py` ampliado con conversiones adicionales

4. **F38 - Compatibilidad macOS** (19 tests)
   - `core/platform.py` - Detección de plataforma y dependencias

### Próxima tarea
- **F-UI (continuar)**: Property panel mejorado, Model tree mejorado
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
backend/src/paz/presentation/
├── dialogs/
│   ├── __init__.py           # MODIFICADO - exports 4 dialogs
│   ├── frame_dialog.py       # NUEVO - diálogo edición frames
│   ├── material_dialog.py    # diálogo selección materiales
│   ├── node_dialog.py        # NUEVO - diálogo edición nodos
│   └── section_dialog.py     # diálogo selección secciones
└── main_window.py            # MODIFICADO - menús completos, Analysis

backend/tests/unit/presentation/dialogs/
├── __init__.py
├── test_material_dialog.py
└── test_section_dialog.py
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

- **GitHub**: https://github.com/p-astudillo/nifes-strucs
- **Branch**: main

---

*Generado: 2026-01-11 11:30*
