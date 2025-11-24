/**
 * ML Training Interface & AI PDF Import
 */

let trainingApiUrl = 'http://localhost:9000/api/train';
let importApiUrl = 'http://localhost:9000/api/pdf/import-ai';
let trainingInterval = null;

// Load on page ready
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    updateStatus();
});

/**
 * Update training status
 */
function updateStatus() {
    const templates = TemplateStorage.getAll();
    document.getElementById('templateCount').textContent = templates.length;
    
    // Check if model exists
    const modelInfo = localStorage.getItem('ml_model_info');
    if (modelInfo) {
        const info = JSON.parse(modelInfo);
        document.getElementById('modelStatus').textContent = 'Trained';
        document.getElementById('modelStatus').className = 'badge bg-success';
        document.getElementById('lastTrained').textContent = formatDate(info.trainedAt);
        
        // Show model info card
        document.getElementById('modelInfoCard').style.display = 'block';
        document.getElementById('modelAccuracy').textContent = info.accuracy || 'N/A';
        document.getElementById('modelEpochs').textContent = info.epochs || 'N/A';
        document.getElementById('modelTemplates').textContent = info.templateCount || 'N/A';
    }
}

/**
 * Start ML training
 */
async function startTraining() {
    const templates = TemplateStorage.getAll();
    
    if (templates.length === 0) {
        alert('No templates found! Please create at least one template first.');
        window.location.href = 'designer.html';
        return;
    }
    
    if (templates.length < 3) {
        if (!confirm(`Only ${templates.length} template(s) found. For better results, create at least 5 templates.\n\nContinue anyway?`)) {
            return;
        }
    }
    
    // Get training parameters
    const epochs = parseInt(document.getElementById('epochs').value);
    const batchSize = parseInt(document.getElementById('batchSize').value);
    const generateSamples = document.getElementById('generateSamples').checked;
    
    // Hide form elements, show progress
    const epochsInput = document.getElementById('epochs');
    const batchSizeInput = document.getElementById('batchSize');
    const generateSamplesInput = document.getElementById('generateSamples');
    const startButton = event ? event.target : document.querySelector('button[onclick="startTraining()"]');
    
    // Hide form controls
    if (epochsInput) epochsInput.closest('.mb-3').style.display = 'none';
    if (batchSizeInput) batchSizeInput.closest('.mb-3').style.display = 'none';
    if (generateSamplesInput) generateSamplesInput.closest('.form-check').style.display = 'none';
    if (startButton) startButton.style.display = 'none';
    
    // Show/hide sections
    const progressSection = document.getElementById('trainingProgress');
    const errorSection = document.getElementById('trainingError');
    const completeSection = document.getElementById('trainingComplete');
    
    if (progressSection) progressSection.style.display = 'block';
    if (errorSection) errorSection.style.display = 'none';
    if (completeSection) completeSection.style.display = 'none';
    
    // Clear log
    document.getElementById('trainingLog').innerHTML = '';
    
    try {
        logMessage('🚀 Starting ML training...');
        logMessage(`📊 Templates: ${templates.length}`);
        logMessage(`⚙️ Epochs: ${epochs}, Batch Size: ${batchSize}`);
        logMessage('');
        
        // Prepare training data
        const trainingData = {
            templates: templates,
            config: {
                epochs: epochs,
                batch_size: batchSize,
                generate_synthetic: generateSamples,
                min_templates: 10
            }
        };
        
        logMessage('📤 Sending templates to backend...');
        updateProgress(10, 'Uploading templates...');
        
        // Call training API
        const response = await axios.post(trainingApiUrl, trainingData, {
            headers: {
                'Content-Type': 'application/json'
            },
            onUploadProgress: (progressEvent) => {
                const percent = Math.round((progressEvent.loaded * 10) / progressEvent.total);
                updateProgress(percent, 'Uploading templates...');
            }
        });
        
        logMessage('✅ Templates uploaded successfully');
        updateProgress(20, 'Preparing training data...');
        
        // Start polling for progress
        const taskId = response.data.task_id;
        if (taskId) {
            await pollTrainingProgress(taskId);
        } else {
            // Training completed immediately - extract result from response
            handleTrainingComplete(response.data.result);
        }
        
    } catch (error) {
        console.error('Training failed:', error);
        handleTrainingError(error);
    }
}

/**
 * Poll training progress
 */
async function pollTrainingProgress(taskId) {
    const statusUrl = trainingApiUrl.replace('/train', `/train/status/${taskId}`);
    
    trainingInterval = setInterval(async () => {
        try {
            const response = await axios.get(statusUrl);
            const status = response.data;
            
            if (status.status === 'running') {
                updateProgress(status.progress || 50, status.message || 'Training...');
                if (status.log) {
                    logMessage(status.log);
                }
            } else if (status.status === 'complete') {
                clearInterval(trainingInterval);
                handleTrainingComplete(status.result);
            } else if (status.status === 'error') {
                clearInterval(trainingInterval);
                throw new Error(status.error);
            }
        } catch (error) {
            clearInterval(trainingInterval);
            handleTrainingError(error);
        }
    }, 2000); // Poll every 2 seconds
}

