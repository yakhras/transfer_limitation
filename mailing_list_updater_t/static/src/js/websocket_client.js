/** @odoo-module **/

/**
 * WebSocket client for real-time mailing list update progress tracking.
 * 
 * This module provides WebSocket communication capabilities for receiving
 * real-time updates during batch operations, enabling live progress tracking
 * and status updates in the frontend.
 */

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MailingWebSocketClient {
    /**
     * Initialize WebSocket client for a specific batch.
     * 
     * @param {string} batchId - The batch ID to track
     * @param {Object} options - Configuration options
     */
    constructor(batchId, options = {}) {
        this.batchId = batchId;
        this.options = {
            reconnectInterval: 3000,
            maxReconnectAttempts: 10,
            heartbeatInterval: 30000,
            ...options
        };
        
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.listeners = {
            progress: [],
            status: [],
            error: [],
            connect: [],
            disconnect: []
        };
        
        this.heartbeatTimer = null;
        this.reconnectTimer = null;
    }
    
    /**
     * Connect to WebSocket server.
     */
    connect() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            return; // Already connected
        }
        
        try {
            // Build WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = `${protocol}//${host}/ws/mailing/progress/${this.batchId}`;
            
            console.log(`[MailingWebSocket] Connecting to: ${wsUrl}`);
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = (event) => {
                console.log(`[MailingWebSocket] Connected to batch ${this.batchId}`);
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this._startHeartbeat();
                this._trigger('connect', { batchId: this.batchId });
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this._handleMessage(data);
                } catch (error) {
                    console.error('[MailingWebSocket] Error parsing message:', error);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('[MailingWebSocket] WebSocket error:', error);
                this._trigger('error', { error, batchId: this.batchId });
            };
            
            this.websocket.onclose = (event) => {
                console.log(`[MailingWebSocket] Connection closed:`, event);
                this.isConnected = false;
                this._stopHeartbeat();
                this._trigger('disconnect', { batchId: this.batchId });
                
                // Attempt to reconnect if not intentionally closed
                if (event.code !== 1000 && this.reconnectAttempts < this.options.maxReconnectAttempts) {
                    this._scheduleReconnect();
                }
            };
            
        } catch (error) {
            console.error('[MailingWebSocket] Connection failed:', error);
            this._trigger('error', { error, batchId: this.batchId });
        }
    }
    
    /**
     * Disconnect from WebSocket server.
     */
    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        this._stopHeartbeat();
        
        if (this.websocket) {
            this.websocket.close(1000, 'Client disconnect');
            this.websocket = null;
        }
        
        this.isConnected = false;
    }
    
    /**
     * Register event listener.
     * 
     * @param {string} event - Event type (progress, status, error, connect, disconnect)
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
    }
    
    /**
     * Remove event listener.
     * 
     * @param {string} event - Event type
     * @param {Function} callback - Callback function to remove
     */
    off(event, callback) {
        if (this.listeners[event]) {
            const index = this.listeners[event].indexOf(callback);
            if (index > -1) {
                this.listeners[event].splice(index, 1);
            }
        }
    }
    
    /**
     * Send message to server.
     * 
     * @param {Object} message - Message to send
     */
    send(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        } else {
            console.warn('[MailingWebSocket] Cannot send message - not connected');
        }
    }
    
    /**
     * Get current connection status.
     * 
     * @returns {Object} Status information
     */
    getStatus() {
        return {
            connected: this.isConnected,
            batchId: this.batchId,
            reconnectAttempts: this.reconnectAttempts,
            websocketState: this.websocket ? this.websocket.readyState : null
        };
    }
    
    // Private methods
    
    /**
     * Handle incoming WebSocket messages.
     * 
     * @private
     * @param {Object} data - Parsed message data
     */
    _handleMessage(data) {
        console.log('[MailingWebSocket] Received message:', data);
        
        switch (data.type) {
            case 'progress_update':
                this._trigger('progress', {
                    batchId: this.batchId,
                    progress: data.progress,
                    message: data.message,
                    timestamp: data.timestamp
                });
                break;
                
            case 'status_change':
                this._trigger('status', {
                    batchId: this.batchId,
                    status: data.status,
                    previousStatus: data.previous_status,
                    message: data.message,
                    timestamp: data.timestamp
                });
                break;
                
            case 'batch_completed':
                this._trigger('status', {
                    batchId: this.batchId,
                    status: 'completed',
                    results: data.results,
                    message: data.message,
                    timestamp: data.timestamp
                });
                break;
                
            case 'batch_failed':
                this._trigger('error', {
                    batchId: this.batchId,
                    error: data.error,
                    message: data.message,
                    timestamp: data.timestamp
                });
                break;
                
            case 'heartbeat':
                // Respond to server heartbeat
                this.send({ type: 'heartbeat_response', batchId: this.batchId });
                break;
                
            default:
                console.warn('[MailingWebSocket] Unknown message type:', data.type);
        }
    }
    
    /**
     * Trigger event listeners.
     * 
     * @private
     * @param {string} event - Event type
     * @param {Object} data - Event data
     */
    _trigger(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[MailingWebSocket] Error in ${event} callback:`, error);
                }
            });
        }
    }
    
    /**
     * Start heartbeat timer.
     * 
     * @private
     */
    _startHeartbeat() {
        this._stopHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'heartbeat', batchId: this.batchId, timestamp: Date.now() });
            }
        }, this.options.heartbeatInterval);
    }
    
    /**
     * Stop heartbeat timer.
     * 
     * @private
     */
    _stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * Schedule reconnection attempt.
     * 
     * @private
     */
    _scheduleReconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        
        this.reconnectAttempts++;
        const delay = Math.min(this.options.reconnectInterval * this.reconnectAttempts, 30000);
        
        console.log(`[MailingWebSocket] Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, delay);
    }
}

