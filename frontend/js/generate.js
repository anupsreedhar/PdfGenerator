/**
 * PDF Generator - Fill data and generate PDF
 */

let selectedTemplate = null;
let apiUrl = 'http://localhost:9000/api/pdf/generate-json';

// Load on page ready
document.addEventListener('DOMContentLoaded', () => {
    loadTemplatesList();
    loadConfig();
    loadTemplateFromURL();
});

/**
 * Load all templates into list
 */
function loadTemplatesList() {
    const templates = TemplateStorage.getAll();
    const list = document.getElementById('templatesList');
    const noTemplates = document.getElementById('noTemplates');

    if (templates.length === 0) {
        list.innerHTML = '';
        noTemplates.style.display = 'block';
        return;
    }

    noTemplates.style.display = 'none';
    
    list.innerHTML = templates.map(t => `
        <div class="template-item" onclick="selectTemplate('${t.id}')" id="tpl-${t.id}">
            <h6><i class="fas fa-file-alt"></i> ${escapeHtml(t.name)}</h6>
            <small class="text-muted">
                ${t.fields.length} field${t.fields.length !== 1 ? 's' : ''}
            </small>
        </div>
    `).join('');
}

/**
 * Filter templates by search
 */
function filterTemplates() {
    const query = document.getElementById('templateSearch').value.toLowerCase();
    const items = document.querySelectorAll('.template-item');
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(query) ? 'block' : 'none';
    });
}

/**
 * Select a template
 */
function selectTemplate(id) {
    const template = TemplateStorage.getById(id);
    
    if (!template) {
        alert('Template not found');
        return;
    }

    selectedTemplate = template;
    
    // Update UI
    document.querySelectorAll('.template-item').forEach(item => {
        item.classList.remove('selected');
    });
    document.getElementById(`tpl-${id}`).classList.add('selected');
    
    // Show template preview
    document.getElementById('templatePreview').style.display = 'block';
    document.getElementById('previewName').textContent = template.name;
    document.getElementById('previewFields').textContent = template.fields.length;
    document.getElementById('previewDate').textContent = formatDate(template.createdAt);
    
    // Generate form
    generateForm(template);
}

/**
 * Load template from URL
 */
function loadTemplateFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    const id = urlParams.get('template');
    
    if (id) {
        selectTemplate(id);
    }
}

/**
 * Generate data entry form
 */
function generateForm(template) {
    const formFields = document.getElementById('formFields');
    const dataForm = document.getElementById('dataForm');
    const selectMessage = document.getElementById('selectTemplateMessage');
    
    selectMessage.style.display = 'none';
    dataForm.style.display = 'block';
    
    // Generate form fields
    formFields.innerHTML = template.fields
        .filter(field => field.type !== 'label') // Skip labels
        .map(field => {
            const inputId = `data_${field.name}`;
            
            let inputHtml = '';
            
            switch(field.type) {
                case 'text':
                    inputHtml = `
                        <input type="text" class="form-control" id="${inputId}" 
                               placeholder="Enter ${field.label}">
                    `;
                    break;
                    
                case 'number':
                    inputHtml = `
                        <input type="number" class="form-control" id="${inputId}" 
                               placeholder="Enter ${field.label}">
                    `;
                    break;
                    
                case 'date':
                    inputHtml = `
                        <input type="date" class="form-control" id="${inputId}">
                    `;
                    break;
                    
                case 'checkbox':
                    inputHtml = `
                        <div class="form-check">
                            <input type="checkbox" class="form-check-input" id="${inputId}">
                            <label class="form-check-label" for="${inputId}">
                                ${field.label}
                            </label>
                        </div>
                    `;
                    break;
                    
                case 'table':
                    inputHtml = generateTableInput(field, inputId);
                    break;
                    
                default:
                    inputHtml = `
                        <input type="text" class="form-control" id="${inputId}" 
                               placeholder="Enter ${field.label}">
                    `;
            }
            
            // Tables take full width
            const colClass = field.type === 'table' ? 'col-md-12' : 'col-md-6';
            
            return `
                <div class="${colClass}">
                    <label class="form-label" for="${inputId}">
                        ${field.label}
                        ${field.type === 'checkbox' || field.type === 'table' ? '' : ':'}
                    </label>
                    ${inputHtml}
                </div>
            `;
        }).join('');
}

/**
 * Generate table input HTML
 */
