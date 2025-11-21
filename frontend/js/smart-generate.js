/**
 * Smart Generate JavaScript
 * ML-Powered PDF generation by template name
 */

const API_BASE = 'http://localhost:9000/api';

let selectedTemplate = null;
let allTemplates = [];

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('Smart Generate initialized');
    await loadTemplates();
    
    // Setup generate button
    document.getElementById('generateBtn').addEventListener('click', generatePDF);
});

// ============================================================================
// Load Templates from ML Model
// ============================================================================

async function loadTemplates() {
    const loadingDiv = document.getElementById('templatesLoading');
    const noTemplatesDiv = document.getElementById('noTemplates');
    const gridDiv = document.getElementById('templatesGrid');
    
    try {
        const response = await axios.get(`${API_BASE}/ml/templates`);
        const data = response.data;
        
        loadingDiv.style.display = 'none';
        
        if (!data.success || !data.templates || data.templates.length === 0) {
            noTemplatesDiv.style.display = 'block';
            return;
        }
        
        allTemplates = data.templates;
        displayTemplates(allTemplates);
        
    } catch (error) {
        console.error('Error loading templates:', error);
        loadingDiv.style.display = 'none';
        noTemplatesDiv.style.display = 'block';
        
        if (error.response?.status === 404) {
            noTemplatesDiv.innerHTML = `
                <h5><i class="bi bi-exclamation-triangle me-2"></i>No Trained Model Found</h5>
                <p>Please train the ML model first to use Smart Generate.</p>
                <a href="train.html" class="btn btn-warning">
                    <i class="bi bi-mortarboard me-2"></i>Train Model Now
                </a>
            `;
        }
    }
}

function displayTemplates(templates) {
    const gridDiv = document.getElementById('templatesGrid');
    gridDiv.innerHTML = '';
    
    templates.forEach(template => {
        const card = document.createElement('div');
        card.className = 'col-md-4 col-lg-3';
        
        const icon = getTemplateIcon(template.name);
        
        card.innerHTML = `
            <div class="card template-card" data-template-id="${template.id}">
                <div class="card-body text-center">
                    <div class="template-icon mb-3">
                        <i class="bi bi-${icon}"></i>
                    </div>
                    <h5 class="card-title">${template.name}</h5>
                    <p class="text-muted mb-2">
                        <i class="bi bi-input-cursor me-1"></i>
                        ${template.field_count} fields
                    </p>
                    <p class="text-muted small mb-0">
                        ${template.width} × ${template.height}
                    </p>
                </div>
            </div>
        `;
        
        card.querySelector('.template-card').addEventListener('click', () => {
            selectTemplate(template);
        });
        
        gridDiv.appendChild(card);
    });
}

function getTemplateIcon(templateName) {
    const name = templateName.toLowerCase();
    
    if (name.includes('invoice')) return 'receipt';
    if (name.includes('form') || name.includes('employee')) return 'person-badge';
    if (name.includes('report')) return 'file-earmark-text';
    if (name.includes('letter')) return 'envelope';
    if (name.includes('certificate')) return 'award';
    if (name.includes('contract')) return 'file-earmark-ruled';
    
    return 'file-earmark-pdf';
}

// ============================================================================
// Template Selection
// ============================================================================

