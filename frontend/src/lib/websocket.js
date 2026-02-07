const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export class WebSocketManager {
  constructor(tenantId) {
    this.tenantId = tenantId;
    this.ws = null;
    this.listeners = new Map();
    this.reconnectTimeout = null;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.isConnected = false;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    
    const wsUrl = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');
    const url = `${wsUrl}/ws/${this.tenantId}`;
    
    try {
      this.ws = new WebSocket(url);
      
      this.ws.onopen = () => {
        this.isConnected = true;
        this.reconnectDelay = 1000;
        console.log('[WS] Connected to', this.tenantId);
        this._startPing();
      };
      
      this.ws.onmessage = (event) => {
        if (event.data === 'pong') return;
        try {
          const data = JSON.parse(event.data);
          this._notifyListeners(data);
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };
      
      this.ws.onclose = () => {
        this.isConnected = false;
        this._stopPing();
        this._scheduleReconnect();
      };
      
      this.ws.onerror = (err) => {
        console.error('[WS] Error:', err);
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      this._scheduleReconnect();
    }
  }

  disconnect() {
    this._stopPing();
    clearTimeout(this.reconnectTimeout);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  on(entity, callback) {
    if (!this.listeners.has(entity)) {
      this.listeners.set(entity, []);
    }
    this.listeners.get(entity).push(callback);
    return () => {
      const cbs = this.listeners.get(entity);
      if (cbs) {
        const idx = cbs.indexOf(callback);
        if (idx !== -1) cbs.splice(idx, 1);
      }
    };
  }

  _notifyListeners(data) {
    const entity = data.entity;
    const cbs = this.listeners.get(entity) || [];
    cbs.forEach(cb => cb(data));
    
    // Notify wildcard listeners
    const wildcardCbs = this.listeners.get('*') || [];
    wildcardCbs.forEach(cb => cb(data));
  }

  _startPing() {
    this._stopPing();
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 25000);
  }

  _stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  _scheduleReconnect() {
    clearTimeout(this.reconnectTimeout);
    this.reconnectTimeout = setTimeout(() => {
      console.log('[WS] Reconnecting...');
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
  }
}
