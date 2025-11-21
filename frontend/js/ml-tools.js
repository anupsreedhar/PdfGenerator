/**
 * ML Tools JavaScript
 * Handles ML-powered PDF analysis features
 */

const API_BASE = 'http://localhost:9000/api';

// ============================================================================
// Utility Functions
// ============================================================================

function showLoading(toolName) {
    document.getElementById(`${toolName}Loading`).classList.add('show');
    document.getElementById(`${toolName}Result`).classList.remove('show');
}

function hideLoading(toolName) {
    document.getElementById(`${toolName}Loading`).classList.remove('show');
}

function showResult(toolName) {
    document.getElementById(`${toolName}Result`).classList.add('show');
}

function showError(message) {
    alert('Error: ' + message);
}

// ============================================================================
// Tool 1: Template Detection
// ============================================================================

function setupTemplateDetection() {
    const dropZone = document.getElementById('detectDropZone');
    const fileInput = document.getElementById('detectFileInput');
    
    // Click to upload
    dropZone.addEventListener('click', () => fileInput.click());
    
    // File selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleTemplateDetection(e.target.files[0]);
        }
    });
    
    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragging');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragging');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragging');
        
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type === 'application/pdf') {
                handleTemplateDetection(file);
            } else {
                showError('Please upload a PDF file');
            }
        }
    });
}

async function handleTemplateDetection(file) {
    showLoading('detect');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await axios.post(`${API_BASE}/ml/detect-template`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        displayDetectionResult(response.data);
        hideLoading('detect');
        showResult('detect');
        
    } catch (error) {
        hideLoading('detect');
        console.error('Detection error:', error);
        showError(error.response?.data?.detail || 'Template detection failed');
    }
}

function displayDetectionResult(data) {
    const container = document.getElementById('detectResultContent');
    
    if (!data.success) {
        container.innerHTML = '<div class="alert alert-danger">Detection failed</div>';
        return;
    }
    
    const confidence = (data.confidence * 100).toFixed(1);
    const confidenceClass = data.confidence > 0.8 ? 'success' : data.confidence > 0.6 ? 'warning' : 'danger';
    
    let html = `
        <div class="text-center mb-4">
            <h3 class="mb-3">${data.template_name || data.template_id}</h3>
            <span class="badge bg-${confidenceClass} confidence-badge">
                ${confidence}% Confidence
            </span>
        </div>
        
        <div class="alert alert-info">
            <strong>Template ID:</strong> ${data.template_id}
        </div>
    `;
    
    // Show all scores
    if (data.all_scores && Object.keys(data.all_scores).length > 0) {
        html += '<h5 class="mt-4 mb-3">All Template Scores:</h5>';
        
        const sortedScores = Object.entries(data.all_scores)
            .sort((a, b) => b[1] - a[1]);
        
        sortedScores.forEach(([templateId, score]) => {
            const scorePercent = (score * 100).toFixed(1);
            const barWidth = score * 100;
            const isMatch = templateId === data.template_id;
            
            html += `
                <div class="mb-3">
                    <div class="d-flex justify-content-between mb-1">
                        <span ${isMatch ? 'class="fw-bold"' : ''}>${templateId}</span>
                        <span>${scorePercent}%</span>
                    </div>
                    <div class="progress">
                        <div class="progress-bar ${isMatch ? 'bg-success' : 'bg-secondary'}" 
                             style="width: ${barWidth}%"></div>
                    </div>
                </div>
            `;
        });
    }
    
    container.innerHTML = html;
}

// ============================================================================
// Tool 2: Data Extraction
// ============================================================================

function setupDataExtraction() {
    const dropZone = document.getElementById('extractDropZone');
    const fileInput = document.getElementById('extractFileInput');
    
    // Click to upload
    dropZone.addEventListener('click', () => fileInput.click());
    
    // File selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleDataExtraction(e.target.files[0]);
        }
    });
    
    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragging');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragging');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragging');
        
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type === 'application/pdf') {
                handleDataExtraction(file);
            } else {
                showError('Please upload a PDF file');
            }
        }
    });
}

