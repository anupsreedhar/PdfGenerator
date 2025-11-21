/**
 * Template Designer - Fabric.js Canvas
 */

let canvas;
let currentTemplate = null;
let selectedObject = null;
let fieldCounter = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initCanvas();
    loadTemplateFromURL();
    setupEventListeners();
});

/**
 * Initialize Fabric.js canvas
 */
function initCanvas() {
    // Letter size: 8.5" x 11" at 72 DPI = 612 x 792 pixels
    canvas = new fabric.Canvas('designCanvas', {
        width: 612,
        height: 792,
        backgroundColor: '#ffffff',
        selection: true
    });

    // Canvas events
    canvas.on('selection:created', onObjectSelected);
    canvas.on('selection:updated', onObjectSelected);
    canvas.on('selection:cleared', onObjectCleared);
    canvas.on('object:modified', updateFieldCount);

    updateFieldCount();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Property panel inputs
    document.getElementById('fieldName')?.addEventListener('change', updateSelectedField);
    document.getElementById('fieldType')?.addEventListener('change', updateSelectedField);
    document.getElementById('fieldLabel')?.addEventListener('change', updateSelectedField);
    document.getElementById('fontSize')?.addEventListener('change', updateSelectedField);
    document.getElementById('fontWeight')?.addEventListener('change', updateSelectedField);
}

/**
 * Add field to canvas
 */
function addField(type) {
    fieldCounter++;
    const fieldName = `field_${type}_${fieldCounter}`;
    
    let obj;
    
    switch(type) {
        case 'text':
        case 'number':
        case 'date':
            obj = new fabric.Rect({
                left: 100,
                top: 100 + (fieldCounter * 50),
                width: 200,
                height: 30,
                fill: 'rgba(13, 110, 253, 0.1)',
                stroke: '#0d6efd',
                strokeWidth: 2,
                rx: 5,
                ry: 5
            });
            break;
            
        case 'checkbox':
            obj = new fabric.Rect({
                left: 100,
                top: 100 + (fieldCounter * 50),
                width: 20,
                height: 20,
                fill: 'rgba(13, 110, 253, 0.1)',
                stroke: '#0d6efd',
                strokeWidth: 2,
                rx: 3,
                ry: 3
            });
            break;
            
        case 'label':
            obj = new fabric.Text('Label Text', {
                left: 100,
                top: 100 + (fieldCounter * 50),
                fontSize: 12,
                fontFamily: 'Arial',
                fill: '#000000'
            });
            break;
    }
    
    // Add custom properties
    obj.set({
        fieldName: fieldName,
        fieldType: type,
        fieldLabel: fieldName.replace(/_/g, ' ').toUpperCase()
    });
    
    canvas.add(obj);
    canvas.setActiveObject(obj);
    canvas.renderAll();
    updateFieldCount();
}

/**
 * Object selected event
 */
function onObjectSelected(e) {
    selectedObject = e.selected[0];
    showProperties(selectedObject);
}

/**
 * Object cleared event
 */
function onObjectCleared() {
    selectedObject = null;
    hideProperties();
}

/**
 * Show properties panel
 */
function showProperties(obj) {
    document.getElementById('propertiesPanel').style.display = 'none';
    document.getElementById('fieldProperties').style.display = 'block';
    
    // Populate fields
    document.getElementById('fieldName').value = obj.fieldName || '';
    document.getElementById('fieldType').value = obj.fieldType || 'text';
    document.getElementById('fieldLabel').value = obj.fieldLabel || '';
    document.getElementById('fontSize').value = obj.fontSize || 12;
    document.getElementById('fontWeight').value = obj.fontWeight || 'normal';
    document.getElementById('posX').value = Math.round(obj.left);
    document.getElementById('posY').value = Math.round(obj.top);
    document.getElementById('width').value = Math.round(obj.width * obj.scaleX);
    document.getElementById('height').value = Math.round(obj.height * obj.scaleY);
}

/**
 * Hide properties panel
 */
function hideProperties() {
    document.getElementById('propertiesPanel').style.display = 'block';
    document.getElementById('fieldProperties').style.display = 'none';
}

