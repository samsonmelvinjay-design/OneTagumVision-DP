/**
 * Real-Time Updates using Server-Sent Events (SSE)
 * Handles notifications, dashboard updates, and project status changes
 * Set window.DEBUG_REALTIME = true or ?debug=1 in URL to show connection logs.
 */
(function() {
    window.DEBUG_REALTIME = window.DEBUG_REALTIME === true || /[?&]debug=1/.test(window.location.search || '');
})();

class RealtimeManager {
    constructor() {
        this.eventSources = {};
        this.callbacks = {
            notifications: [],
            dashboard: [],
            projects: []
        };
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this._errorLogged = {}; // Log SSE errors once per key to avoid console spam (e.g. ERR_QUIC_PROTOCOL_ERROR)
    }

    /**
     * Connect to notifications stream
     */
    connectNotifications(callback) {
        if (this.callbacks.notifications.indexOf(callback) === -1) {
            this.callbacks.notifications.push(callback);
        }

        if (this.eventSources.notifications) {
            if (window.DEBUG_REALTIME) console.log('✅ Notifications SSE already connected');
            return; // Already connected
        }

        const url = '/projeng/api/realtime/notifications/';
        if (window.DEBUG_REALTIME) console.log('🔌 Connecting to notifications SSE:', url);
        this._connectSSE('notifications', url);
    }

    /**
     * Connect to dashboard updates stream
     */
    connectDashboard(callback) {
        if (this.callbacks.dashboard.indexOf(callback) === -1) {
            this.callbacks.dashboard.push(callback);
        }

        if (this.eventSources.dashboard) {
            return; // Already connected
        }

        const url = '/projeng/api/realtime/dashboard/';
        this._connectSSE('dashboard', url);
    }

    /**
     * Connect to project status stream
     */
    connectProjects(callback, projectId = null) {
        if (this.callbacks.projects.indexOf(callback) === -1) {
            this.callbacks.projects.push(callback);
        }

        const key = projectId ? `projects_${projectId}` : 'projects';
        if (this.eventSources[key]) {
            return; // Already connected
        }

        const url = projectId 
            ? `/projeng/api/realtime/projects/${projectId}/`
            : '/projeng/api/realtime/projects/';
        this._connectSSE(key, url);
    }

    /**
     * Internal method to connect SSE
     */
    _connectSSE(key, url) {
        const eventSource = new EventSource(url);
        
        eventSource.onmessage = (event) => {
            try {
                // Skip heartbeat messages
                if (!event.data || event.data.trim() === '' || event.data.startsWith(':')) {
                    return;
                }
                const data = JSON.parse(event.data);
                this._handleMessage(key, data);
            } catch (e) {
                if (event.data && !event.data.startsWith(':') && window.DEBUG_REALTIME) {
                    console.error('Error parsing SSE data:', e, event.data);
                }
            }
        };

        eventSource.onerror = (error) => {
            // Log once per key per page load to avoid flooding console (e.g. ERR_QUIC_PROTOCOL_ERROR)
            if (!this._errorLogged[key]) {
                this._errorLogged[key] = true;
                const msg = `SSE connection issue for ${key} (reconnecting silently). Set DEBUG_REALTIME=true for details.`;
                console.warn(msg, window.DEBUG_REALTIME ? error : '(If you see ERR_QUIC_PROTOCOL_ERROR, it is often a browser/network quirk with long-lived connections; app still works.)');
            }
            this._handleError(key, error);
        };

        eventSource.onopen = () => {
            // Do not reset _errorLogged here so we only ever log one warning per stream per page load
            if (window.DEBUG_REALTIME) console.log('✅ SSE connected:', key, url);
            this.isConnected = true;
            this.reconnectAttempts = 0;
        };

        this.eventSources[key] = eventSource;
    }

    /**
     * Handle incoming messages
     */
    _handleMessage(key, data) {
        // Skip invalid or empty data
        if (!data || typeof data !== 'object') {
            return;
        }
        
        if (data.type === 'error') {
            if (data.message && window.DEBUG_REALTIME) {
                console.error('SSE error:', data.message);
            }
            return;
        }

        // Route to appropriate callbacks
        if (key === 'notifications' || key.startsWith('notifications')) {
            this.callbacks.notifications.forEach(cb => cb(data));
        }
        
        if (key === 'dashboard' || key.startsWith('dashboard')) {
            this.callbacks.dashboard.forEach(cb => cb(data));
        }
        
        if (key === 'projects' || key.startsWith('projects')) {
            this.callbacks.projects.forEach(cb => cb(data));
        }
    }

