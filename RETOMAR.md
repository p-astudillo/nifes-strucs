# RETOMAR.md

> Lee este archivo primero si eres una IA nueva retomando este proyecto.

---

## PROYECTO
**Nombre**: PAZ (Software Profesional de Análisis Estructural)
**Estado**: en progreso
**Última actividad**: 2026-01-11 10:30

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

### Última sesión (2026-01-11 10:30)

**F-UI - Continuación de Interfaz de Usuario:**

1. **Diálogos de Materiales y Secciones**
   - `presentation/dialogs/__init__.py` - Módulo de diálogos
   - `presentation/dialogs/material_dialog.py` - MaterialDialog
     - Filtro por tipo (Steel, Concrete, etc.)
     - Búsqueda por nombre
     - Vista de propiedades (E, G, nu, rho, fy, fu, fc)
   - `presentation/dialogs/section_dialog.py` - SectionDialog
     - Filtro por forma (W, HSS, L, C, etc.)
     - Búsqueda por designación
     - Vista de propiedades geométricas (A, Ix, Iy, Sx, Sy, rx, ry, Zx, Zy, J)

2. **Integración File > Open/Save en MainWindow**
   - Menú File: New, Open, Save, Save As, Exit
   - Menú Model: Materials, Sections (abre diálogos)
   - Guardar/cargar proyectos .paz
   - Indicador de modificación (*) en título
   - Confirmación antes de descartar cambios

3. **Tests para diálogos**
   - `tests/unit/presentation/dialogs/test_material_dialog.py`
   - `tests/unit/presentation/dialogs/test_section_dialog.py`

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
│   ├── __init__.py           # NUEVO - exports MaterialDialog, SectionDialog
│   ├── material_dialog.py    # NUEVO - diálogo selección materiales
│   └── section_dialog.py     # NUEVO - diálogo selección secciones
└── main_window.py            # MODIFICADO - Open/Save, menú Model

backend/tests/unit/presentation/dialogs/
├── __init__.py               # NUEVO
├── test_material_dialog.py   # NUEVO - tests lógica materiales
└── test_section_dialog.py    # NUEVO - tests lógica secciones
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

*Generado: 2026-01-11 10:30*
