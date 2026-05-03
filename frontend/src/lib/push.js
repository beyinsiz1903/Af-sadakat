// PWA + Push helpers — service worker registration, install prompt, push subscribe.
import api from './api';

let deferredInstallPrompt = null;

export function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return Promise.resolve(null);
  return navigator.serviceWorker.register('/sw.js').catch((e) => {
    console.warn('[SW] register failed', e);
    return null;
  });
}

export function attachInstallPrompt(onAvailable) {
  if (typeof window === 'undefined') return;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    if (typeof onAvailable === 'function') onAvailable(true);
  });
  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    if (typeof onAvailable === 'function') onAvailable(false);
  });
}

export async function triggerInstallPrompt() {
  if (!deferredInstallPrompt) return { outcome: 'unavailable' };
  deferredInstallPrompt.prompt();
  const choice = await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  return choice;
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = window.atob(base64);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr;
}

export async function subscribeToPush(tenantSlug) {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null;
  const reg = await navigator.serviceWorker.ready;

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return null;

  const keyResp = await api.get(`/v2/push/tenants/${tenantSlug}/vapid-public-key`);
  const vapidKey = keyResp.data.public_key || keyResp.data.publicKey || keyResp.data;
  if (!vapidKey) return null;

  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey),
    });
  }
  await api.post(`/v2/push/tenants/${tenantSlug}/subscribe`, { subscription: sub.toJSON() });
  return sub;
}
