
    // State
    let items = [];

    // Init
    document.addEventListener('DOMContentLoaded', () => {
        addItemRow(); // Start with one row
        loadArticles(); // Fetch Autocomplete Data
        loadRoutes(); // Fetch Active Routes

        // ... existing logic ...
    });

    // --- Route Logic ---
    async function loadRoutes() {
        try {
            const res = await fetch('/logistics/api/routes?t=' + new Date().getTime());
            if (res.ok) {
                const routes = await res.json();
                const select = document.getElementById('routeSelect');
                const currentVal = select.value;
                select.innerHTML = '<option value="">Seleccione una Ruta...</option>';
                routes.forEach(r => {
                    const option = document.createElement('option');
                    option.value = r.id;
                    option.textContent = r.name;
                    select.appendChild(option);
                });
                if (currentVal) select.value = currentVal;

                // DEBUG: Verify routes loaded
                if (routes.length === 0) {
                    console.warn("No routes returned from API");
                } else {
                    console.log("Loaded " + routes.length + " routes.");
                }
            }
        } catch (e) { console.error("Error loading routes", e); }
    }

    function toggleRouteInput() {
        const select = document.getElementById('routeSelect');
        const input = document.getElementById('routeInput');
        const btn = document.getElementById('btnToggleRoute');

        if (input.style.display === 'none') {
            // Switch to Input Mode
            input.style.display = 'block';
            select.style.display = 'none';
            select.value = ""; // Clear selection
            input.focus();

            // Change Button to 'List' or 'Cancel' icon
            btn.innerHTML = "☰"; // Menu icon to go back to list
            btn.style.background = "#64748b"; // Grey for 'Back'
            btn.title = "Seleccionar de lista";
        } else {
            // Switch to Select Mode
            input.style.display = 'none';
            select.style.display = 'block';
            input.value = ""; // Clear input

            // Change Button back to '+'
            btn.innerHTML = "+";
            btn.style.background = "#10b981";
            btn.title = "Agregar Nueva Ruta";
        }
    }

    // Reset Button Logic
    // Find the "Nuevo Despacho" span and make it clickable
    // It was defined above as: <span style="...">Nuevo Despacho</span> in line 21-23
    // I need to target it. Since I don't want to break the HTML replacement with huge chunks, 
    // I will trust the user to use the 'New Dispatch' action which triggers 'resetForm'.
    // For now, let's attach the resetForm to that element if I can match it, or I should have replaced it in HTML.
    // Wait, I replaced the HTML block above but I missed the "Nuevo Despacho" span in the ReplacementContent because I started at "Header Fields".
    // The "Nuevo Despacho" span is at line 21. My replacement started at line 31.
    // I must ensure I don't miss hooking it up.
    // I will add a script to find it or I should have replaced the whole card header.
    // Let's do a targeted replace for the header button first in the NEXT step or just add a listener here.

    const newDispatchBtn = document.querySelector('.card h3 + span');
    if (newDispatchBtn) {
        newDispatchBtn.style.cursor = 'pointer';
        newDispatchBtn.onclick = resetForm;
    }


    // Reset Form
    function resetForm() {
        if (confirm("¿Estás seguro de limpiar el formulario?")) {
            document.getElementById('dispatchForm').reset();
            items = [];
            addItemRow();
            document.getElementById('invoiceBadges').innerHTML = '';
            document.getElementById('importedInvoices').value = '';
            document.getElementById('invoiceInput').value = '';
        }
    }

    // --- Invoice Autocomplete & Search Logic ---
    // --- Invoice Autocomplete & Search Logic ---
    const invoiceInput = document.getElementById('invoiceInput');
    const invoiceList = document.getElementById('invoiceList');
    let invoiceDebounce;

    // State: 'invoice' or 'delivery_note'
    let currentDocType = 'invoice';

    function toggleDocType() {
        const btn = document.getElementById('btnDocToggle');
        const lbl = document.getElementById('lblDocType');
        const input = document.getElementById('invoiceInput');

        if (currentDocType === 'invoice') {
            currentDocType = 'delivery_note';
            btn.innerHTML = '🔄 Cambiar a Factura';
            lbl.innerText = 'Número de Nota de Entrega';
            input.placeholder = 'Buscar Nota de Entrega...';
        } else {
            currentDocType = 'invoice';
            btn.innerHTML = '🔄 Cambiar a Nota de Entrega';
            lbl.innerText = 'Número de Factura';
            input.placeholder = 'Buscar Factura (Escriba nro o cliente)...';
        }

        // Clear input logic
        input.value = '';
        input.focus();
    }

    invoiceInput.addEventListener('input', (e) => {
        const val = e.target.value;
        if (val.includes(' - ')) {
            // Optional: Auto-select logic if desired
        }

        if (val.length < 2) return;

        clearTimeout(invoiceDebounce);
        invoiceDebounce = setTimeout(async () => {
            try {
                // Dynamic Endpoint
                const endpoint = currentDocType === 'invoice'
                    ? '/logistics/api/external/invoices/search'
                    : '/logistics/api/external/delivery_notes/search';

                const res = await fetch(`${endpoint}?q=${encodeURIComponent(val)}`);
                if (res.ok) {
                    const data = await res.json();
                    invoiceList.innerHTML = '';
                    data.forEach(item => {
                        const option = document.createElement('option');
                        option.value = `${item.doc_num} - ${item.client}`;
                        invoiceList.appendChild(option);
                    });
                }
            } catch (err) {
                console.error("Autocomplete error", err);
            }
        }, 300);
    });

    function handleInvoiceEnter(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            searchInvoice();
        }
    }

    async function searchInvoice() {
        const input = document.getElementById('invoiceInput');
        let val = input.value.trim();

        if (val.includes(' - ')) {
            val = val.split(' - ')[0].trim();
        }

        const docNum = val;
        if (!docNum) return;

        const hiddenInput = document.getElementById('importedInvoices');
        const currentInvoices = hiddenInput.value ? hiddenInput.value.split(',') : [];

        // Use prefix to uniqueness
        const prefix = currentDocType === 'invoice' ? 'FACT' : 'NOTA';
        const storedValue = `${prefix}:${docNum}`;

        if (currentInvoices.includes(storedValue)) {
            alert(`${currentDocType === 'invoice' ? 'Esta factura' : 'Esta nota'} ya está en la lista actual.`);
            return;
        }

        input.disabled = true;

        try {
            const endpoint = currentDocType === 'invoice'
                ? `/logistics/api/external/invoice/${encodeURIComponent(docNum)}/items`
                : `/logistics/api/external/delivery_note/${encodeURIComponent(docNum)}/items`;

            const res = await fetch(endpoint);
            const data = await res.json();

            if (data.error) {
                alert(data.error);
                input.disabled = false;
                return;
            }
            if (!Array.isArray(data) || data.length === 0) {
                alert(`${currentDocType === 'invoice' ? 'Factura no encontrada' : 'Nota de entrega no encontrada'} o sin ítems pendientes.`);
                input.disabled = false;
                return;
            }

            if (items.length === 1 && !items[0].item && !items[0].qty) {
                items = [];
            }

            const totalAmount = data[0].invoice_total || 0;
            const clientName = data[0].client_name || '';

            data.forEach(invItem => {
                items.push({
                    client: clientName,
                    fact: invItem.fact_num,
                    item: invItem.art_des,
                    qty: invItem.total_articulo,
                    unit: invItem.co_uni || 'Unid',
                    total_cajas: invItem.total_cajas,
                    unidad_cajas: invItem.unidad_cajas,
                    num_lote: invItem.num_lote,
                    invoice_total: totalAmount
                });
            });

            currentInvoices.push(storedValue);
            hiddenInput.value = currentInvoices.join(',');

            // Pass just the list, updateBadges parses it
            updateBadges(currentInvoices);

            // Assume renderItems or similar exists. 
            // In typical flow we modify 'items' then user might see updates if Vue/React, 
            // but this is vanilla JS.
            // I'll ensure I call renderItems() or addItemRow() (if logic adds there).
            // Actually, based on previous code reading, `items` is just an array, logic needs to re-render table.
            renderItems();

            input.value = '';

        } catch (e) {
            console.error(e);
            alert("Error consultando documento");
        } finally {
            input.disabled = false;
            input.focus();
        }
    }

    function updateBadges(invoices) {
        const badgeContainer = document.getElementById('invoiceBadges');
        badgeContainer.innerHTML = '';
        invoices.forEach(val => {
            let type = 'Fact.';
            let cleanNum = val;

            if (val.includes(':')) {
                const parts = val.split(':');
                if (parts[0] === 'NOTA') type = 'Nota';
                cleanNum = parts[1];
            } else {
                // Determine inferred type if no prefix? (Legacy support)
                // Assume Fact if raw number.
            }

            const span = document.createElement('span');
            span.style.background = '#e0f2fe';
            span.style.color = '#0369a1';
            span.style.padding = '2px 8px';
            span.style.borderRadius = '4px';
            span.style.fontSize = '0.8rem';
            span.style.display = 'flex';
            span.style.alignItems = 'center';
            span.style.gap = '4px';

            // Pass 'val' (prefixed) to removeInvoice
            span.innerHTML = `<strong>${type}</strong> ${cleanNum} <span onclick="removeInvoice('${val}')" style="cursor:pointer; font-weight:bold; color: #0284c7; margin-left: 4px;">&times;</span>`;

            badgeContainer.appendChild(span);
        });
    }

    function removeInvoice(val) {
        const hiddenInput = document.getElementById('importedInvoices');
        let list = hiddenInput.value ? hiddenInput.value.split(',') : [];
        list = list.filter(i => i !== val);
        hiddenInput.value = list.join(',');

        let cleanNum = val;
        if (val.includes(':')) cleanNum = val.split(':')[1];

        // Remove items
        items = items.filter(i => i.fact !== cleanNum);
        renderItems();
        updateBadges(list);
    }

    // --- Legacy Functions Removed (checkPendingInvoices, importSpecificInvoice, importSelectedInvoices) ---
    // Keeping empty stubs if referenced elsewhere, but essentially replaced by searchInvoice.



    // Populate Product Datalist
    async function loadArticles() {
        try {
            const res = await fetch('/api/external/articles');
            if (res.ok) {
                const articles = await res.json();
                const datalist = document.getElementById('productList');
                datalist.innerHTML = ''; // Clear
                articles.forEach(art => {
                    const option = document.createElement('option');
                    // Format: DESCRIPTION (CODE)
                    option.value = `${art.description} (${art.code})`;
                    datalist.appendChild(option);
                });
            }
        } catch (e) {
            console.error("Failed to load articles", e);
        }
    }

    function renderItems() {
        const tbody = document.getElementById('itemsTableBody');
        const emptyState = document.getElementById('emptyState');
        tbody.innerHTML = '';

        if (items.length === 0) {
            emptyState.style.display = 'block';
            return;
        } else {
            emptyState.style.display = 'none';
        }

        items.forEach((item, index) => {
            // Determine breakdown text
            let breakdownHtml = '';
            if (item.total_cajas && item.total_cajas > 0) {
                const unit = item.unidad_cajas || 'CAJ';
                breakdownHtml = `<div style="font-size: 0.75rem; color: #16a34a; margin-top:0.25rem;">📦 ${item.total_cajas} ${unit}</div>`;
            }

            const tr = document.createElement('tr');
            
            // Build the string carefully without deep quote escaping inside string interpolation
            let itemInput = `<input type="text" value="${item.item}" onchange="updateItem(${index}, 'item', this.value)" list="productList" style="width: 100%; border: 1px solid var(--border); padding: 0.25rem; border-radius: var(--radius-sm);">`;
            if (item.fact) {
                itemInput = `<input type="text" value="${item.item}" readonly style="background: #f1f5f9; color: #64748b; width: 100%; border: 1px solid var(--border); padding: 0.25rem; border-radius: var(--radius-sm);">`;
            }

            let qtyInput = `<input type="number" step="0.01" value="${item.qty}" onchange="updateItem(${index}, 'qty', parseFloat(this.value))" style="width: 100%; border: 1px solid var(--border); padding: 0.25rem; border-radius: var(--radius-sm);">`;
            if (item.fact) {
                qtyInput = `<input type="number" step="0.01" value="${item.qty}" readonly title="Las cantidades de facturas no son modificables" style="background: #f1f5f9; color: #64748b; width: 100%; border: 1px solid var(--border); padding: 0.25rem; border-radius: var(--radius-sm);">`;
            }

            let unitSelect = `<select onchange="updateItem(${index}, 'unit', this.value)" style="width: 100%; border: 1px solid var(--border); padding: 0.25rem; border-radius: var(--radius-sm);">
                <option value="Unid" ${item.unit === 'Unid' ? 'selected' : ''}>Unid</option>
                <option value="Kg" ${item.unit === 'Kg' ? 'selected' : ''}>Kg</option>
                <option value="Cjas" ${item.unit === 'Cjas' ? 'selected' : ''}>Cajas</option>
                <option value="Lts" ${item.unit === 'Lts' ? 'selected' : ''}>Litros</option>
                <option value="${item.unit}" ${['Unid', 'Kg', 'Cjas', 'Lts'].includes(item.unit) ? '' : 'selected'}>${item.unit}</option>
            </select>`;
            if (item.fact) {
                unitSelect = `<select disabled style="background: #f1f5f9; color: #64748b; width: 100%; border: 1px solid var(--border); padding: 0.25rem; border-radius: var(--radius-sm);">
                <option value="${item.unit}" selected>${item.unit}</option>
            </select>`;
            }

            let actionBtn = `<button type="button" onclick="removeItem(${index})" style="background: transparent; border: none; color: var(--danger); cursor: pointer; font-size: 1.2rem; opacity: 0.6;">&times;</button>`;
            if (item.fact) {
                actionBtn = `<span title="Remueva la factura completa desde la sección superior" style="color: #cbd5e1; cursor: not-allowed; font-size: 1.2rem;">&times;</span>`;
            }

            tr.innerHTML = `
                <td style="padding: 0.5rem; text-align: center; color: var(--text-muted);">${index + 1}</td>
                <td style="padding: 0.5rem; font-size: 0.85rem; color: var(--primary);">
                    ${item.client || '-'}
                </td>
                <td style="padding: 0.5rem;">
                    <span style="font-size: 0.8rem; background: #e2e8f0; padding: 2px 6px; border-radius: 4px;">
                        ${item.fact || 'Manual'}
                    </span>
                </td>
                <td style="padding: 0.5rem;">
                    ${itemInput}
                    ${breakdownHtml}
                </td>
                <td style="padding: 0.5rem;">
                    ${qtyInput}
                </td>
                <td style="padding: 0.5rem;">
                    ${unitSelect}
                </td>
                <td style="padding: 0.5rem; text-align: center;">
                    ${actionBtn}
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    function addItemRow() {
        const clientInput = document.getElementById('clientInput');
        const currentClient = clientInput ? clientInput.value : '';
        items.push({ client: currentClient, item: '', qty: '', unit: 'Unid' });
        renderItems();
    }

    // --- Annulment Logic ---
    async function annulDispatch(id, ref) {
        if (!confirm(`⚠️ ALERTA ⚠️\n\n¿Estás seguro de que deseas ANULAR la guía ${ref}?\n\n- Esta acción no se puede deshacer.\n- Todas las facturas o notas contenidas volverán a estar disponibles de inmediato.\n\nEscribe "ANULAR" para confirmar:`)) return;

        try {
            const res = await fetch(`/logistics/api/dispatch/${id}/annul`, {
                method: 'POST'
            });
            const data = await res.json();

            if (res.ok) {
                alert(data.message);
                location.reload(); // Reload to refresh list and annulled states
            } else {
                alert(data.detail || "Error anulando la guía.");
            }
        } catch (e) {
            console.error(e);
            alert("Error de conexión al anular.");
        }
    }

    function removeItem(index) {
        items.splice(index, 1);
        renderItems();
    }

    function updateItem(index, field, value) {
        items[index][field] = value;
    }

    // Submit Handler
    document.getElementById('dispatchForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        // Validation
        const validItems = items.filter(i => i.item.trim() !== '' && i.qty > 0);

        if (validItems.length === 0) {
            alert("⚠️ Por favor agrega al menos un ítem válido (Nombre y Cantidad > 0).");
            return;
        }

        const formData = new FormData(e.target);
        // We only send valid items
        formData.append('items', JSON.stringify(validItems));

        try {
            // Button is now outside the form, connected via form attribute
            const btn = document.querySelector('button[form="dispatchForm"]');
            const originalText = btn.innerHTML;
            btn.innerHTML = '⏳ Guardando...';
            btn.disabled = true;

            const res = await fetch('/logistics/dispatch', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                showSuccessModal(data.document_ref);
                btn.innerHTML = originalText;
                btn.disabled = false;
            } else {
                // Try to get error detail
                try {
                    const errData = await res.json();
                    console.error("Error Saving:", errData);

                    let msg = "Error desconocido.";

                    if (errData.detail) {
                        if (typeof errData.detail === 'string') {
                            msg = errData.detail;
                        } else if (Array.isArray(errData.detail)) {
                            // Pydantic styled errors
                            msg = errData.detail.map(e => `${e.loc ? e.loc.join('.') : ''}: ${e.msg}`).join('\n');
                        } else {
                            // Object or other
                            msg = JSON.stringify(errData.detail, null, 2);
                        }
                    } else {
                        msg = JSON.stringify(errData, null, 2);
                    }

                    alert("❌ " + msg);
                } catch (e) {
                    console.error(e);
                    alert("❌ Error al procesar la respuesta del servidor.");
                }

                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        } catch (err) {
            console.error(err);
            alert("Error de conexión con el servidor.");
        }
    });

    // Summary Modal Logic
    function showSuccessModal(guideRef) {
        if (guideRef) {
            document.getElementById('successGuideRef').textContent = "Nro. Guía: " + guideRef;
        }
        document.getElementById('successModal').style.display = 'flex';
    }

    function closeSuccessAndReload() {
        window.location.reload();
    }

    // --- Search & Print Logic ---
    function filterLogs() {
        const input = document.getElementById('logSearch');
        const filter = input.value.toLowerCase();
        const list = document.getElementById('logList');
        const items = list.getElementsByClassName('log-item');

        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            const ref = (item.getAttribute('data-ref') || '').toLowerCase();
            const date = (item.getAttribute('data-date') || '').toLowerCase();
            const text = item.textContent.toLowerCase();

            if (ref.includes(filter) || date.includes(filter) || text.includes(filter)) {
                item.style.display = "";
            } else {
                item.style.display = "none";
            }
        }
    }

    function printDispatch(id) {
        // Open print view in new window
        const width = 800;
        const height = 600;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;

        window.open(
            `/logistics/dispatch/${id}/print`,
            'PrintDispatch',
            `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes`
        );
    }

    function printDispatchLabels(id) {
        const width = 800;
        const height = 600;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;

        window.open(
            `/logistics/dispatch/${id}/print-labels`,
            'Print',
            `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes`
        );
    }

    // --- Consolidated Report Logic ---
    let searchDebounceTimer;

    function debounceSearchGuides() {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            searchGuides();
        }, 600);
    }

    function openConsolidatedModal() {
        document.getElementById('consolidatedModal').style.display = 'flex';
        // Set default date to today
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('consDateFrom').value = today;
        document.getElementById('consDateTo').value = today;
        document.getElementById('consGuideRef').value = '';

        // Reset Views
        document.getElementById('consGuideListContainer').style.display = 'none';
        document.getElementById('consResultsContainer').style.display = 'none';

        // Clear Report Data
        const tbody = document.getElementById('consTableBody');
        if (tbody) tbody.innerHTML = '';
        document.getElementById('consTotalBoxes').textContent = '0';
        document.getElementById('consTotalWeight').textContent = '0.00 kg';

        document.getElementById('btnPrintConsolidated').style.display = 'none';

        // Initial Search
        searchGuides();
    }

    function closeConsolidatedModal() {
        document.getElementById('consolidatedModal').style.display = 'none';
    }

    async function searchGuides() {
        const guideRef = document.getElementById('consGuideRef').value.trim();
        const dateFrom = document.getElementById('consDateFrom').value;
        const dateTo = document.getElementById('consDateTo').value;

        // Visual loading state if needed, or silent for debounce
        // Let's toggle the button logic if it was clicked
        // But for debounce we might skip it to avoid flickering

        document.getElementById('consResultsContainer').style.display = 'none';
        document.getElementById('consGuideListContainer').style.display = 'none';
        document.getElementById('btnPrintConsolidated').style.display = 'none';

        try {
            const url = new URL('/logistics/api/guides/search', window.location.origin);
            if (guideRef) url.searchParams.append('q', guideRef);
            if (dateFrom) url.searchParams.append('date_from', dateFrom);
            if (dateTo) url.searchParams.append('date_to', dateTo);

            const res = await fetch(url);
            if (res.ok) {
                const guides = await res.json();
                renderGuideList(guides);
            } else {
                console.error("Search error");
            }
        } catch (e) {
            console.error(e);
        }
    }

    function renderGuideList(guides) {
        const tbody = document.getElementById('consGuideListBody');
        tbody.innerHTML = '';
        const container = document.getElementById('consGuideListContainer');
        container.style.display = 'block';

        if (guides.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:1rem;">No se encontraron guías.</td></tr>';
            return;
        }

        guides.forEach(g => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border);">${g.date}</td>
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border); font-weight: 600;">${g.guide_number}</td>
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border); font-size: 0.85rem;">${g.client}</td>
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border); text-align: center;">
                    <button onclick="selectConsolidatedGuide('${g.document_ref}')" 
                        class="btn" style="background: var(--bg-hover); color: var(--primary); padding: 0.25rem 0.75rem; font-size: 0.8rem;">
                        Ver Reporte
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    async function selectConsolidatedGuide(guideRef) {
        try {
            const url = new URL('/logistics/api/consolidated_report', window.location.origin);
            url.searchParams.append('guide_ref', guideRef);

            const res = await fetch(url);
            if (!res.ok) throw new Error("Error loading report");
            const data = await res.json();

            // Hide List, Show Report
            document.getElementById('consGuideListContainer').style.display = 'none';
            renderConsolidatedReport(data);

            // Set Print Context
            document.getElementById('consolidatedModal').setAttribute('data-selected-guide', guideRef);

        } catch (e) {
            console.error(e);
            alert("Error cargando reporte");
        }
    }

    function renderConsolidatedReport(data) {
        const tbody = document.getElementById('consTableBody');
        tbody.innerHTML = '';

        if (!data.details || data.details.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 1rem;">No se encontraron datos.</td></tr>';
            document.getElementById('consTotalBoxes').textContent = '0';
            document.getElementById('consTotalWeight').textContent = '0.00 kg';
            return;
        }

        data.details.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border);">${item.sku}</td>
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border); text-align: center;">${item.total_units}</td>
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border); text-align: center;">${item.total_boxes}</td>
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border); text-align: center;">${item.total_weight.toFixed(2)} kg</td>
                <td style="padding: 0.75rem; border-bottom: 1px solid var(--border); font-size: 0.8rem; color: #666;">
                    ${item.invoices.join(', ')}
                </td>
            `;
            tbody.appendChild(tr);
        });


        document.getElementById('consTotalBoxes').textContent = data.total_boxes_all;
        document.getElementById('consTotalWeight').textContent = data.total_weight_all.toFixed(2) + ' kg';

        // Update Invoice Count
        document.getElementById('consTotalInvoices').textContent = data.total_invoices_count || 0;

        if (data.total_amount_all) {
            document.getElementById('consTotalAmount').textContent = parseFloat(data.total_amount_all).toLocaleString('es-VE', { minimumFractionDigits: 2 });
        } else {
            document.getElementById('consTotalAmount').textContent = '0.00';
        }

        // Show print button and container if we have data
        if (data.details && data.details.length > 0) {
            document.getElementById('btnPrintConsolidated').style.display = 'inline-block';
            document.getElementById('consResultsContainer').style.display = 'block';
        }
    }

    function printConsolidatedReport() {
        // Get selected guide from attribute
        const guideRef = document.getElementById('consolidatedModal').getAttribute('data-selected-guide');

        if (!guideRef) return;

        // Extract number for pretty printing if needed, or pass full ref
        const guideNum = guideRef.split('|')[0].trim();

        const url = new URL('/logistics/consolidated_report/print', window.location.origin);
        url.searchParams.append('guide_ref', guideNum);

        const width = screen.availWidth;
        const height = screen.availHeight;

        window.open(
            url.toString(),
            'PrintConsolidated',
            `width=${width},height=${height},top=0,left=0,resizable=yes,scrollbars=yes`
        );
    }