/**
 * Update selected field from properties
 */
function updateSelectedField() {
    if (!selectedObject) return;
    
    selectedObject.set({
        fieldName: document.getElementById('fieldName').value,
        fieldType: document.getElementById('fieldType').value,
        fieldLabel: document.getElementById('fieldLabel').value
    });
    
    canvas.renderAll();
}

/**
 * Apply properties to selected object
 */
function applyProperties() {
    if (!selectedObject) return;
    
    const updates = {
        fieldName: document.getElementById('fieldName').value,
        fieldType: document.getElementById('fieldType').value,
        fieldLabel: document.getElementById('fieldLabel').value,
        left: parseInt(document.getElementById('posX').value),
        top: parseInt(document.getElementById('posY').value)
    };
    
    const newWidth = parseInt(document.getElementById('width').value);
    const newHeight = parseInt(document.getElementById('height').value);
    
    if (selectedObject.type === 'text') {
        updates.fontSize = parseInt(document.getElementById('fontSize').value);
        updates.fontWeight = document.getElementById('fontWeight').value;
    } else {
        updates.scaleX = newWidth / selectedObject.width;
        updates.scaleY = newHeight / selectedObject.height;
    }
    
    selectedObject.set(updates);
    canvas.renderAll();
    
    showNotification('Properties applied', 'success');
}

/**
 * Show table modal
 */
function showTableModal() {
    const modal = new bootstrap.Modal(document.getElementById('tableModal'));
    modal.show();
}

/**
 * Add table to canvas
 */
function addTable() {
    const tableName = document.getElementById('tableName').value.trim() || `table_${++fieldCounter}`;
    const rows = parseInt(document.getElementById('tableRows').value);
    const columns = parseInt(document.getElementById('tableColumns').value);
    const headersInput = document.getElementById('tableHeaders').value.trim();
    const cellWidth = parseInt(document.getElementById('tableCellWidth').value);
    const cellHeight = parseInt(document.getElementById('tableCellHeight').value);
    
    // Parse headers
    const headers = headersInput ? headersInput.split(',').map(h => h.trim()) : [];
    
    // Calculate table dimensions
    const tableWidth = cellWidth * columns;
    const hasHeaders = headers.length > 0;
    const tableHeight = cellHeight * (rows + (hasHeaders ? 1 : 0));
    
    // Create table as a group of rectangles and lines
    const tableElements = [];
    
    // Starting position (centered)
    const startX = 100;
    const startY = 100;
    
    // Draw table border
    const border = new fabric.Rect({
        left: startX,
        top: startY,
        width: tableWidth,
        height: tableHeight,
        fill: 'transparent',
        stroke: '#333',
        strokeWidth: 2,
        selectable: false
    });
    tableElements.push(border);
    
    // Draw horizontal lines
    const totalRows = rows + (hasHeaders ? 1 : 0);
    for (let i = 1; i < totalRows; i++) {
        const line = new fabric.Line(
            [startX, startY + (i * cellHeight), startX + tableWidth, startY + (i * cellHeight)],
            {
                stroke: '#333',
                strokeWidth: hasHeaders && i === 1 ? 2 : 1,
                selectable: false
            }
        );
        tableElements.push(line);
    }
    
    // Draw vertical lines
    for (let i = 1; i < columns; i++) {
        const line = new fabric.Line(
            [startX + (i * cellWidth), startY, startX + (i * cellWidth), startY + tableHeight],
            {
                stroke: '#333',
                strokeWidth: 1,
                selectable: false
            }
        );
        tableElements.push(line);
    }
    
    // Add header text if provided
    if (hasHeaders) {
        for (let col = 0; col < Math.min(columns, headers.length); col++) {
            const headerText = new fabric.Text(headers[col], {
                left: startX + (col * cellWidth) + 5,
                top: startY + 5,
                fontSize: 12,
                fontWeight: 'bold',
                fill: '#000',
                selectable: false
            });
            tableElements.push(headerText);
        }
    }
    
    // Create group
    const tableGroup = new fabric.Group(tableElements, {
        left: startX,
        top: startY,
        selectable: true,
        hasControls: true
    });
    
    // Add custom properties
    tableGroup.set({
        fieldName: tableName,
        fieldType: 'table',
        fieldLabel: tableName.replace(/_/g, ' ').toUpperCase(),
        tableRows: rows,
        tableColumns: columns,
        tableHeaders: headers,
        cellWidth: cellWidth,
        cellHeight: cellHeight
    });
    
    canvas.add(tableGroup);
    canvas.setActiveObject(tableGroup);
    canvas.renderAll();
    updateFieldCount();
    
    // Close modal
    bootstrap.Modal.getInstance(document.getElementById('tableModal')).hide();
    showNotification('Table added successfully', 'success');
}