async function handleDataExtraction(file) {
    showLoading('extract');
    
    const formData = new FormData();
    formData.append('file', file);
    // Let backend auto-detect template
    
    try {
        const response = await axios.post(`${API_BASE}/ml/extract-data`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        displayExtractionResult(response.data);
        hideLoading('extract');
        showResult('extract');
        
    } catch (error) {
        hideLoading('extract');
        console.error('Extraction error:', error);
        
        // Try to parse error response
        let errorMessage = 'Data extraction failed';
        let errorData = null;
        
        if (error.response?.data) {
            if (typeof error.response.data === 'string') {
                errorMessage = error.response.data;
            } else if (error.response.data.detail) {
                errorMessage = error.response.data.detail;
            } else {
                errorData = error.response.data;
                errorMessage = error.response.data.message || errorMessage;
            }
        }
        
        // Show error in result area instead of alert
        const container = document.getElementById('extractResultContent');
        container.innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="bi bi-exclamation-triangle me-2"></i>Error</h5>
                <p class="mb-0">${errorMessage}</p>
            </div>
        `;
        showResult('extract');
    }
}

function displayExtractionResult(data) {
    const container = document.getElementById('extractResultContent');
    
    if (!data.success) {
        let errorHtml = `
            <div class="alert alert-danger">
                <h5><i class="bi bi-exclamation-triangle me-2"></i>Extraction Failed</h5>
                <p class="mb-2"><strong>Error:</strong> ${data.error || 'Unknown error'}</p>
                <p class="mb-0">${data.message || 'Could not extract data from PDF'}</p>
        `;
        
        // Show available templates if provided
        if (data.available_templates && data.available_templates.length > 0) {
            errorHtml += `
                <hr>
                <p class="mb-1"><strong>Available Templates:</strong></p>
                <ul class="mb-0">
                    ${data.available_templates.map(t => `<li>${t}</li>`).join('')}
                </ul>
            `;
        }
        
        // Show detection details if provided
        if (data.details && data.details.all_scores) {
            errorHtml += `
                <hr>
                <p class="mb-1"><strong>Template Detection Scores:</strong></p>
                <small>
                    ${Object.entries(data.details.all_scores)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 3)
                        .map(([name, score]) => `${name}: ${(score * 100).toFixed(1)}%`)
                        .join(', ')}
                </small>
            `;
        }
        
        errorHtml += `</div>`;
        container.innerHTML = errorHtml;
        return;
    }
    
    let html = `
        <div class="alert alert-success mb-4">
            <strong>Template:</strong> ${data.template_id}<br>
            <strong>Fields Extracted:</strong> ${Object.keys(data.data || {}).length}
        </div>
    `;
    
    if (data.data && Object.keys(data.data).length > 0) {
        html += '<div class="row">';
        
        Object.entries(data.data).forEach(([fieldName, value]) => {
            // Format field name (remove underscores, capitalize)
            const displayName = fieldName
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
            
            html += `
                <div class="col-md-6 mb-3">
                    <div class="field-item">
                        <div class="field-label">${displayName}</div>
                        <div class="field-value">${value || '(empty)'}</div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        
        // Add copy button
        html += `
            <div class="mt-3">
                <button class="btn btn-outline-primary" onclick="copyExtractedData()">
                    <i class="bi bi-clipboard me-2"></i>Copy as JSON
                </button>
            </div>
        `;
        
        // Store data for copying
        window.lastExtractedData = data.data;
        
    } else {
        html += '<div class="alert alert-warning">No data could be extracted</div>';
    }
    
    container.innerHTML = html;
}

