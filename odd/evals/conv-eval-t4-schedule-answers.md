# Evaluación conversacional — `t4-schedule-answers`

Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, ventana de 24 h y plantillas de Meta quedan fuera de alcance.

- Sello: `4996fb4d80cfef5254802df9241dbb59d521103d` · árbol sucio: **sí** · corrida: cliente scripted
- Corpus: `dfb632518dd0` · KB: `91ca087a1130` (4 documentos)
- Bot: `deepseek` / `deepseek-chat`
- Juez: `sin juez (solo gates)` · inicio: 2026-10-27T21:00:53+00:00

> **No citable como baseline**: el árbol no estaba limpio.

## Resumen

- Escenarios: **4** · pasan: **4**
- Peor dimensión: `—`

| Tier | Escenarios | Pasan |
| --- | --- | --- |
| simple | 1 | 1 |
| complejo | 2 | 2 |
| supercomplejo | 1 | 1 |

### Gates que fallaron

Ninguno.

### Dimensiones del juez

Sin juez en esta corrida: los gates deciden solos.

## Escenarios que no pasan

Ninguno.

## Contra la corrida anterior

- Regresiones: ninguna
- Arreglos: simple-horario-sabado
- Gates que se movieron: simple-horario-sabado/G6 se arregló