/**
 * Handle training completion
 */
function handleTrainingComplete(result) {
    console.log('🔍 Training result received:', result);
    console.log('🔍 Result keys:', Object.keys(result));
    console.log('🔍 Accuracy:', result.accuracy);
    console.log('🔍 Epochs:', result.epochs);
    console.log('🔍 Training time:', result.training_time);
    
    logMessage('');
    logMessage('✅ Training completed successfully!');
    logMessage(`📈 Final Accuracy: ${result.accuracy || 'N/A'}`);
    logMessage(`⏱️ Training Time: ${result.training_time || 'N/A'}`);
    
    updateProgress(100, 'Complete!');
    
    // Save model info
    const modelInfo = {
        trainedAt: new Date().toISOString(),
        accuracy: result.accuracy,
        epochs: result.epochs,
        templateCount: result.template_count,
        trainingTime: result.training_time
    };
    localStorage.setItem('ml_model_info', JSON.stringify(modelInfo));
    
    // Show complete screen
    setTimeout(() => {
        document.getElementById('trainingProgress').style.display = 'none';
        document.getElementById('trainingComplete').style.display = 'block';
        
        document.getElementById('finalAccuracy').textContent = result.accuracy || 'N/A';
        document.getElementById('finalEpochs').textContent = result.epochs || 'N/A';
        document.getElementById('finalTime').textContent = result.training_time || 'N/A';
        
        updateStatus();
    }, 1000);
}

/**
 * Handle training error
 */
function handleTrainingError(error) {
    document.getElementById('trainingProgress').style.display = 'none';
    document.getElementById('trainingError').style.display = 'block';
    
    let errorMsg = 'Unknown error occurred';
    
    if (error.response) {
        errorMsg = `Server error: ${error.response.status} - ${error.response.data.detail || error.response.statusText}`;
    } else if (error.request) {
        errorMsg = 'Cannot connect to backend server. Please ensure the Python backend is running.';
    } else {
        errorMsg = error.message;
    }
    
    document.getElementById('errorMessage').textContent = errorMsg;
    logMessage('❌ Error: ' + errorMsg);
}

/**
 * Update progress bar
 */
function updateProgress(percent, message) {
    const progressBar = document.getElementById('progressBar');
    progressBar.style.width = percent + '%';
    progressBar.textContent = percent + '%';
    
    if (message) {
        document.getElementById('progressText').textContent = message;
    }
}

/**
 * Log message to training log
 */
function logMessage(message) {
    const log = document.getElementById('trainingLog');
    const timestamp = new Date().toLocaleTimeString();
    log.innerHTML += `[${timestamp}] ${message}\n`;
    log.scrollTop = log.scrollHeight;
}

/**
 * Reset training UI
 */
function resetTraining() {
    document.getElementById('trainingForm').style.display = 'block';
    document.getElementById('trainingProgress').style.display = 'none';
    document.getElementById('trainingComplete').style.display = 'none';
    document.getElementById('trainingError').style.display = 'none';
    
    if (trainingInterval) {
        clearInterval(trainingInterval);
    }
}

/**
 * Load config
 */
function loadConfig() {
    const saved = localStorage.getItem('ml_training_api_url');
    if (saved) {
        // Auto-migrate old port 8000 to new port 9000
        if (saved.includes(':8000')) {
            trainingApiUrl = saved.replace(':8000', ':9000');
            localStorage.setItem('ml_training_api_url', trainingApiUrl);
        } else {
            trainingApiUrl = saved;
        }
        document.getElementById('trainingApiUrl').value = trainingApiUrl;
    }
}

/**
 * Save training config
 */
function saveTrainingConfig() {
    trainingApiUrl = document.getElementById('trainingApiUrl').value;
    localStorage.setItem('ml_training_api_url', trainingApiUrl);
    showNotification('Configuration saved', 'success');
    bootstrap.Modal.getInstance(document.getElementById('configModal')).hide();
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
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

// ============================================================================
// AI PDF Import Functions
// ============================================================================

/**
 * Import PDF with AI
 */
async function importWithAI() {
    const fileInput = document.getElementById('pdfFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a PDF file first');
        return;
    }
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Please select a valid PDF file');
        return;
    }
    
    // Hide previous results
    document.getElementById('aiResults').style.display = 'none';
    document.getElementById('aiError').style.display = 'none';
    
    // Show progress
    document.getElementById('aiProgress').style.display = 'block';
    document.getElementById('importBtn').disabled = true;
    
    updateAIProgress(20, 'Uploading PDF...');
    
    try {
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        
        updateAIProgress(40, 'Analyzing with LayoutLMv3 AI...');
        
        // Call AI import API
        const response = await axios.post(importApiUrl, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        
        updateAIProgress(100, 'Complete!');
        
        // Process results
        const template = response.data;
        
        // Save template to localStorage
        if (template.fields && template.fields.length > 0) {
            TemplateStorage.save(template);
            console.log('✅ Template saved to localStorage:', template.name);
            
            // Also save template to backend (file system)
            try {
                const saveResponse = await fetch('http://localhost:9000/api/templates/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(template)  // ← FIX: Added missing body parameter
                });
                
                const result = await saveResponse.json();
                
                if (saveResponse.ok && result.success) {
                    console.log('✅ Template saved to backend:', result.file_path);
                    logMessage(`✅ Template saved to: ${result.file_path}`);
                } else {
                    console.warn('⚠️ Failed to save template to backend:', result.message);
                }
            } catch (saveError) {
                console.error('⚠️ Could not save template to backend:', saveError);
                // Don't fail the import if backend save fails - localStorage save is still successful
            }
            
            // Show results
            setTimeout(() => {
                displayAIResults(template);
            }, 500);
        } else {
            throw new Error('No fields detected in PDF. The PDF might be empty or not contain form fields.');
        }
        
    } catch (error) {
        console.error('AI Import failed:', error);
        displayAIError(error);
    } finally {
        document.getElementById('importBtn').disabled = false;
    }
}