function generateTableInput(field, inputId) {
    const rows = field.tableRows || 3;
    const columns = field.tableColumns || 3;
    const headers = field.tableHeaders || [];
    
    let tableHtml = `
        <div class="table-responsive">
            <table class="table table-bordered table-sm" id="${inputId}">
                ${headers.length > 0 ? `
                    <thead class="table-light">
                        <tr>
                            ${headers.map(header => `<th>${header}</th>`).join('')}
                        </tr>
                    </thead>
                ` : ''}
                <tbody>
    `;
    
    for (let row = 0; row < rows; row++) {
        tableHtml += '<tr>';
        for (let col = 0; col < columns; col++) {
            const cellId = `${inputId}_${row}_${col}`;
            const placeholder = headers[col] || `Col ${col + 1}`;
            tableHtml += `
                <td>
                    <input type="text" class="form-control form-control-sm" 
                           id="${cellId}" 
                           placeholder="${placeholder}"
                           data-row="${row}" 
                           data-col="${col}">
                </td>
            `;
        }
        tableHtml += '</tr>';
    }
    
    tableHtml += `
                </tbody>
            </table>
        </div>
        <small class="text-muted">
            <i class="fas fa-info-circle"></i> 
            Fill in the table data. Empty cells will be left blank in the PDF.
        </small>
    `;
    
    return tableHtml;
}

/**
 * Collect form data
 */
function collectFormData() {
    if (!selectedTemplate) {
        throw new Error('No template selected');
    }
    
    const data = {};
    
    selectedTemplate.fields.forEach(field => {
        if (field.type === 'label') return; // Skip labels
        
        const inputId = `data_${field.name}`;
        
        if (field.type === 'table') {
            // Collect table data
            data[field.name] = collectTableData(field, inputId);
        } else {
            const input = document.getElementById(inputId);
            
            if (input) {
                if (field.type === 'checkbox') {
                    // Only send 'Yes' if checked, empty string if not
                    data[field.name] = input.checked ? 'Yes' : '';
                } else {
                    data[field.name] = input.value;
                }
            }
        }
    });
    
    return data;
}

/**
 * Collect table data from input fields
 */
function collectTableData(field, inputId) {
    const rows = field.tableRows || 3;
    const columns = field.tableColumns || 3;
    const headers = field.tableHeaders || [];
    const tableData = [];
    
    for (let row = 0; row < rows; row++) {
        const rowData = [];
        let hasData = false;
        
        for (let col = 0; col < columns; col++) {
            const cellId = `${inputId}_${row}_${col}`;
            const cellInput = document.getElementById(cellId);
            const cellValue = cellInput ? cellInput.value.trim() : '';
            
            rowData.push(cellValue);
            if (cellValue) hasData = true;
        }
        
        // Only include rows that have at least one non-empty cell
        if (hasData) {
            tableData.push(rowData);
        }
    }
    
    return tableData;
}

/**
 * Generate PDF
 */
