# NIFES STRUC — Estado actual + Pipeline OpenSees (macOS Apple Silicon)

Este documento consolida **TODO el estado real del proyecto NIFES STRUC** y
describe **paso a paso** cómo se dejó **OpenSees funcionando correctamente**
en **macOS Apple Silicon (M-series, M5)**.

Este archivo es **fuente de verdad** para:
- Agentes Codex
- Claude
- Revisión futura del proyecto
- Refactors sin romper el pipeline

---

## 1. Entorno de ejecución

- Sistema operativo: **macOS (Apple Silicon, M-series / M5)**
- Python: **3.12**
- Entorno virtual: **.venv**
- GUI: **Tkinter**
- Visualización 3D: **PyVista + VTK**
- Motor estructural: **OpenSees (binario externo)**  
  ❌ *NO OpenSeesPy*

Ejecución estándar del proyecto:

```bash
cd /path/to/NIFES_STRUC
source .venv/bin/activate
python src/run_gui.py