    /**
     * Handle connection errors
     */
    _handleError(key, error) {
        const eventSource = this.eventSources[key];
        if (eventSource) {
            eventSource.close();
            delete this.eventSources[key];
        }

        // Attempt reconnection (silent unless DEBUG_REALTIME to avoid console spam)
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            if (window.DEBUG_REALTIME) console.log('Reconnecting', key, 'in', delay, 'ms...');

            setTimeout(() => {
                // Reconnect based on key
                if (key === 'notifications') {
                    this.connectNotifications(() => {});
                } else if (key === 'dashboard') {
                    this.connectDashboard(() => {});
                } else if (key.startsWith('projects')) {
                    const projectId = key.includes('_') ? parseInt(key.split('_')[1]) : null;
                    this.connectProjects(() => {}, projectId);
                }
            }, delay);
        } else {
            if (window.DEBUG_REALTIME) console.warn('Max reconnection attempts reached for', key);
            this.isConnected = false;
        }
    }

    /**
     * Disconnect all streams
     */
    disconnect() {
        Object.keys(this.eventSources).forEach(key => {
            if (this.eventSources[key]) {
                this.eventSources[key].close();
                delete this.eventSources[key];
            }
        });
        this.callbacks = {
            notifications: [],
            dashboard: [],
            projects: []
        };
        this.isConnected = false;
    }

    /**
     * Disconnect specific stream
     */
    disconnectStream(key) {
        if (this.eventSources[key]) {
            this.eventSources[key].close();
            delete this.eventSources[key];
        }
    }
}

// Global instance
window.realtimeManager = new RealtimeManager();

/**
 * Notification Handler - Professional, non-intrusive
 */
let lastNotificationId = null;

// Track shown notifications across page navigations using sessionStorage
function getShownNotificationIds() {
    try {
        const stored = sessionStorage.getItem('shownNotificationIds');
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        return [];
    }
}

function addShownNotificationId(id) {
    try {
        const shown = getShownNotificationIds();
        if (!shown.includes(id)) {
            shown.push(id);
            // Keep only last 50 IDs to prevent storage bloat
            if (shown.length > 50) {
                shown.shift();
            }
            sessionStorage.setItem('shownNotificationIds', JSON.stringify(shown));
        }
    } catch (e) {
        if (window.DEBUG_REALTIME) console.error('Error storing shown notification ID:', e);
    }
}

function hasNotificationBeenShown(id) {
    return getShownNotificationIds().includes(id);
}