async function generatePDF() {
    if (!selectedTemplate) {
        alert('Please select a template first');
        return;
    }

    try {
        // Collect data
        const data = collectFormData();
        
        // Validate data
        const hasData = Object.values(data).some(v => v && v.trim());
        if (!hasData) {
            if (!confirm('All fields are empty. Generate blank PDF anyway?')) {
                return;
            }
        }

        // Show progress
        document.getElementById('dataForm').style.display = 'none';
        document.getElementById('progressIndicator').style.display = 'block';
        document.getElementById('errorMessage').style.display = 'none';
        document.getElementById('successMessage').style.display = 'none';

        // Prepare request with proper structure
        const request = {
            template: {
                name: selectedTemplate.name,
                fields: selectedTemplate.fields,
                pageWidth: selectedTemplate.pageWidth || 612,
                pageHeight: selectedTemplate.pageHeight || 792,
                pdfFilePath: selectedTemplate.pdfFilePath || null
            },
            data: data
        };

        // Call API with JSON
        const response = await axios.post(apiUrl, request, {
            responseType: 'blob',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        // Download PDF
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${selectedTemplate.name}_${Date.now()}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        // Save to recent
        TemplateStorage.saveRecentGeneration({
            templateId: selectedTemplate.id,
            templateName: selectedTemplate.name,
            data: data
        });

        // Show success
        document.getElementById('progressIndicator').style.display = 'none';
        document.getElementById('successMessage').style.display = 'block';
        document.getElementById('dataForm').style.display = 'block';

        // Update recent list
        updateRecentList();

        setTimeout(() => {
            document.getElementById('successMessage').style.display = 'none';
        }, 5000);

    } catch (error) {
        console.error('PDF generation failed:', error);
        
        document.getElementById('progressIndicator').style.display = 'none';
        document.getElementById('dataForm').style.display = 'block';
        
        const errorText = document.getElementById('errorText');
        
        if (error.response) {
            errorText.textContent = `Server error: ${error.response.status} - ${error.response.statusText}`;
        } else if (error.request) {
            errorText.textContent = 'Cannot connect to server. Is the backend running?';
        } else {
            errorText.textContent = error.message;
        }
        
        document.getElementById('errorMessage').style.display = 'block';
    }
}

/**
 * Clear form
 */
function clearForm() {
    if (confirm('Clear all entered data?')) {
        selectedTemplate.fields.forEach(field => {
            const inputId = `data_${field.name}`;
            const input = document.getElementById(inputId);
            
            if (input) {
                if (field.type === 'checkbox') {
                    input.checked = false;
                } else {
                    input.value = '';
                }
            }
        });
    }
}

/**
 * Load sample data
 */
function loadSampleData() {
    if (!selectedTemplate) return;
    
    selectedTemplate.fields.forEach(field => {
        const inputId = `data_${field.name}`;
        
        if (field.type === 'table') {
            // Load sample table data
            const rows = field.tableRows || 3;
            const columns = field.tableColumns || 3;
            
            for (let row = 0; row < Math.min(rows, 3); row++) {
                for (let col = 0; col < columns; col++) {
                    const cellId = `${inputId}_${row}_${col}`;
                    const cellInput = document.getElementById(cellId);
                    if (cellInput) {
                        cellInput.value = `Row ${row + 1} Col ${col + 1}`;
                    }
                }
            }
        } else {
            const input = document.getElementById(inputId);
            
            if (!input) return;
            
            switch(field.type) {
                case 'text':
                    input.value = `Sample ${field.label}`;
                    break;
                case 'number':
                    input.value = Math.floor(Math.random() * 1000);
                    break;
                case 'date':
                    input.value = new Date().toISOString().split('T')[0];
                    break;
                case 'checkbox':
                    input.checked = Math.random() > 0.5;
                    break;
            }
        }
    });
    
    showNotification('Sample data loaded', 'info');
}

/**
 * Load data from JSON file
 */
function loadDataFromJSON() {
    const fileInput = document.getElementById('jsonFileInput');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const jsonData = JSON.parse(e.target.result);
            
            // Populate form with JSON data
            Object.keys(jsonData).forEach(key => {
                const inputId = `data_${key}`;
                
                // Find the field in the template to check its type
                const field = selectedTemplate ? selectedTemplate.fields.find(f => f.name === key) : null;
                
                if (field && field.type === 'table') {
                    // Handle table data (array of arrays or array of objects)
                    const tableData = jsonData[key];
                    
                    if (Array.isArray(tableData)) {
                        tableData.forEach((row, rowIndex) => {
                            if (Array.isArray(row)) {
                                // Array of arrays format
                                row.forEach((cellValue, colIndex) => {
                                    const cellId = `${inputId}_${rowIndex}_${colIndex}`;
                                    const cellInput = document.getElementById(cellId);
                                    if (cellInput) {
                                        cellInput.value = cellValue;
                                    }
                                });
                            } else if (typeof row === 'object') {
                                // Array of objects format
                                Object.values(row).forEach((cellValue, colIndex) => {
                                    const cellId = `${inputId}_${rowIndex}_${colIndex}`;
                                    const cellInput = document.getElementById(cellId);
                                    if (cellInput) {
                                        cellInput.value = cellValue;
                                    }
                                });
                            }
                        });
                    }
                } else {
                    // Handle regular input fields
                    const input = document.getElementById(inputId);
                    
                    if (input) {
                        if (input.type === 'checkbox') {
                            input.checked = jsonData[key] === true || 
                                           jsonData[key] === 'true' || 
                                           jsonData[key] === 'Yes';
                        } else {
                            input.value = jsonData[key];
                        }
                    }
                }
            });
            
            showNotification('Data loaded from JSON file', 'success');
        } catch (error) {
            alert('Invalid JSON file: ' + error.message);
        }
    };
    
    reader.readAsText(file);
}

/**
 * Export current form data as JSON
 */
function exportDataJSON() {
    if (!selectedTemplate) {
        alert('Please select a template first');
        return;
    }
    
    const data = collectFormData();
    const json = JSON.stringify(data, null, 2);
    
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedTemplate.name}_data_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showNotification('Data exported as JSON', 'success');
}

/**
 * Update recent generations list
 */
function updateRecentList() {
    const recent = TemplateStorage.getRecentGenerations();
    const list = document.getElementById('recentList');
    
    if (recent.length === 0) {
        list.innerHTML = '<p class="text-muted small mb-0">No recent generations</p>';
        return;
    }
    
    list.innerHTML = recent.slice(0, 5).map(r => `
        <div class="list-group-item">
            <div class="d-flex justify-content-between">
                <strong>${escapeHtml(r.templateName)}</strong>
                <small class="text-muted">${formatDate(r.timestamp)}</small>
            </div>
        </div>
    `).join('');
}

/**
 * Load config
 */
function loadConfig() {
    const saved = localStorage.getItem('pdf_api_url');
    if (saved) {
        // Auto-migrate old port 8000 to new port 9000
        if (saved.includes(':8000')) {
            apiUrl = saved.replace(':8000', ':9000');
            localStorage.setItem('pdf_api_url', apiUrl);
        } else {
            apiUrl = saved;
        }
        document.getElementById('apiUrl').value = apiUrl;
    }
    updateRecentList();
}

/**
 * Save config
 */
function saveConfig() {
    apiUrl = document.getElementById('apiUrl').value;
    localStorage.setItem('pdf_api_url', apiUrl);
    showNotification('Configuration saved', 'success');
    bootstrap.Modal.getInstance(document.getElementById('configModal')).hide();
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    
    return date.toLocaleDateString();
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
