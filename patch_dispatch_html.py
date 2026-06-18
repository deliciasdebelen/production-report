with open("app/templates/logistics/dispatch.html", "r") as f:
    content = f.read()

# 1. Add 'status' display to table row
old_table_row_start = """                        <tr class="hover:bg-gray-50/50">
                            <!-- Acciones -->
                            <td class="px-3 py-2 whitespace-nowrap text-sm text-center border-l-2" style="border-left-color: {{ color }}; border-bottom: 1px solid #e5e7eb;">
                                <div class="flex items-center justify-center gap-1">"""
                                
new_table_row_start = """                        {% set is_anulada = log.status == 'Anulada' %}
                        <tr class="hover:bg-gray-50/50 {% if is_anulada %}bg-red-50/30 opacity-70{% endif %}">
                            <!-- Acciones -->
                            <td class="px-3 py-2 whitespace-nowrap text-sm text-center border-l-2" style="border-left-color: {{ color }}; border-bottom: 1px solid #e5e7eb;">
                                <div class="flex items-center justify-center gap-1">"""

if old_table_row_start in content:
    content = content.replace(old_table_row_start, new_table_row_start)

# 1b. Change badge visualization in the table
old_badge = """                                                {{ color }}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </td>"""

new_badge = """                                                {{ color }}
                                            </span>
                                            {% if is_anulada %}
                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 ml-2">
                                                Anulada
                                            </span>
                                            {% endif %}
                                        </div>
                                    </div>
                                </div>
                            </td>"""

if old_badge in content:
    content = content.replace(old_badge, new_badge)

# 2. Add 'Anular' button
old_button_group = """                                <button onclick="printDispatch('{{ log.id }}')"
                                    style="background: none; border: none; cursor: pointer; font-size: 1.1rem; opacity: 0.7; transition: opacity 0.2s;"
                                    title="Imprimir Guía">
                                    🖨️
                                </button>
                                </div>"""

new_button_group = """                                <button onclick="printDispatch('{{ log.id }}')"
                                    style="background: none; border: none; cursor: pointer; font-size: 1.1rem; opacity: 0.7; transition: opacity 0.2s;"
                                    title="Imprimir Guía">
                                    🖨️
                                </button>
                                {% if not is_anulada %}
                                <button onclick="annulDispatch('{{ log.id }}')"
                                    style="background: none; border: none; cursor: pointer; font-size: 1.1rem; opacity: 0.7; transition: opacity 0.2s; color: red;"
                                    title="Anular Guía">
                                    🚫
                                </button>
                                {% endif %}
                                </div>"""

if old_button_group in content:
    content = content.replace(old_button_group, new_button_group)

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

old_script_start = """    <script>
        function deleteDispatch(id) {"""

new_script_start = "    <script>\n        " + script_injection + "\n\n        function deleteDispatch(id) {"

if old_script_start in content:
    content = content.replace(old_script_start, new_script_start)

with open("app/templates/logistics/dispatch.html", "w") as f:
    f.write(content)

print("Patched app/templates/logistics/dispatch.html successfully.")
