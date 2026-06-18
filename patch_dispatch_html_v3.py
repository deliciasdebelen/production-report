with open("app/templates/logistics/dispatch.html", "r") as f:
    content = f.read()

# 1. Add Anulada badge and styling
if "is_anulada" not in content:
    content = content.replace(
        '<div class="dispatch-item" onclick="openDispatch(\'{{ log.id }}\')">',
        '{% set is_anulada = log.status == "Anulada" %}\n                <div class="dispatch-item {% if is_anulada %}opacity-70 bg-red-50{% endif %}" onclick="openDispatch(\'{{ log.id }}\')">'
    )
    content = content.replace(
        '{{ log.client_destination\n                            }}</strong>\n                    </div>',
        '{{ log.client_destination\n                            }}</strong>\n                        {% if is_anulada %}\n                        <span style="font-size: 0.75rem; color: #dc2626; background: #fee2e2; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">Anulada</span>\n                        {% endif %}\n                    </div>'
    )

# 2. Add Anular button
if "annulDispatch(" not in content:
    content = content.replace(
        'title="Imprimir Guía">\n                                🖨️\n                            </button>\n                        </div>',
        'title="Imprimir Guía">\n                                🖨️\n                            </button>\n                            {% if not is_anulada %}\n                            <button onclick="event.stopPropagation(); annulDispatch(\'{{ log.id }}\')"\n                                style="background: none; border: none; cursor: pointer; font-size: 1.1rem; opacity: 0.7; transition: opacity 0.2s; color: red;"\n                                title="Anular Guía">\n                                🚫\n                            </button>\n                            {% endif %}\n                        </div>'
    )

# 3. Add JS function
script_injection = """
    function annulDispatch(dispatchId) {
        Swal.fire({
            title: '¿Anular Guía de Despacho?',
            text: "Al anular esta guía, las facturas y notas de entrega volverán a estar disponibles.",
            icon: 'warning',
            showCancelButton: true,
            confirmColor: '#d33',
            cancelColor: '#3085d6',
            confirmButtonText: 'Sí, Anular',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                fetch(`/logistics/dispatch/${dispatchId}/annul`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(res => res.json().then(data => ({status: res.status, body: data})))
                .then(res => {
                    if(res.status === 200) {
                        Swal.fire('¡Anulada!', res.body.message, 'success')
                        .then(() => window.location.reload());
                    } else {
                        Swal.fire('Error', res.body.detail || 'Ocurrió un error', 'error');
                    }
                })
                .catch(err => Swal.fire('Error', 'Error de red', 'error'));
            }
        });
    }
"""

if "function annulDispatch(" not in content:
    content = content.replace(
        'function printDispatch(id) {',
        script_injection + '\n    function printDispatch(id) {'
    )

with open("app/templates/logistics/dispatch.html", "w") as f:
    f.write(content)
print("Patched dispatch.html")