/**
 * OWL Component wrapper for WebSocket functionality.
 * 
 * This component can be used in OWL templates to easily integrate
 * WebSocket communication with reactive UI updates.
 */
export class MailingProgressTracker extends Component {
    static template = "mailing_list_updater_t.ProgressTracker";
    
    setup() {
        this.rpc = useService("rpc");
        
        this.state = useState({
            connected: false,
            progress: 0,
            status: 'unknown',
            message: 'Initializing...',
            error: null,
            batchId: this.props.batchId
        });
        
        this.websocketClient = null;
        
        onMounted(() => {
            this._initializeWebSocket();
        });
        
        onWillUnmount(() => {
            if (this.websocketClient) {
                this.websocketClient.disconnect();
            }
        });
    }
    
    /**
     * Initialize WebSocket connection and event handlers.
     * 
     * @private
     */
    _initializeWebSocket() {
        if (!this.props.batchId) {
            console.error('[MailingProgressTracker] No batch ID provided');
            return;
        }
        
        this.websocketClient = new MailingWebSocketClient(this.props.batchId);
        
        // Register event handlers
        this.websocketClient.on('connect', () => {
            this.state.connected = true;
            this.state.error = null;
        });
        
        this.websocketClient.on('disconnect', () => {
            this.state.connected = false;
        });
        
        this.websocketClient.on('progress', (data) => {
            this.state.progress = data.progress.progress_percentage || 0;
            this.state.message = data.progress.current_operation || 'Processing...';
        });
        
        this.websocketClient.on('status', (data) => {
            this.state.status = data.status;
            this.state.message = data.message || `Status: ${data.status}`;
        });
        
        this.websocketClient.on('error', (data) => {
            this.state.error = data.error || 'An error occurred';
            this.state.status = 'error';
        });
        
        // Connect to WebSocket
        this.websocketClient.connect();
    }
    
    /**
     * Fallback to HTTP polling if WebSocket fails.
     * 
     * @private 
     */
    async _fallbackToPolling() {
        if (!this.props.batchId) return;
        
        try {
            const result = await this.rpc(`/mailing/update/progress/${this.props.batchId}`);
            if (result.success) {
                const progress = result.data;
                this.state.progress = progress.progress_percentage || 0;
                this.state.status = progress.state;
                this.state.message = progress.current_operation || 'Processing...';
                
                // Continue polling if still processing
                if (progress.state === 'processing') {
                    setTimeout(() => this._fallbackToPolling(), 2000);
                }
            }
        } catch (error) {
            console.error('[MailingProgressTracker] Polling failed:', error);
            this.state.error = 'Failed to get progress updates';
        }
    }
}

// Register the component
registry.category("components").add("MailingProgressTracker", MailingProgressTracker);

// Export for direct usage
export { MailingWebSocketClient, MailingProgressTracker };