/**
 * Delete selected object
 */
function deleteSelected() {
    if (!selectedObject) {
        alert('Please select a field to delete');
        return;
    }
    
    canvas.remove(selectedObject);
    selectedObject = null;
    hideProperties();
    updateFieldCount();
}

/**
 * Clear canvas
 */
function clearCanvas() {
    if (confirm('Clear all fields from canvas?')) {
        canvas.clear();
        canvas.backgroundColor = '#ffffff';
        updateFieldCount();
        fieldCounter = 0;
    }
}

/**
 * Update field count display
 */
function updateFieldCount() {
    const count = canvas.getObjects().length;
    document.getElementById('fieldCount').textContent = `Fields: ${count}`;
}

/**
 * Save template
 */
async function saveTemplate() {
    console.log('🔵 saveTemplate() called');
    
    const name = document.getElementById('templateName').value.trim();
    
    if (!name) {
        alert('Please enter a template name');
        document.getElementById('templateName').focus();
        return;
    }
    
    const objects = canvas.getObjects();
    console.log(`🔵 Found ${objects.length} objects on canvas`);
    
    if (objects.length === 0) {
        alert('Please add at least one field to the template');
        return;
    }
    
    // Convert canvas objects to field structure
    const fields = objects.map(obj => {
        const field = {
            name: obj.fieldName || 'unnamed',
            type: obj.fieldType || 'text',
            label: obj.fieldLabel || obj.fieldName,
            x: Math.round(obj.left),
            y: Math.round(obj.top),
            width: Math.round(obj.width * (obj.scaleX || 1)),
            height: Math.round(obj.height * (obj.scaleY || 1)),
            fontSize: obj.fontSize || 12,
            fontWeight: obj.fontWeight || 'normal',
            fontFamily: obj.fontFamily || 'Arial'
        };
        
        // Add table-specific properties
        if (obj.fieldType === 'table') {
            field.tableRows = obj.tableRows;
            field.tableColumns = obj.tableColumns;
            field.tableHeaders = obj.tableHeaders;
            field.cellWidth = obj.cellWidth;
            field.cellHeight = obj.cellHeight;
        }
        
        return field;
    });
    
    const template = {
        id: currentTemplate?.id || name.toLowerCase().replace(/\s+/g, '_'),
        name: name,
        fields: fields,
        pageWidth: 612,
        pageHeight: 792
    };
    
    console.log('🔵 Template prepared:', template);
    
    try {
        console.log('🔵 Sending POST request to http://localhost:9000/api/templates/save');
        
        // Save to backend (data/templates folder)
        const response = await fetch('http://localhost:9000/api/templates/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(template)
        });
        
        console.log('🔵 Response received:', response.status, response.statusText);
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Failed to save template to server');
        }
        
        console.log('✅ Template saved to backend:', result);
        
        // Also save to localStorage for quick access
        const saved = TemplateStorage.save(template);
        currentTemplate = saved;
        
        showNotification(`Template "${name}" saved successfully to data/templates!`, 'success');
        
        // Update URL
        if (!window.location.search.includes('id=')) {
            window.history.pushState({}, '', `?id=${saved.id}`);
        }
        
    } catch (error) {
        console.error('❌ Error saving template:', error);
        
        // Fallback: save only to localStorage
        const saved = TemplateStorage.save(template);
        currentTemplate = saved;
        
        showNotification(
            `Template saved to browser storage only. Server error: ${error.message}`,
            'warning'
        );
    }
}

