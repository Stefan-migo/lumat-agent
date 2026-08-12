# LumatAgent — Requerimientos de servidor e infraestructura

> Documento técnico interno — HandCodeStudio (Stefan Miranda)
> Fecha: 7 de agosto de 2026
> **Estatus: propuesta técnica; valores económicos referenciales y sujetos a verificación al momento de contratar.**

---

## 1. Proveedor sugerido

**VPS recomendado: Hostinger KVM 2** — 2 vCPU / 8 GB RAM / 100 GB NVMe, datacenter en São Paulo (Brasil), con latencia a Chile de ~40-60 ms. Como alternativas: **MOX Networks** (datacenter local en Santiago de Chile) y **Hetzner** (económica, recomendada para entorno de staging/dev).

| Proveedor | Plan | Precio/mes (referencial) | Datacenter | Latencia a Chile | Notas clave |
|-----------|------|--------------------------|------------|------------------|-------------|
| **Hostinger** | KVM 2 (2 vCPU / 8 GB / 100 GB NVMe) | ~US$8.79/mes intro (2 años prepago); renovación ~US$14.99 | São Paulo (Brasil) | ~40-60 ms | Backups semanales gratis + snapshots, IP dedicada, firewall y protección DDoS, soporte en español 24/7 |
| **MOX Networks** | VPS Pro (2 vCPU / 4 GB / 10 GB NVMe) | ~US$18/mes (CLP 17.000, IVA incl.) | Santiago de Chile | 1-5 ms | IP chilena dedicada (LACNIC CL), backup diario externo incluido, soporte humano en español |
| **Hetzner** | CPX21 (3 vCPU / 4 GB / 80 GB NVMe) | ~€5-15/mes (referencial; verificar en hetzner.com/cloud) | Europa/USA/Singapur | ~240-290 ms | Sin datacenter en LATAM; útil como entorno de staging/dev, no como servidor principal |

**Notas:**

- **Hostinger (principal)**: cumple el dimensionamiento propuesto (2 vCPU / 8 GB / 100 GB NVMe), incluye backups semanales gratis, soporte en español y buena latencia a Chile (~40-60 ms). Ojo: el precio de introducción es US$8.79/mes (pago por adelantado, ciclo de 2 años) y la renovación real es ~US$14.99/mes (~CLP 14.200). hostinger.cl no es tienda oficial chilena (es landing de afiliados); Hostinger factura en EUR/USD.
- **MOX Networks (local)**: proveedor chileno real (Concepción, desde 2009), IP chilena dedicada, backup diario externo incluido y latencia local de 1-5 ms. Ojo: disco chico (10 GB) y virtualización LXC por defecto.
- **Hetzner (económica)**: sigue siendo la más barata, pero no tiene datacenter en Latinoamérica (~240-290 ms de latencia), lo que la hace mala para webhooks de Meta. Usarla como entorno de staging/dev, no como servidor principal.
- **Vultr (mención)**: único proveedor global con datacenter en Santiago de Chile (+ São Paulo y México); plan 2 vCPU / 4 GB = ~US$24/mes. Considerarla si el cliente prioriza rendimiento.

> **Advertencia**: todos los precios son referenciales a la fecha 7/8/2026 y sujetos a verificación al momento de contratar. La conversión CLP/USD es aproximada (US$1 ≈ CLP 950). hostinger.cl no es tienda oficial (Hostinger factura en EUR/USD) y Hetzner no publica precios extraíbles de su web (verificar en hetzner.com/cloud).

Alternativa equivalente: cualquier VPS con 2 vCPU / 8 GB RAM en un proveedor con respaldo confiable (Hostinger, MOX o Vultr como principal; Hetzner queda como staging). El dimensionamiento exacto se ajusta tras la fase de pruebas.

---

## 2. Sistema operativo y contenedores

- **SO**: Ubuntu LTS (última versión estable soportada).
- **Contenedores**: Docker + Docker Compose para todos los servicios (API, orquestador, worker, PostgreSQL, panel).
- **Actualizaciones**: parches de seguridad programados y reinicios planificados.

---

## 3. Stack de aplicación

| Componente | Tecnología | Rol |
|------------|------------|-----|
| API gateway | **FastAPI (Python)** | Recibe webhooks de WhatsApp, sirve la API REST, expone el panel |
| Orquestador | **LangGraph** | Estado del flujo conversacional y coordinación de sub-agentes |
| Base de datos | **PostgreSQL + pgvector** | Fuente de verdad (clientes, visitas, configuraciones) + búsqueda semántica de la base de conocimiento |
| Almacenamiento de archivos | **Volumen persistente** | Documentos de la base de conocimiento, exportaciones ICS, media |
| Worker de automatizaciones | Proceso determinístico (sin LLM) | Ejecuta reglas y colas aunque el modelo esté caído |

