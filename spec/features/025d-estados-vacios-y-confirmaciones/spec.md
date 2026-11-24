# Spec 025d — Estados vacíos y confirmaciones

> Estado: **hecha** (2026-11-24; plan, inventario y validación en `plan-tasks.md`).

## Contexto y objetivo

Hallazgos F5 y F8 de la [revisión](../025-revision-ux/revision.md): las
gráficas de trayectorias abren con ejes vacíos de −0.04 a 0.04 sin decir
qué falta; los diálogos de estados, trayectorias y simulaciones abren
con todo deshabilitado; borrar un material pide confirmación aunque se
puede deshacer, y borrar un estado no; varios cuadros de aviso dicen que
una acción no se puede hacer después de pulsarla.

## Historias de usuario

- H1: Como usuario nuevo quiero que una gráfica o lista vacía me diga
  cómo llenarla.
- H2: Como usuario quiero borrar sin diálogos, sabiendo que puedo deshacer.

## Requisitos funcionales (EARS)

- **RF-1**: MIENTRAS una gráfica de trayectorias no tenga datos, EL
  SISTEMA mostrará en ella qué falta y la acción del menú que lo crea, en
  lugar de ejes con escala inventada.
- **RF-2**: MIENTRAS el panel de animación no tenga simulaciones, EL
  SISTEMA dirá que hace falta calcular una (Tests > Compute).
- **RF-3**: MIENTRAS un diálogo de estados, trayectorias o simulaciones
  no tenga elementos, EL SISTEMA mostrará un texto con el primer paso y
  un botón «Add» / «Añadir» con texto (hoy «+»).
- **RF-4**: CUANDO el usuario borre un material, estado, trayectoria o
  simulación, EL SISTEMA lo borrará sin confirmación y dirá en la barra de
  estado qué borró y que Ctrl+Z lo recupera.
- **RF-5**: SI una acción no está disponible en el estado actual, ENTONCES
  EL SISTEMA la mostrará deshabilitada con un tooltip que diga por qué
  (p. ej. «Delete: a project keeps at least one material»), en lugar de un
  cuadro de aviso al pulsarla.
- **RF-6**: EL SISTEMA solo pedirá confirmación para lo irreversible:
  cerrar o abrir con cambios sin guardar y sobrescribir un archivo.

## Requisitos no funcionales

Ninguna confirmación nueva en código que ejecuten los tests (ganchos como
`ask_unsaved`). Textos con `tr()` y español.

## UX

U5, U6, U7, U15, U16.

## Casos límite

- Deshacer tras borrar el material activo: vuelve seleccionado.
- Estado de fallo con todos los puntos excluidos: la gráfica lo dice.

## Fuera de alcance

Errores de cálculo del núcleo (siguen como mensaje, con su texto).

## Criterios de finalización

Cada RF con su test; inventario de los 23 `QMessageBox` con qué se hace
con cada uno (queda, pasa a barra de estado, pasa a acción deshabilitada).

## Dudas abiertas

Resuelta (2026-11-24): el estado vacío lleva botones que ejecutan la acción.
