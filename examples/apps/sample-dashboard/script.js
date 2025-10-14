// Fetch and display service information
async function loadServiceInfo() {
    const container = document.getElementById('service-info');

    try {
        const response = await fetch('/api/v1/info');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const info = await response.json();

        const html = `
            <div class="info-row">
                <span class="info-label">Service Name:</span>
                <span class="info-value">${info.display_name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Version:</span>
                <span class="info-value">${info.version}</span>
            </div>
            ${info.summary ? `
            <div class="info-row">
                <span class="info-label">Summary:</span>
                <span class="info-value">${info.summary}</span>
            </div>
            ` : ''}
            ${info.description ? `
            <div class="info-row">
                <span class="info-label">Description:</span>
                <span class="info-value">${info.description}</span>
            </div>
            ` : ''}
        `;

        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load service info: ${error.message}</div>`;
    }
}

// Load service info when page loads
document.addEventListener('DOMContentLoaded', loadServiceInfo);