---

## 4. Red y dominio

- **Firewall**: solo puertos **80/443 y SSH**. Todo lo demás cerrado.
- **TLS obligatorio**: certificado HTTPS en todas las comunicaciones (Let's Encrypt o equivalente, renovación automática).
- **Dominio propio de Lumat** con subdominios:
  - `agente.lumat.cl` — API del agente / webhooks de WhatsApp.
  - `panel.lumat.cl` — panel web de administración (PWA).

---

## 5. Seguridad del servidor

| Capa | Medida |
|------|--------|
| Acceso | SSH solo por llave (sin password), usuario dedicado sin privilegios para la app |
| Protección de fuerza bruta | **fail2ban** sobre SSH y endpoints expuestos |
| Contenedores | Docker **sin `--privileged`**, filesystem **read-only** para el agente, red interna por servicios |
| Secretos | API keys de Meta/OpenAI en **variables de entorno del servidor**, nunca en código ni en el repositorio |
| Backups | **Automáticos diarios** de PostgreSQL a volumen externo, con retención definida y verificación periódica de restauración |
| Monitoreo | Básico: uptime, alerta si el bot o una API externa caen, aviso si un backup falla |
| Registro | Auditoría de acciones en `audit_log` (quién, qué, cuándo) |

### Seguridad del canal WhatsApp (prompt injection)

El bot recibe mensajes de cualquier persona desconocida: es la superficie de ataque más expuesta. Mitigaciones:

- **Aislamiento de instrucciones**: el input del cliente se trata como dato, nunca como instrucción.
- **Validación de entrada**: detección y neutralización de intentos de inyección.
- **Whitelist de tools por rol**: un cliente no puede ejecutar acciones de admin.
- **Escalamiento controlado**: consultas fuera de alcance o manipulaciones → derivación a humano, nunca ejecución.
- **Auditoría completa**: toda conversación y toda llamada a herramienta queda registrada.

---

## 6. Cargas esperadas y límites del plan de WhatsApp

- **Volumen realista**: decenas de conversaciones diarias (consultas, emergencias, agendamiento) — holgado para el VPS propuesto.
- **Ventana de 24 horas de Meta**: los mensajes al cliente son libres dentro de la ventana abierta por el último mensaje del cliente; fuera de ella, **solo plantillas aprobadas** (costo referencial ~$0.04-0.08 por mensaje de plantilla).
- **Plantillas de utilidad** (recordatorios, alertas, resúmenes): se aprueban rápido, a veces pre-aprobadas automáticamente.
- **Número de prueba de Meta**: gratuito pero solo a 5 destinatarios verificados — insuficiente para clientes reales; la fase de pruebas con Lumat usa un **número prepago dedicado**.
- **Límite de números registrados**: el portfolio inicia con hasta 2 números (ampliable a 20 tras verificación de negocio).

---

## 7. Checklist "listo para producción"

> Requisitos mínimos para operar con el número real. Responsable S = Stefan (HandCodeStudio), L = Lumat.

| Requisito | Estado | Responsable |
|-----------|--------|-------------|
| VPS contratado (Hostinger KVM 2 — São Paulo, o MOX local; Hetzner como staging) | Pendiente | S |
| Ubuntu LTS + Docker + Compose instalados y actualizados | Pendiente | S |
| Firewall activo solo 80/443/SSH | Pendiente | S |
| TLS habilitado en `agente.lumat.cl` y `panel.lumat.cl` | Pendiente | S |
| SSH solo por llave, sin password; fail2ban activo | Pendiente | S |
| Secretos en variables de entorno (ninguno en el repo) | Pendiente | S |
| Contenedores sin `--privileged`, filesystem read-only del agente | Pendiente | S |
| Backups automáticos diarios configurados y verificados | Pendiente | S |
| Monitoreo básico con alertas (uptime, bot caído, backup fallido) | Pendiente | S |
| Dominio `lumat.cl` con subdominios apuntando al servidor | Pendiente | L (entrega acceso de DNS) |
| Número prepago dedicado de pruebas comprado y disponible | Pendiente | L |
| Trámite de API de Meta iniciado (ver checklist Meta) | Pendiente | L |
| Base de conocimiento inicial cargada | Pendiente | L (contenido) / S (carga) |
| Pruebas con número prepago aprobadas por Lumat | Pendiente | L |
| Migración al número real de WhatsApp | Pendiente | S + L |
