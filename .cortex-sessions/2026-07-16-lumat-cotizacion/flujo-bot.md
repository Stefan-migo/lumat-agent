# Flujo del Bot IA — Lumat

> Documento ilustrativo del funcionamiento del asistente virtual.
> Preparado para presentación al cliente.

## Arquitectura conceptual

```
Cliente escribe por WhatsApp
           │
           ▼
    ┌──────────────────┐
    │   IDENTIFICACIÓN  │
    │   (por teléfono)  │
    └──────┬───────────┘
           │
     ┌─────┴──────┐
     │ ¿Existe?   │
     ├── Sí ──────┼──→ Cargar historial del cliente
     └── No ──────┼──→ Crear ficha nueva
           │
           ▼
    ┌──────────────────┐
    │  CONSTRUIR       │
    │  CONTEXTO        │
    │  ──────────────  │
    │  "Eres el        │
    │   asistente de   │
    │   Lumat..."      │
    │  + datos cliente │
    │  + historial     │
    │  + conocimiento  │
    └──────┬───────────┘
           │
           ▼
    ┌──────────────────┐
    │  CONSULTAR       │
    │  BASE DE         │
    │  CONOCIMIENTO    │
    │  (RAG)           │
    └──────┬───────────┘
           │
           ▼
    ┌──────────────────┐
    │  INTELIGENCIA    │
    │  ARTIFICIAL      │
    │  genera respuesta│
    │  con herramientas│
    └──────┬───────────┘
           │
           ▼
    ┌──────────────────┐
    │  GUARDAR TODO    │
    │  + responder     │
    └──────────────────┘
```

## El bot recuerda a cada cliente

Cuando un cliente vuelve a escribir, el bot ya sabe:

- **Quién es** (nombre, dirección, comuna)
- **Qué equipos tiene** (marca, modelo, antigüedad)
- **Historial de servicios** (qué se reparó, cuándo)
- **Preferencias** (horarios, forma de pago)
- **Patrones** (llama cada 6 meses por mantención)

**El cliente nunca tiene que repetir su historia.**

## Datos que captura el bot

| Categoría | Datos |
|-----------|-------|
| Identificación | Nombre, teléfono, correo |
| Ubicación | Comuna, dirección |
| Equipo | Tipo, marca, modelo, antigüedad |
| Falla | Descripción, código de error, frecuencia |
| Evidencia | Fotos, videos, audio |
| Disponibilidad | Días y horarios para visita |

## Detección de emergencias

El bot monitorea palabras clave como *gas, fuga, humo, incendio, chispa, explosión, monóxido, intoxicación*.

Si detecta una emergencia:
1. Interrumpe el flujo normal
2. Entrega instrucciones de seguridad
3. Recomienda contactar a servicios de emergencia
4. Notifica inmediatamente al equipo Lumat

## Derivación a atención humana

El bot deriva a una persona cuando:
- El cliente lo solicita
- No entiende la consulta tras 2 intentos
- Hay una emergencia
- Es un reclamo o garantía
- Se necesita presupuesto personalizado
- La información técnica es insuficiente

**La derivación incluye el historial completo** — el cliente no repite información.

## Memoria del sistema (cómo aprende)

Después de cada conversación, el sistema:

1. **Genera un resumen** de lo que se habló
2. **Actualiza la ficha del cliente** con nueva información
3. **Detecta patrones**: problemas recurrentes, oportunidades de servicio, equipos que podrían requerir atención
4. **Mejora la base de conocimiento** con preguntas no resueltas

Así, el bot es más inteligente con cada interacción.
