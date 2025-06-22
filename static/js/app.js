// Utility functions
async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API fetch error:', error);
        throw error;
    }
}

// Alert system
function showAlert(message, type = 'info', container = 'statusMessages') {
    const alertContainer = document.getElementById(container);
    if (!alertContainer) return;
    
    const alertTypes = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    };
    
    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-triangle',
        'warning': 'fa-exclamation-circle',
        'info': 'fa-info-circle'
    };
    
    const alertClass = alertTypes[type] || 'alert-info';
    const icon = icons[type] || 'fa-info-circle';
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas ${icon}"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Progress bar utilities
function updateProgress(elementId, percent, text = null) {
    const progressBar = document.getElementById(elementId);
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.setAttribute('aria-valuenow', percent);
        
        if (text) {
            progressBar.textContent = text;
        } else {
            progressBar.textContent = percent + '%';
        }
        
        // Update color based on progress
        progressBar.className = 'progress-bar';
        if (percent < 30) {
            progressBar.classList.add('bg-danger');
        } else if (percent < 70) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-success');
        }
    }
}

// Format date/time
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    // Chuẩn hóa định dạng nếu thiếu 'T'
    if (dateString.indexOf('T') === -1 && dateString.indexOf(' ') !== -1) {
        dateString = dateString.replace(' ', 'T');
    }
    let d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    // Đã chuẩn hóa backend trả về đúng giờ Việt Nam, KHÔNG cộng thêm 7 tiếng nữa
    let dd = String(d.getDate()).padStart(2, '0');
    let mm = String(d.getMonth() + 1).padStart(2, '0');
    let yyyy = d.getFullYear();
    let hh = String(d.getHours()).padStart(2, '0');
    let min = String(d.getMinutes()).padStart(2, '0');
    let ss = String(d.getSeconds()).padStart(2, '0');
    return `${dd}-${mm}-${yyyy} ${hh}:${min}:${ss}`;
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Connection status indicator
function updateConnectionStatus(isConnected, elementId = 'connectionStatus') {
    const indicator = document.getElementById(elementId);
    if (indicator) {
        indicator.className = `connection-indicator ${isConnected ? 'connected' : 'disconnected'}`;
        indicator.title = isConnected ? 'Đã kết nối' : 'Đã ngắt kết nối';
    }
}

// File parts progress
function updatePartsProgress(receivedParts, totalParts, containerId = 'partsProgress') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = '';
    
    for (let i = 1; i <= totalParts; i++) {
        const partDiv = document.createElement('div');
        partDiv.className = 'part-indicator';
        partDiv.title = `Phần ${i}`;
        
        if (receivedParts.includes(i)) {
            partDiv.classList.add('received');
        } else {
            partDiv.classList.add('pending');
        }
        
        container.appendChild(partDiv);
    }
}

// Table utilities
function createTableRow(data, columns) {
    const row = document.createElement('tr');
    
    columns.forEach(column => {
        const cell = document.createElement('td');
        
        if (typeof column === 'string') {
            cell.textContent = data[column] || '';
        } else if (typeof column === 'object') {
            // Custom column with formatter
            if (column.formatter) {
                cell.innerHTML = column.formatter(data[column.key], data);
            } else {
                cell.textContent = data[column.key] || '';
            }
        }
        
        row.appendChild(cell);
    });
    
    return row;
}

// Status formatters
function formatStatus(status) {
    const statusClasses = {
        'pending': 'status-pending',
        'completed': 'status-completed',
        'error': 'status-error',
        'running': 'status-running'
    };
    
    const statusIcons = {
        'pending': 'fa-clock',
        'completed': 'fa-check-circle',
        'error': 'fa-exclamation-triangle',
        'running': 'fa-spinner fa-spin'
    };
    
    const statusClass = statusClasses[status] || '';
    const statusIcon = statusIcons[status] || 'fa-question-circle';
    
    return `<span class="${statusClass}">
        <i class="fas ${statusIcon}"></i> ${status}
    </span>`;
}

// Auto refresh functionality
let autoRefreshInterval = null;

function startAutoRefresh(callback, interval = 5000) {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(callback, interval);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Loading spinner
function showLoading(elementId, message = 'Đang tải...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">${message}</span>
                </div>
                <p class="mt-2 text-muted">${message}</p>
            </div>
        `;
    }
}

// Copy to clipboard
function copyToClipboard(text, showAlert = true) {
    navigator.clipboard.writeText(text).then(() => {
        if (showAlert) {
            showAlert('Đã sao chép vào clipboard!', 'success');
        }
    }).catch(err => {
        console.error('Không thể sao chép:', err);
        if (showAlert) {
            showAlert('Không thể sao chép vào clipboard!', 'error');
        }
    });
}

// Export table data
function exportTableToCSV(tableId, filename = 'data.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    for (let i = 0; i < rows.length; i++) {
        const row = [];
        const cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            let text = cols[j].textContent.trim();
            // Escape quotes and wrap in quotes if contains comma
            if (text.includes(',') || text.includes('"')) {
                text = '"' + text.replace(/"/g, '""') + '"';
            }
            row.push(text);
        }
        
        csv.push(row.join(','));
    }
    
    // Download CSV
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add fade-in animation to main content
    const mainContent = document.querySelector('.container');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// Global error handler
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showAlert('Có lỗi xảy ra trong ứng dụng!', 'error');
});

// Expose functions globally
window.apiFetch = apiFetch;
window.showAlert = showAlert;
window.updateProgress = updateProgress;
window.formatDateTime = formatDateTime;
window.formatFileSize = formatFileSize;
window.updateConnectionStatus = updateConnectionStatus;
window.updatePartsProgress = updatePartsProgress;
window.formatStatus = formatStatus;
window.startAutoRefresh = startAutoRefresh;
window.stopAutoRefresh = stopAutoRefresh;
window.showLoading = showLoading;
window.copyToClipboard = copyToClipboard;
window.exportTableToCSV = exportTableToCSV;