/**
 * Load template from localStorage
 */
function loadTemplate() {
    const templates = TemplateStorage.getAll();
    
    if (templates.length === 0) {
        alert('No templates found. Create a new template first.');
        return;
    }
    
    const list = document.getElementById('templateList');
    list.innerHTML = templates.map(t => `
        <div class="template-item" onclick="loadTemplateById('${t.id}')">
            <h6>${t.name}</h6>
            <small class="text-muted">${t.fields.length} fields</small>
        </div>
    `).join('');
    
    const modal = new bootstrap.Modal(document.getElementById('loadModal'));
    modal.show();
}

/**
 * Load template by ID
 */
function loadTemplateById(id) {
    const template = TemplateStorage.getById(id);
    
    if (!template) {
        alert('Template not found');
        return;
    }
    
    // Clear canvas
    canvas.clear();
    canvas.backgroundColor = '#ffffff';
    
    // Set template name
    document.getElementById('templateName').value = template.name;
    currentTemplate = template;
    
    // Add fields to canvas
    template.fields.forEach(field => {
        let obj;
        
        if (field.type === 'label') {
            obj = new fabric.Text(field.label, {
                left: field.x,
                top: field.y,
                fontSize: field.fontSize || 12,
                fontFamily: field.fontFamily || 'Arial',
                fontWeight: field.fontWeight || 'normal',
                fill: '#000000'
            });
        } else {
            obj = new fabric.Rect({
                left: field.x,
                top: field.y,
                width: field.width,
                height: field.height,
                fill: 'rgba(13, 110, 253, 0.1)',
                stroke: '#0d6efd',
                strokeWidth: 2,
                rx: 5,
                ry: 5
            });
        }
        
        obj.set({
            fieldName: field.name,
            fieldType: field.type,
            fieldLabel: field.label
        });
        
        canvas.add(obj);
    });
    
    canvas.renderAll();
    updateFieldCount();
    
    bootstrap.Modal.getInstance(document.getElementById('loadModal')).hide();
    showNotification(`Template "${template.name}" loaded`, 'success');
    
    // Update URL
    window.history.pushState({}, '', `?id=${id}`);
}

/**
 * Load template from URL parameter
 */
function loadTemplateFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    const id = urlParams.get('id');
    
    if (id) {
        loadTemplateById(id);
    }
}

/**
 * Preview template JSON
 */
function previewTemplate() {
    const objects = canvas.getObjects();
    
    if (objects.length === 0) {
        alert('Canvas is empty. Add some fields first.');
        return;
    }
    
    const fields = objects.map(obj => ({
        name: obj.fieldName || 'unnamed',
        type: obj.fieldType || 'text',
        label: obj.fieldLabel || obj.fieldName,
        x: Math.round(obj.left),
        y: Math.round(obj.top),
        width: Math.round(obj.width * (obj.scaleX || 1)),
        height: Math.round(obj.height * (obj.scaleY || 1))
    }));
    
    const template = {
        name: document.getElementById('templateName').value || 'Untitled',
        fields: fields,
        pageWidth: 612,
        pageHeight: 792
    };
    
    document.getElementById('jsonPreview').textContent = JSON.stringify(template, null, 2);
    
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
    modal.show();
}

/**
 * Copy JSON to clipboard
 */
function copyJSON() {
    const json = document.getElementById('jsonPreview').textContent;
    navigator.clipboard.writeText(json).then(() => {
        showNotification('JSON copied to clipboard', 'success');
    });
}

/**
 * Download JSON as file
 */
function downloadJSON() {
    const json = document.getElementById('jsonPreview').textContent;
    const templateName = document.getElementById('templateName').value || 'template';
    const filename = `${templateName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_template.json`;
    
    // Create blob and download
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showNotification(`JSON file "${filename}" downloaded`, 'success');
}

/**
 * Export template JSON directly (without preview modal)
 */
