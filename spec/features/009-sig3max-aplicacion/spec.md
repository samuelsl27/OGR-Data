# Spec 009 — Rango de tensión por aplicación (σ3max túnel/talud)

## Qué se construye

El selector **Application: Custom | Tunnel | Slope** del Failure Range
(spec 002 lo dejó pendiente a propósito). Con túnel o talud se piden
**peso unitario (MN/m3)** y **profundidad/altura (m)** y el σ3max se
estima solo, como ORMAS (verificado: túnel γ=0,026·H=50 → σ3max=0,6642
MPa con refit c=0,3669 φ=49,98°; talud → c=0,4608 φ=46,50°) y como
RocData ("RocData estimates maximum σ3 values for tunneling and slope
design applications based on the principles outlined in Ref. 1").

## Trabajo de especificación incluido

Extraer las fórmulas exactas del §6 del paper Hoek, Carranza-Torres &
Corkum 2002 (PDF ya en Bibliografia) y de Marinos-Hoek 2000 §2.2
("0 < σ3 < σv where σv = depth × unit weight") y **validar numéricamente
contra los dos casos ORMAS** anotados arriba antes de implementar.
Si la fórmula del paper no reproduce ORMAS, la spec documentará ambas
variantes y se preguntará al propietario cuál adoptar (no inventar).

**Opciones confirmadas en RSData** (tercera pasada, captura `40_*`):
Application = **Custom | General | Tunnels | Slopes** ("General" = σci/4
del viejo RocData; Custom pide σ3max manual; Tunnels/Slopes piden peso
unitario y profundidad/altura).

## Criterios de aceptación

- Los dos casos ORMAS reproducidos con tolerancia 0,5 %.
- Custom sigue pidiendo σ3max manual.
- Tests sin Qt del cálculo de σ3max.

## Fuera de alcance

- Estimación σ3max "General" = σci/4 ya disponible en spec 001.
