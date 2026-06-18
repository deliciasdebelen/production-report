with open("app/templates/logistics/dispatch.html", "r") as f:
    content = f.read()

# 1. Add Anulada badge
if "Anulada" not in content and "log.status == 'Anulada'" not in content:
    content = content.replace(
        '<tr class="hover:bg-gray-50/50">',
        '{% set is_anulada = log.status == "Anulada" %}\n                        <tr class="hover:bg-gray-50/50 {% if is_anulada %}bg-red-50/30 opacity-70{% endif %}">'
    )
    
    content = content.replace(
        '{{ color }}\n                                            </span>',
        '{{ color }}\n                                            </span>\n                                            {% if is_anulada %}\n                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 ml-2">\n                                                Anulada\n                                            </span>\n                                            {% endif %}'
    )

# 2. Add Anular button
if "annulDispatch(" not in content:
    old_btn = '                                </button>\n                                </div>'
    new_btn = '                                </button>\n                                {% if not is_anulada %}\n                                <button onclick="annulDispatch(\'{{ log.id }}\')"\n                                    style="background: none; border: none; cursor: pointer; font-size: 1.1rem; opacity: 0.7; transition: opacity 0.2s; color: red;"\n                                    title="Anular Guía">\n                                    🚫\n                                </button>\n                                {% endif %}\n                                </div>'
    content = content.replace(old_btn, new_btn)

# 3. Add JS function
script_injection = """function annulDispatch(dispatchId) {
    Swal.fire({
        title: '¿Anular Guía de Despacho?',
        text: "Al anular esta guía, las facturas y notas de entrega seleccionadas volverán a estar disponibles. Esta acción no se puede deshacer.",
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
                headers: {
                    'Content-Type': 'application/json'
                }
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
            .catch(err => {
                Swal.fire('Error', 'Error de red', 'error');
                console.error(err);
            });
        }
    });
}"""

if "function annulDispatch(" not in content:
    content = content.replace(
        '    <script>\n        function deleteDispatch(id) {',
        '    <script>\n        ' + script_injection + '\n\n        function deleteDispatch(id) {'
    )

with open("app/templates/logistics/dispatch.html", "w") as f:
    f.write(content)
print("Patched dispatch.html")