/**
 * Update AI progress
 */
function updateAIProgress(percent, message) {
    const progressBar = document.getElementById('aiProgressBar');
    progressBar.style.width = percent + '%';
    progressBar.textContent = message;
    
    document.getElementById('aiProgressText').textContent = message;
}

/**
 * Display AI results
 */
function displayAIResults(template) {
    document.getElementById('aiProgress').style.display = 'none';
    document.getElementById('aiResults').style.display = 'block';
    
    const numFields = template.fields.length;
    const templateName = template.name || 'Unnamed Template';
    
    document.getElementById('aiResultMessage').textContent = 
        `Successfully imported "${templateName}" with ${numFields} field${numFields !== 1 ? 's' : ''}!`;
    
    // Display detected fields
    const fieldsContainer = document.getElementById('detectedFields');
    fieldsContainer.innerHTML = '';
    
    if (numFields === 0) {
        fieldsContainer.innerHTML = '<p class="text-muted">No fields detected</p>';
    } else {
        const fieldsList = document.createElement('div');
        fieldsList.className = 'list-group';
        
        template.fields.forEach((field, index) => {
            const fieldItem = document.createElement('div');
            fieldItem.className = 'list-group-item';
            fieldItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${index + 1}. ${field.label || field.name}</strong>
                        <div class="small text-muted">
                            Type: ${field.type || 'text'} | 
                            Position: (${field.x}, ${field.y}) | 
                            Size: ${field.width}×${field.height}
                        </div>
                    </div>
                    <span class="badge bg-primary">${field.type || 'text'}</span>
                </div>
            `;
            fieldsList.appendChild(fieldItem);
        });
        
        fieldsContainer.appendChild(fieldsList);
    }
    
    // Show success notification
    showNotification(`Successfully imported and saved ${numFields} field${numFields !== 1 ? 's' : ''} to data/templates!`, 'success');
}

/**
 * Display AI error
 */
function displayAIError(error) {
    document.getElementById('aiProgress').style.display = 'none';
    document.getElementById('aiError').style.display = 'block';
    
    let errorMsg = 'Unknown error occurred';
    
    if (error.response) {
        const detail = error.response.data?.detail;
        if (typeof detail === 'object') {
            errorMsg = detail.message || detail.error || JSON.stringify(detail);
        } else {
            errorMsg = detail || `Server error: ${error.response.status}`;
        }
    } else if (error.request) {
        errorMsg = 'Cannot connect to backend server. Please ensure the Python backend is running on http://localhost:9000';
    } else {
        errorMsg = error.message;
    }
    
    document.getElementById('aiErrorMessage').textContent = errorMsg;
}

/**
 * Reset AI import
 */
function resetAIImport() {
    document.getElementById('pdfFile').value = '';
    document.getElementById('aiResults').style.display = 'none';
    document.getElementById('aiError').style.display = 'none';
    document.getElementById('aiProgress').style.display = 'none';
}

/**
 * Go to generate page
 * Ensures template is saved before navigation
 */
async function goToGenerate() {
    // Get the most recently imported template
    const templates = TemplateStorage.getAll();
    if (templates.length === 0) {
        alert('No templates found. Please import a PDF first.');
        return;
    }
    
    // Get the most recent template (last one in array)
    const latestTemplate = templates[templates.length - 1];
    
    try {
        // Ensure template is saved to backend before navigating
        const saveResponse = await axios.post('http://localhost:9000/api/templates/save', latestTemplate, {
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (saveResponse.data.success) {
            console.log('✅ Template confirmed saved to backend:', saveResponse.data.file_path);
            showNotification('Template saved! Redirecting to generate page...', 'success');
            
            // Navigate after a brief delay to show the notification
            setTimeout(() => {
                window.location.href = 'generate.html';
            }, 800);
        } else {
            throw new Error(saveResponse.data.message || 'Failed to save template');
        }
    } catch (error) {
        console.error('❌ Error saving template:', error);
        
        // Ask user if they want to continue anyway
        const continueAnyway = confirm(
            'Warning: Could not save template to server.\n\n' +
            'The template is saved in your browser, but may not be available for ML training.\n\n' +
            'Continue to generate page anyway?'
        );
        
        if (continueAnyway) {
            window.location.href = 'generate.html';
        }
    }
}
