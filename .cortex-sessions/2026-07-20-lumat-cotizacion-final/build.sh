#!/bin/bash
#
# build.sh — Lumat Propuesta Técnica y Económica
# Orquestra la generación del PDF final desde el Markdown ensamblado.
#
# Requisitos:
#   - Node.js + npm
#   - md-to-pdf (instalado localmente o global)
#   - Mermaid CLI (@mermaid-js/mermaid-cli) para regenerar diagramas
#
# Uso:
#   chmod +x build.sh
#   ./build.sh          # Genera el PDF completo
#   ./build.sh --diagrams  # Solo regenera los diagramas
#   ./build.sh --clean     # Limpia archivos generados

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MD_FILE="propuesta-tecnica-economica-lumat.md"
PDF_OUTPUT="propuesta-tecnica-economica-lumat.pdf"
CONFIG_FILE="md-to-pdf.config.js"
CSS_FILE="style.css"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[build]${NC} $1"; }
success() { echo -e "${GREEN}[build]${NC} $1"; }

# ---- Regenerar diagramas Mermaid ----
generate_diagrams() {
    log "Generando diagramas Mermaid..."
    
    local MMDC="node_modules/.bin/mmdc"
    if [ ! -f "$MMDC" ]; then
        log "Instalando @mermaid-js/mermaid-cli..."
        npm install --no-audit --no-fund @mermaid-js/mermaid-cli 2>&1 | tail -3
    fi
    
    mkdir -p diagrams
    
    for mmd_file in diagrams/*.mmd; do
        local base="$(basename "$mmd_file" .mmd)"
        local png_file="diagrams/${base}.png"
        log "  Renderizando $mmd_file → $png_file"
        node "$MMDC" -i "$mmd_file" -o "$png_file" -w 1200 -b white 2>&1 || true
    done
    
    success "Diagramas generados."
}

# ---- Tomar screenshots de wireframes ----
generate_wireframes() {
    log "Generando screenshots de wireframes..."
    
    if [ ! -f "node_modules/puppeteer" ] && [ ! -f "node_modules/puppeteer-core" ]; then
        log "Instalando puppeteer..."
        npm install --no-audit --no-fund puppeteer 2>&1 | tail -3
    fi
    
    node screenshot.js 2>&1 || log "Wireframe screenshots — algunos pueden haber fallado (no bloqueante)"
}

# ---- Generar PDF ----
generate_pdf() {
    log "Generando PDF desde $MD_FILE..."
    
    if [ ! -f "$MD_FILE" ]; then
        echo "ERROR: No se encontró $MD_FILE"
        exit 1
    fi
    
    # Verificar que md-to-pdf esté disponible
    if ! npx md-to-pdf --version &>/dev/null; then
        log "Instalando md-to-pdf..."
        npm install --no-audit --no-fund md-to-pdf 2>&1 | tail -3
    fi
    
    log "Ejecutando md-to-pdf..."
    npx md-to-pdf "$MD_FILE" --config-file "$CONFIG_FILE" --stylesheet "$CSS_FILE" 2>&1
    
    if [ -f "$PDF_OUTPUT" ]; then
        local size=$(du -h "$PDF_OUTPUT" | cut -f1)
        success "PDF generado: $PDF_OUTPUT ($size)"
    else
        echo "ERROR: Falló la generación del PDF"
        exit 1
    fi
}

# ---- Limpiar ----
clean() {
    log "Limpiando archivos generados..."
    rm -f "$PDF_OUTPUT"
    rm -f diagrams/*.png
    rm -f wireframes/*.png
    success "Limpieza completada."
}

# ---- Main ----
case "${1:-}" in
    --diagrams)
        generate_diagrams
        ;;
    --wireframes)
        generate_wireframes
        ;;
    --clean)
        clean
        ;;
    --pdf-only)
        generate_pdf
        ;;
    *)
        log "=== Build: Propuesta Técnica y Económica Lumat ==="
        generate_diagrams
        generate_wireframes
        generate_pdf
        success "Build completo. PDF: $PDF_OUTPUT"
        ;;
esac