function copyExtractedData() {
    if (window.lastExtractedData) {
        const json = JSON.stringify(window.lastExtractedData, null, 2);
        navigator.clipboard.writeText(json).then(() => {
            alert('Data copied to clipboard!');
        });
    }
}

// ============================================================================
// Tool 3: Auto-Generate Template
// ============================================================================

function setupAutoGenerate() {
    const dropZone = document.getElementById('generateDropZone');
    const fileInput = document.getElementById('generateFileInput');
    const saveBtn = document.getElementById('saveTemplateBtn');
    
    // Click to upload
    dropZone.addEventListener('click', () => fileInput.click());
    
    // File selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleAutoGenerate(e.target.files[0]);
        }
    });
    
    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragging');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragging');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragging');
        
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type === 'application/pdf') {
                handleAutoGenerate(file);
            } else {
                showError('Please upload a PDF file');
            }
        }
    });
    
    // Save template button
    saveBtn.addEventListener('click', saveGeneratedTemplate);
}

async function handleAutoGenerate(file) {
    showLoading('generate');
    
    const templateName = document.getElementById('templateNameInput').value || 
                        file.name.replace('.pdf', '');
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('template_name', templateName);
    
    try {
        const response = await axios.post(`${API_BASE}/ml/auto-generate-template`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        displayGenerateResult(response.data);
        hideLoading('generate');
        showResult('generate');
        
    } catch (error) {
        hideLoading('generate');
        console.error('Generation error:', error);
        showError(error.response?.data?.detail || 'Template generation failed');
    }
}

function displayGenerateResult(data) {
    const container = document.getElementById('generateResultContent');
    
    if (!data.success) {
        container.innerHTML = '<div class="alert alert-danger">Template generation failed</div>';
        return;
    }
    
    const template = data.template;
    const fieldCount = template.fields ? template.fields.length : 0;
    
    let html = `
        <div class="alert alert-success mb-4">
            <strong>Template Name:</strong> ${template.name}<br>
            <strong>Fields Detected:</strong> ${fieldCount}<br>
            <strong>Page Size:</strong> ${template.width} x ${template.height}
        </div>
    `;
    
    if (fieldCount > 0) {
        html += '<h6 class="mb-3">Detected Fields:</h6>';
        html += '<div class="row">';
        
        template.fields.forEach((field, index) => {
            const typeIcon = field.type === 'text' ? 'bi-fonts' :
                           field.type === 'checkbox' ? 'bi-check-square' :
                           field.type === 'table' ? 'bi-table' : 'bi-circle';
            
            html += `
                <div class="col-md-6 mb-3">
                    <div class="field-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <i class="bi ${typeIcon} me-2"></i>
                                <strong>${field.name || `Field ${index + 1}`}</strong>
                            </div>
                            <span class="badge bg-secondary">${field.type}</span>
                        </div>
                        <small class="text-muted">
                            Position: (${Math.round(field.x)}, ${Math.round(field.y)})
                            ${field.width ? ` • Size: ${Math.round(field.width)}x${Math.round(field.height)}` : ''}
                        </small>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    // Store template for saving
    window.generatedTemplate = template;
    
    container.innerHTML = html;
}

function saveGeneratedTemplate() {
    if (!window.generatedTemplate) {
        showError('No template to save');
        return;
    }
    
    const template = window.generatedTemplate;
    
    // Save to localStorage
    try {
        localStorage.setItem(template.id, JSON.stringify(template));
        
        alert(`✅ Template "${template.name}" saved successfully!\n\nYou can now use it in the Generate page.`);
        
        // Optionally navigate to designer
        if (confirm('Would you like to edit this template in the Designer?')) {
            window.location.href = `designer.html?template=${template.id}`;
        }
        
    } catch (error) {
        console.error('Save error:', error);
        showError('Failed to save template: ' + error.message);
    }
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    setupTemplateDetection();
    setupDataExtraction();
    setupAutoGenerate();
    
    console.log('ML Tools initialized');
});