function setupRealtimeNotifications() {
    if (window.DEBUG_REALTIME) console.log('🔔 Setting up real-time notifications...');
    const notificationBell = document.getElementById('notification-bell');
    const notificationCount = document.getElementById('notification-count');

    if (!window.realtimeManager) {
        if (window.DEBUG_REALTIME) console.error('❌ RealtimeManager not initialized!');
        return;
    }

    window.realtimeManager.connectNotifications((data) => {
        if (window.DEBUG_REALTIME) console.log('📨 Received notification data:', data);
        if (data.type === 'notification') {
            // Get current count BEFORE updating
            const currentCount = notificationCount ? (parseInt(notificationCount.textContent) || 0) : 0;
            const newCount = data.unread_count || 0;
            const countIncreased = newCount > currentCount;
            
            // Update notification count silently (always update count)
            if (notificationCount) {
                notificationCount.textContent = newCount;
                
                if (newCount === 0) {
                    notificationCount.classList.add('hidden');
                } else {
                    notificationCount.classList.remove('hidden');
                }
            }
            
            // Only process notification details if a notification object is present
            // This prevents showing old notifications when only count is sent
            if (!data.notification) {
                return; // Only count update, no notification to show
            }
            
            // Check if this notification has already been shown (across page navigations)
            const notificationId = data.notification ? data.notification.id : null;
            const notificationMessage = data.notification ? data.notification.message : null;
            
            // Check if this exact notification has been shown before (by ID or by message content)
            const hasBeenShown = notificationId ? hasNotificationBeenShown(notificationId) : false;
            
            // Also check by message content to prevent duplicates even if ID is missing
            let messageShown = false;
            if (notificationMessage) {
                try {
                    const shownMessages = JSON.parse(sessionStorage.getItem('shownNotificationMessages') || '[]');
                    messageShown = shownMessages.includes(notificationMessage);
                    if (!messageShown && notificationMessage) {
                        shownMessages.push(notificationMessage);
                        // Keep only last 20 messages to prevent storage bloat
                        if (shownMessages.length > 20) {
                            shownMessages.shift();
                        }
                        sessionStorage.setItem('shownNotificationMessages', JSON.stringify(shownMessages));
                    }
                } catch (e) {
                    if (window.DEBUG_REALTIME) console.error('Error checking shown messages:', e);
                }
            }
            
            const isNewNotification = notificationId && 
                                     notificationId !== lastNotificationId && 
                                     !hasBeenShown && !messageShown;
            
            // countIncreased is already calculated above
            
            // Only animate badge if count increased and it's a new notification
            if (notificationCount && isNewNotification) {
                if (countIncreased) {
                    notificationCount.classList.add('animate-pulse');
                    setTimeout(() => {
                        notificationCount.classList.remove('animate-pulse');
                    }, 2000);
                }
            }

            // Show toast notification when we have a new notification message
            // Always show if we have a message and it hasn't been shown before
            // This ensures the toast appears for every new notification
            const shouldShowToast = notificationMessage && !messageShown && (
                countIncreased ||  // Count increased = definitely new
                isNewNotification ||  // New notification by ID
                notificationId  // Has an ID (means it's a real notification)
            );
            
            if (shouldShowToast) {
                if (window.DEBUG_REALTIME) console.log('🔔 Showing toast:', notificationMessage);
                showToastNotification(notificationMessage);
                
                // Mark as shown immediately to prevent re-showing
                if (notificationId) {
                    addShownNotificationId(notificationId);
                }
                // Also mark message as shown
                try {
                    const shownMessages = JSON.parse(sessionStorage.getItem('shownNotificationMessages') || '[]');
                    if (!shownMessages.includes(notificationMessage)) {
                        shownMessages.push(notificationMessage);
                        if (shownMessages.length > 20) {
                            shownMessages.shift();
                        }
                        sessionStorage.setItem('shownNotificationMessages', JSON.stringify(shownMessages));
                    }
                } catch (e) {
                    if (window.DEBUG_REALTIME) console.error('Error marking message as shown:', e);
                }
            }

            // Only show browser notification for NEW notifications (not on page load or already shown)
            // This ensures notifications only "pop once" per new notification
            if (isNewNotification && 'Notification' in window && Notification.permission === 'granted') {
                new Notification('OneTagumVision', {
                    body: notificationMessage,
                    icon: '/static/img/tagum.jpg',
                    tag: `notification-${notificationId}`, // Prevent duplicate notifications
                    requireInteraction: false
                });
            }

            // Update last notification ID
            if (notificationId) {
                lastNotificationId = notificationId;
            }
        }
    });
}

/**
 * Dashboard Updates Handler
 */
function setupRealtimeDashboard() {
    window.realtimeManager.connectDashboard((data) => {
        if (data.type === 'dashboard_update') {
            // Update status counts
            if (data.status_counts) {
                updateDashboardCards(data.status_counts, data.total_projects);
            }

            // Recent updates banner is disabled - too intrusive
            // Users can check notifications page for details
            // if (data.recent_updates && data.recent_updates.length > 0) {
            //     showRecentUpdates(data.recent_updates);
            // }
        }
    });
}

/**
 * Project Status Handler
 */
function setupRealtimeProjects(projectId = null) {
    window.realtimeManager.connectProjects((data) => {
        if (data.type === 'project_status') {
            if (projectId && data.project_id === projectId) {
                // Update single project
                updateProjectStatus(data);
            } else if (!projectId && data.projects) {
                // Update multiple projects
                data.projects.forEach(project => {
                    updateProjectStatus(project);
                });
            }
        }
    }, projectId);
}

/**
 * Helper: Update dashboard cards
 */
