/**
 * Real-Time Updates using Server-Sent Events (SSE)
 * Handles notifications, dashboard updates, and project status changes
 */

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
    }

    /**
     * Connect to notifications stream
     */
    connectNotifications(callback) {
        if (this.callbacks.notifications.indexOf(callback) === -1) {
            this.callbacks.notifications.push(callback);
        }

        if (this.eventSources.notifications) {
            return; // Already connected
        }

        const url = '/projeng/api/realtime/notifications/';
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
                const data = JSON.parse(event.data);
                this._handleMessage(key, data);
            } catch (e) {
                console.error('Error parsing SSE data:', e);
            }
        };

        eventSource.onerror = (error) => {
            console.error(`SSE connection error for ${key}:`, error);
            this._handleError(key, error);
        };

        eventSource.onopen = () => {
            console.log(`SSE connected: ${key}`);
            this.isConnected = true;
            this.reconnectAttempts = 0;
        };

        this.eventSources[key] = eventSource;
    }

    /**
     * Handle incoming messages
     */
    _handleMessage(key, data) {
        if (data.type === 'error') {
            console.error('SSE error:', data.message);
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

        // Attempt reconnection
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Reconnecting ${key} in ${delay}ms...`);
            
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
            console.error(`Max reconnection attempts reached for ${key}`);
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
        console.error('Error storing shown notification ID:', e);
    }
}

function hasNotificationBeenShown(id) {
    return getShownNotificationIds().includes(id);
}

function setupRealtimeNotifications() {
    const notificationBell = document.getElementById('notification-bell');
    const notificationCount = document.getElementById('notification-count');
    
    if (!notificationBell) return;

    window.realtimeManager.connectNotifications((data) => {
        if (data.type === 'notification') {
            // Check if this notification has already been shown (across page navigations)
            const notificationId = data.notification ? data.notification.id : null;
            const isNewNotification = notificationId && 
                                     notificationId !== lastNotificationId && 
                                     !hasNotificationBeenShown(notificationId);
            
            // Update notification count silently
            if (notificationCount) {
                const currentCount = parseInt(notificationCount.textContent) || 0;
                const newCount = data.unread_count || 0;
                
                notificationCount.textContent = newCount;
                
                if (newCount === 0) {
                    notificationCount.classList.add('hidden');
                } else {
                    notificationCount.classList.remove('hidden');
                    
                    // Only animate if count increased (new notification)
                    if (newCount > currentCount && isNewNotification) {
                        notificationCount.classList.add('animate-pulse');
                        setTimeout(() => {
                            notificationCount.classList.remove('animate-pulse');
                        }, 2000);
                    }
                }
            }

            // Only show browser notification for NEW notifications (not on page load or already shown)
            // This ensures notifications only "pop once" per new notification
            if (isNewNotification && 'Notification' in window && Notification.permission === 'granted') {
                new Notification('OneTagumVision', {
                    body: data.notification.message,
                    icon: '/static/img/tagum.jpg',
                    tag: `notification-${notificationId}`, // Prevent duplicate notifications
                    requireInteraction: false
                });
                
                // Mark as shown immediately to prevent re-showing on page navigation
                addShownNotificationId(notificationId);
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
 * Helper: Show toast notification (removed - too intrusive)
 * Notifications are now handled silently via badge count only
 */
function showToastNotification(message) {
    // Disabled - notifications are now handled professionally via badge count only
    // Users can check notifications page for details
    return;
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
    
    if (path.includes('dashboard') || path === '/') {
        setupRealtimeDashboard();
        setupRealtimeNotifications();
    } else if (path.includes('projects')) {
        const projectIdMatch = path.match(/projects\/(\d+)/);
        if (projectIdMatch) {
            setupRealtimeProjects(parseInt(projectIdMatch[1]));
        } else {
            setupRealtimeProjects();
        }
        setupRealtimeNotifications();
    } else {
        // Setup notifications on all pages
        setupRealtimeNotifications();
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        window.realtimeManager.disconnect();
    });
});

