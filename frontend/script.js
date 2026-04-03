const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-upload');
const loading = document.getElementById('loading');
const resultsContainer = document.getElementById('results');
const errorMessage = document.getElementById('error-message');

const API_KEY = "sk_track2_987654321"; // Hardcoded for local testing

// Drag and drop events
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.classList.add('dragover');
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', handleDrop, false);
fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (files.length === 0) return;
    const file = files[0];
    
    // Extensions mapping
    const validExtensions = ['pdf', 'docx', 'jpg', 'jpeg', 'png'];
    const fileName = file.name;
    let extension = fileName.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(extension)) {
        showError("Invalid file type. Please upload PDF, DOCX, JPG, or PNG.");
        return;
    }

    processFile(file, extension);
}

function processFile(file, extension) {
    hideError();
    hideResults();
    showLoading();

    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = async function() {
        const base64String = reader.result.split(',')[1];
        
        try {
            const response = await fetch("/api/document-analyze", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-api-key": API_KEY
                },
                body: JSON.stringify({
                    fileName: file.name,
                    fileType: extension,
                    fileBase64: base64String
                })
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                displayResults(data);
            } else {
                showError(data.message || data.detail || "An error occurred during processing.");
            }
        } catch (error) {
            showError("Failed to connect to the backend API. Please make sure the FastAPI server is running.");
            console.error(error);
        } finally {
            hideLoading();
        }
    };
    reader.onerror = function(error) {
        hideLoading();
        showError("Failed to read file.");
    };
}

function displayResults(data) {
    // Summary
    document.getElementById('summary-text').innerText = data.summary;
    
    // Sentiment
    const sentimentBadge = document.getElementById('sentiment-badge');
    const sentiment = data.sentiment ? data.sentiment.trim() : "Neutral";
    sentimentBadge.innerText = sentiment;
    sentimentBadge.className = 'badge';
    sentimentBadge.classList.add(sentiment.toLowerCase());

    // Entities
    renderTags('entities-names', data.entities?.names);
    renderTags('entities-orgs', data.entities?.organizations);
    renderTags('entities-dates', data.entities?.dates);
    renderTags('entities-amounts', data.entities?.amounts);

    resultsContainer.classList.remove('hidden');
}

function renderTags(elementId, items) {
    const container = document.getElementById(elementId);
    container.innerHTML = ''; // Clear previous
    
    if (!items || items.length === 0) {
        container.innerHTML = '<span class="tag" style="background: transparent; color: #64748b; padding:0;">None found</span>';
        return;
    }

    items.forEach(item => {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.innerText = item;
        container.appendChild(tag);
    });
}

function showLoading() { loading.classList.remove('hidden'); dropZone.classList.add('hidden'); }
function hideLoading() { loading.classList.add('hidden'); dropZone.classList.remove('hidden'); }
function showResults() { resultsContainer.classList.remove('hidden'); }
function hideResults() { resultsContainer.classList.add('hidden'); }
function showError(msg) { 
    errorMessage.classList.remove('hidden'); 
    document.getElementById('error-text').innerText = msg;
}
function hideError() { errorMessage.classList.add('hidden'); }