function updateDashboardCards(statusCounts, totalProjects) {
    // Update total projects - try multiple possible IDs
    const totalEl = document.getElementById('total-projects') || 
                    document.getElementById('card-total-projects') ||
                    document.querySelector('[id*="total"]');
    if (totalEl) {
        totalEl.textContent = totalProjects;
    }

    // Update status counts - try multiple possible ID patterns
    ['planned', 'in_progress', 'completed', 'delayed'].forEach(status => {
        // Try different ID patterns
        const el = document.getElementById(`status-${status}`) ||
                   document.getElementById(`card-${status}`) ||
                   document.getElementById(`card-${status.replace('_', '-')}`);
        
        if (el && statusCounts[status] !== undefined) {
            const oldValue = parseInt(el.textContent) || 0;
            const newValue = statusCounts[status];
            if (oldValue !== newValue) {
                el.textContent = newValue;
                // Add highlight animation
                el.classList.add('text-yellow-500', 'font-bold');
                setTimeout(() => {
                    el.classList.remove('text-yellow-500', 'font-bold');
                }, 2000);
            }
        }
    });
}

/**
 * Helper: Show recent updates (DISABLED - too intrusive, use notification badge instead)
 */
function showRecentUpdates(updates) {
    // DISABLED: This function was creating persistent banners
    // Notifications are now handled via the notification badge only
    // Users can check the notifications page for details
    return;
}

/**
 * Helper: Update project status
 */
function updateProjectStatus(data) {
    const projectEl = document.querySelector(`[data-project-id="${data.id}"]`);
    if (projectEl) {
        // Update status badge
        const statusBadge = projectEl.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = data.status;
            statusBadge.className = `status-badge status-${data.status}`;
        }

        // Update progress if available
        if (data.progress !== undefined) {
            const progressBar = projectEl.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${data.progress}%`;
            }
        }

        // Add highlight animation
        projectEl.classList.add('bg-yellow-100');
        setTimeout(() => {
            projectEl.classList.remove('bg-yellow-100');
        }, 2000);
    }
}

/**
 * Helper: Show toast notification
 * Shows a blue pop-up notification in the upper right corner
 */
function showToastNotification(message) {
    const toastContainer = document.getElementById('toast-notification');
    const toastMessage = document.getElementById('toast-message');
    const toastClose = document.getElementById('toast-close');

    if (!toastContainer || !toastMessage) {
        if (window.DEBUG_REALTIME) console.warn('Toast elements not found (toast-notification / toast-message)');
        return;
    }
    
    // Set message
    toastMessage.textContent = message || 'New notification';
    
    // Ensure container is positioned correctly
    toastContainer.style.position = 'fixed';
    toastContainer.style.top = '1rem';
    toastContainer.style.right = '1rem';
    toastContainer.style.zIndex = '9999';
    
    // Hide any existing toast first
    toastContainer.classList.add('hidden');
    
    // Force reflow to reset animation
    void toastContainer.offsetWidth;
    
    toastContainer.classList.remove('hidden');

    const autoHide = setTimeout(() => {
        hideToastNotification();
    }, 5000);
    
    // Store timeout ID for cleanup
    if (toastContainer) {
        toastContainer._autoHideTimeout = autoHide;
    }
    
    // Close button handler
    if (toastClose) {
        // Remove old handlers
        const newCloseBtn = toastClose.cloneNode(true);
        toastClose.parentNode.replaceChild(newCloseBtn, toastClose);
        
        newCloseBtn.onclick = () => {
            if (toastContainer._autoHideTimeout) {
                clearTimeout(toastContainer._autoHideTimeout);
            }
            hideToastNotification();
        };
    }
}

/**
 * Hide toast notification
 */
function hideToastNotification() {
    const toastContainer = document.getElementById('toast-notification');
    if (toastContainer) {
        toastContainer.classList.add('hidden');
    }
}

/**
 * Request notification permission
 */
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Request notification permission
    requestNotificationPermission();

    // Setup real-time features based on page
    const path = window.location.pathname;
    
    // ALWAYS setup notifications for ALL users on ALL pages
    // This ensures real-time updates work for:
    // - Head Engineers
    // - Finance Managers  
    // - Project Engineers
    // - Admins
    setupRealtimeNotifications();
    
    if (path.includes('dashboard') || path === '/') {
        setupRealtimeDashboard();
    } else if (path.includes('projects')) {
        const projectIdMatch = path.match(/projects\/(\d+)/);
        if (projectIdMatch) {
            setupRealtimeProjects(parseInt(projectIdMatch[1]));
        } else {
            setupRealtimeProjects();
        }
    }
    
    // Test toast notification on page load (for debugging)
    // Uncomment the line below to test the toast notification
    // setTimeout(() => showToastNotification('Test notification - Toast system is working!'), 2000);

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        window.realtimeManager.disconnect();
    });
});