function exportTemplateJSON() {
    const objects = canvas.getObjects();
    
    if (objects.length === 0) {
        alert('Canvas is empty. Add some fields first.');
        return;
    }
    
    const templateName = document.getElementById('templateName').value || 'template';
    
    const fields = objects.map(obj => {
        const field = {
            name: obj.fieldName || 'unnamed',
            type: obj.fieldType || 'text',
            label: obj.fieldLabel || obj.fieldName,
            x: Math.round(obj.left),
            y: Math.round(obj.top),
            width: Math.round(obj.width * (obj.scaleX || 1)),
            height: Math.round(obj.height * (obj.scaleY || 1)),
            fontSize: obj.fontSize || 12,
            fontWeight: obj.fontWeight || 'normal',
            fontFamily: obj.fontFamily || 'Arial'
        };
        
        // Add table-specific properties
        if (obj.fieldType === 'table') {
            field.tableRows = obj.tableRows;
            field.tableColumns = obj.tableColumns;
            field.tableHeaders = obj.tableHeaders;
            field.cellWidth = obj.cellWidth;
            field.cellHeight = obj.cellHeight;
        }
        
        return field;
    });
    
    const template = {
        name: templateName,
        description: '',
        fields: fields,
        pageWidth: 612,
        pageHeight: 792
    };
    
    const json = JSON.stringify(template, null, 2);
    const filename = `${templateName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_template.json`;
    
    // Create blob and download
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showNotification(`Template exported as "${filename}"`, 'success');
}

/**
 * Import PDF template and extract form fields
 */
async function importPDFTemplate() {
    const fileInput = document.getElementById('pdfFileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        return;
    }
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Please select a PDF file');
        return;
    }
    
    showNotification('Importing PDF template...', 'info');
    
    try {
        // Create FormData
        const formData = new FormData();
        formData.append('file', file);
        
        // Upload and parse PDF
        const response = await axios.post('http://localhost:9000/api/pdf/import', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        
        const template = response.data;
        
        if (template.error) {
            alert(`Error: ${template.message}`);
            return;
        }
        
        // Clear canvas
        canvas.clear();
        canvas.backgroundColor = '#ffffff';
        
        // Set template name
        document.getElementById('templateName').value = template.name;
        
        // Add fields to canvas
        template.fields.forEach(field => {
            const text = new fabric.Text(field.label || field.name, {
                left: field.x,
                top: field.y,
                width: field.width,
                fontSize: field.fontSize || 12,
                fontFamily: field.fontFamily || 'Arial',
                fontWeight: field.fontWeight || 'normal',
                fill: '#000000',
                backgroundColor: '#e3f2fd',
                padding: 5
            });
            
            // Store field metadata
            text.fieldName = field.name;
            text.fieldType = field.type;
            text.fieldLabel = field.label || field.name;
            
            canvas.add(text);
        });
        
        canvas.renderAll();
        updateFieldCount();
        
        showNotification(`Successfully imported ${template.fields.length} fields from PDF`, 'success');
        
    } catch (error) {
        console.error('Error importing PDF:', error);
        let errorMessage = 'Failed to import PDF template';
        
        if (error.response) {
            errorMessage = error.response.data.detail?.message || error.response.data.detail || errorMessage;
        } else if (error.request) {
            errorMessage = 'Cannot connect to backend server. Please ensure the Python backend is running.';
        }
        
        alert(errorMessage);
    } finally {
        // Reset file input
        fileInput.value = '';
    }
}

/**
 * Zoom in
 */
function zoomIn() {
    const zoom = canvas.getZoom();
    canvas.setZoom(zoom * 1.1);
    updateZoomDisplay();
}

/**
 * Zoom out
 */
function zoomOut() {
    const zoom = canvas.getZoom();
    canvas.setZoom(zoom * 0.9);
    updateZoomDisplay();
}

/**
 * Update zoom display
 */
function updateZoomDisplay() {
    const zoom = Math.round(canvas.getZoom() * 100);
    document.getElementById('zoomLevel').textContent = zoom + '%';
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        ${message}
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}
