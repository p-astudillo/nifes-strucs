---
name: retomar
description: Genera/actualiza RETOMAR.md para continuidad de IA
triggers:
  - /retomar
  - actualiza el archivo de retomar
auto_trigger:
  - after: guardar
  - after: guardar-codigo
  - after: preparar-manual
  - after: preparar-auto
---

# Skill: Generar/Actualizar RETOMAR.md

> Este skill se ejecuta automáticamente con cada /guardar*
> También puede invocarse manualmente con /retomar

## Acción

### 1. Recopilar información

Leer y extraer:
- Nombre del proyecto (de CLAUDE.md o carpeta)
- Estado actual (de .agente/codigo/resumen.md)
- Última actividad (fecha actual)
- Modo de trabajo (detectar si existe feature_list.json)
- Progreso (de feature_list.json si existe)
- Última feature trabajada
- Próxima tarea pendiente
- Resumen de última sesión (de .agente/codigo/reciente.md)

### 2. Generar RETOMAR.md en raíz del proyecto

```markdown
# RETOMAR.md

> Lee este archivo primero si eres una IA nueva retomando este proyecto.

---

## PROYECTO
**Nombre**: [nombre]
**Estado**: [en progreso | completado | iniciando]
**Última actividad**: [fecha hora]

---

## LEER PRIMERO

1. `CLAUDE.md` - Instrucciones y reglas del proyecto
2. `.agente/codigo/resumen.md` - Estado actual del código
3. `.agente/specs/brief.md` - Visión y objetivos

---

## ESTADO ACTUAL

**Modo**: [manual | automatico]
**Progreso**: [X/Y features] o [descripción si es manual]

### Última sesión
[Resumen breve de qué se hizo]

### Próxima tarea
[Qué hacer a continuación]

---

## DECISIONES IMPORTANTES

[Lista de decisiones críticas tomadas - de .agente/codigo/decisiones.md]

---

## ARCHIVOS MODIFICADOS RECIENTEMENTE

[Lista de archivos tocados en últimas sesiones]

---

## CÓMO CONTINUAR

### Si el usuario quiere seguir manualmente:
1. Lee los archivos de "LEER PRIMERO"
2. Revisa el estado actual
3. Pregunta qué quiere hacer
4. Al terminar: `/guardar-codigo`

### Si el usuario quiere modo automático:
```powershell
..\agente.ps1 -Status   # Ver estado
..\agente.ps1 -All      # Continuar todas las features
```

---

## HERRAMIENTAS

- **LSP**: SIEMPRE usar para navegación (findReferences, goToDefinition)
- **Plugins**: `/plugins` para ver disponibles
- **Background**: `Ctrl+B` para research paralelo

---

*Generado: [fecha hora]*
```

### 3. Confirmar

Responder: "RETOMAR.md actualizado - cualquier IA nueva puede leerlo para retomar el trabajo."