function selectTemplate(template) {
    selectedTemplate = template;
    
    // Update UI - highlight selected card
    document.querySelectorAll('.template-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    const selectedCard = document.querySelector(`[data-template-id="${template.id}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
    
    // Show field inputs section
    document.getElementById('fieldInputsSection').classList.add('show');
    
    // Generate field inputs
    generateFieldInputs(template);
    
    // Scroll to fields
    setTimeout(() => {
        document.getElementById('fieldInputsSection').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }, 100);
}

// ============================================================================
// Generate Field Inputs
// ============================================================================

function generateFieldInputs(template) {
    const container = document.getElementById('fieldInputs');
    container.innerHTML = '';
    
    if (!template.fields || template.fields.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    This template has no fields defined. The AI will generate a basic PDF.
                </div>
            </div>
        `;
        return;
    }
    
    template.fields.forEach(field => {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'col-md-6';
        
        const fieldName = field.name;
        const fieldType = field.type || 'text';
        const displayName = formatFieldName(fieldName);
        const isRequired = field.required || false;
        
        let inputHtml = '';
        
        switch (fieldType) {
            case 'checkbox':
                inputHtml = `
                    <div class="form-check form-switch">
                        <input class="form-check-input field-input" 
                               type="checkbox" 
                               id="field_${fieldName}" 
                               data-field-name="${fieldName}"
                               data-field-type="${fieldType}">
                        <label class="form-check-label" for="field_${fieldName}">
                            ${displayName} ${isRequired ? '<span class="text-danger">*</span>' : ''}
                        </label>
                    </div>
                `;
                break;
                
            case 'date':
                inputHtml = `
                    <label for="field_${fieldName}" class="form-label">
                        ${displayName} ${isRequired ? '<span class="text-danger">*</span>' : ''}
                    </label>
                    <input type="date" 
                           class="form-control field-input" 
                           id="field_${fieldName}" 
                           data-field-name="${fieldName}"
                           data-field-type="${fieldType}"
                           placeholder="Auto-filled if empty">
                `;
                break;
                
            case 'number':
                inputHtml = `
                    <label for="field_${fieldName}" class="form-label">
                        ${displayName} ${isRequired ? '<span class="text-danger">*</span>' : ''}
                    </label>
                    <input type="number" 
                           class="form-control field-input" 
                           id="field_${fieldName}" 
                           data-field-name="${fieldName}"
                           data-field-type="${fieldType}"
                           placeholder="Auto-filled with 0 if empty">
                `;
                break;
                
            case 'textarea':
                inputHtml = `
                    <label for="field_${fieldName}" class="form-label">
                        ${displayName} ${isRequired ? '<span class="text-danger">*</span>' : ''}
                    </label>
                    <textarea class="form-control field-input" 
                              id="field_${fieldName}" 
                              data-field-name="${fieldName}"
                              data-field-type="${fieldType}"
                              rows="3"
                              placeholder="Auto-filled with empty if not provided"></textarea>
                `;
                break;
                
            default: // text
                inputHtml = `
                    <label for="field_${fieldName}" class="form-label">
                        ${displayName} ${isRequired ? '<span class="text-danger">*</span>' : ''}
                    </label>
                    <input type="text" 
                           class="form-control field-input" 
                           id="field_${fieldName}" 
                           data-field-name="${fieldName}"
                           data-field-type="${fieldType}"
                           placeholder="Auto-filled with empty if not provided">
                `;
        }
        
        fieldDiv.innerHTML = `
            <div class="field-input-group">
                ${inputHtml}
                <small class="text-muted">
                    <i class="bi bi-tag me-1"></i>Type: ${fieldType}
                </small>
            </div>
        `;
        
        container.appendChild(fieldDiv);
    });
}

function formatFieldName(fieldName) {
    // Convert snake_case or camelCase to Title Case
    return fieldName
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
        .trim();
}

// ============================================================================
// Generate PDF
// ============================================================================

async function generatePDF() {
    if (!selectedTemplate) {
        alert('Please select a template first');
        return;
    }
    
    // Collect field data
    const data = {};
    const fieldInputs = document.querySelectorAll('.field-input');
    
    fieldInputs.forEach(input => {
        const fieldName = input.dataset.fieldName;
        const fieldType = input.dataset.fieldType;
        
        if (fieldType === 'checkbox') {
            data[fieldName] = input.checked;
        } else if (input.value) {
            data[fieldName] = input.value;
        }
        // Don't include empty fields - let backend auto-fill
    });
    
    console.log('Generating PDF with data:', data);
    
    // Show loading overlay
    document.getElementById('loadingOverlay').classList.add('show');
    
    try {
        const response = await axios.post(
            `${API_BASE}/ml/smart-generate`,
            {
                template_name: selectedTemplate.id,
                data: data
            },
            {
                responseType: 'blob'
            }
        );
        
        // Download PDF
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedTemplate.name.replace(/\s+/g, '_')}_${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // Success message
        showSuccess('PDF generated successfully!');
        
    } catch (error) {
        console.error('Generation error:', error);
        let errorMessage = 'Failed to generate PDF';
        
        if (error.response?.data) {
            // Try to read error message from blob
            const reader = new FileReader();
            reader.onload = () => {
                try {
                    const errorData = JSON.parse(reader.result);
                    alert('Error: ' + (errorData.detail || errorMessage));
                } catch {
                    alert('Error: ' + errorMessage);
                }
            };
            reader.readAsText(error.response.data);
        } else {
            alert('Error: ' + errorMessage);
        }
        
    } finally {
        // Hide loading overlay
        document.getElementById('loadingOverlay').classList.remove('show');
    }
}

function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    alertDiv.style.zIndex = '10000';
    alertDiv.innerHTML = `
        <i class="bi bi-check-circle me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}
