# Spec 022 — Estimación de propiedades sin ensayos (selectores visibles)

## Qué se construye

El valor del programa de referencia antiguo: obtener las propiedades de un material **sin
ensayos**, con tablas y cartas de campo. El programa de referencia las conserva escondidas
(botón de cada fila, que solo responde a **doble clic**); ORMAS las
tiene a la vista (botones "+"). OGR-Data las pone en primer plano, con
**un solo clic**, junto a σci, GSI, mi, D y Ei del criterio GHB (y los
equivalentes de HB clásico). Análisis: `08_estimacion_sin_ensayos.md` del análisis privado del programa de
referencia en `Referencias/Ejemplos/`, y `ORMAS_analisis/`.

1. **σci**: tabla de 7 clases de Hoek (ya en la spec 003). Valores que
   escribe cada clase = los del programa de referencia y ORMAS (verificados): 250, 175,
   75, 35, 15, 3, 0,6 MPa (hecho en esta revisión).
2. **GSI**:
   - Cartas: *Basic Observational 2000* (Hoek y Marinos), *Heterogeneous
     / flysch 2000* (Marinos y Hoek, en Bibliografia) y, con fuente, la
     *General Quantitative 2013* y la *Heterogeneous 2013* del programa de referencia.
   - **Clic sobre la carta → GSI** interpolando entre isolíneas
     digitalizadas (método de ORMAS: segmentos de igual GSI de 5 en 5,
     interpolación lineal por distancia; N/A fuera de zona). Hoy la 003
     solo ofrece estructura × superficie con rango indicativo.
   - **Calculadora** (el programa de referencia): RQD + JCond89 (GSI = 1,5·JCond89 + RQD/2),
     JCond76 (JCond89 = 1,3·JCond76) o Jr/Ja (GSI = 5,5·ln(Jr/Ja) + 21 +
     RQD/2). Mostrar el valor sin truncar (el programa de referencia parece truncar).
3. **mi**: la tabla de la 003 (Hoek, Tabla 3) con **filtros** Rock Type /
   Texture como el programa de referencia. Las nueve discrepancias entre ORMAS y el programa de referencia del
   documento 08 quedan resueltas: nuestra tabla (transcrita de Hoek)
   coincide con el programa de referencia; ORMAS tiene erratas (p. ej. Diorite/Diabase
   cruzadas).
4. **D**: tabla de Hoek 2002 (Tabla 1) / Practical Rock Engineering 2023
   (fig. 9): túnel y talud, con descripción y valor (0; 0; 0,5; 0,8;
   0,7/1,0; 1,0/0,7). Sustituye el punto 3 de la spec 018.
5. **Ei y módulo de la masa**: campo **Ei** visible en GHB (hoy oculto,
   12 000 MPa fijo en el núcleo) con selector **MR** (Ei = MR·σci; tabla
   MR de Deere 1968 en Practical Rock Engineering 2023, fig. 13) y
   **selector de método** de Erm (generalizado / simplificado H&D 2006 /
   Hoek 2002), como ORMAS. No reproducir el Ei fijo oculto del programa de referencia
   (20 000 MPa, deducido en el documento 08).

## Fuentes

- En Bibliografia: Hoek PRE cap. 11 (Tablas 2 y 3), PRE 2023 (figs. 9 y
  13, ecs. 20-22), Hoek 2002 (Tabla 1), Marinos & Hoek 2000 (carta GSI
  y flysch).
- Hoek, Carter & Diederichs (2013), *Quantification of the Geological
  Strength Index chart* (ARMA 13-672): en `Bibliografia/General/`
  (carta cuantitativa y calculadora; ver plan). Carta heterogénea 2013:
  pendiente (ver plan).
- Derechos: las cartas GSI y las fotos de D son material con derechos
  (Hoek, Marinos, el fabricante del programa de referencia): **redibujarlas** (vectorial, con las
  isolíneas digitalizadas) o pedir permiso; no copiar imágenes.

## Criterios de aceptación

- Botón de un clic junto a cada campo; el valor elegido se escribe en el
  formulario y se puede editar.
- Clic en la carta GSI devuelve el mismo GSI que ORMAS en puntos de
  control (a definir con su código, `getGsiGeneral`/`getGsiFlysch`).
- Calculadora: los tres casos del documento 08 (RQD 30) dan 30, 34,5 y
  39,81.
- Ei = MR·σci y Erm por los tres métodos coinciden con ORMAS (ya
  validado en el núcleo: 3686,23 / 9340,70 / 5477,23 MPa).

## Prioridad

Requisito clave indicado por el propietario (documento 08): se propone
como **siguiente spec**, antes de la 014.
