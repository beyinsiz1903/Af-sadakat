import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { pushAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  Bell, BellRing, Send, Users, Zap, CheckCircle, XCircle,
  Smartphone, Monitor, Plus, Trash2, BarChart3, Clock, AlertTriangle
} from 'lucide-react';

export default function PushNotificationsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [sendDialog, setSendDialog] = useState(false);
  const [pushData, setPushData] = useState({ title: '', body: '', user_id: '' });
  const [pushSupported, setPushSupported] = useState(false);
  const [pushSubscribed, setPushSubscribed] = useState(false);

  useEffect(() => {
    setPushSupported('serviceWorker' in navigator && 'PushManager' in window);
    checkSubscription();
  }, []);

  const checkSubscription = async () => {
    try {
      if ('serviceWorker' in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        if (reg) {
          const sub = await reg.pushManager.getSubscription();
          setPushSubscribed(!!sub);
        }
      }
    } catch (e) {
      console.log('Push check error:', e);
    }
  };

  const { data: stats } = useQuery({
    queryKey: ['push-stats', tenant?.slug],
    queryFn: () => pushAPI.getStats(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: subsData } = useQuery({
    queryKey: ['push-subscriptions', tenant?.slug],
    queryFn: () => pushAPI.listSubscriptions(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: logsData } = useQuery({
    queryKey: ['push-logs', tenant?.slug],
    queryFn: () => pushAPI.listPushLogs(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const subscribeMutation = useMutation({
    mutationFn: async () => {
      // Register service worker
      const reg = await navigator.serviceWorker.register('/sw.js');
      await navigator.serviceWorker.ready;

      // Get VAPID key
      const { data } = await pushAPI.getVapidKey(tenant?.slug);
      const vapidKey = data.public_key;

      // Convert VAPID key
      const urlBase64ToUint8Array = (base64String) => {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
          outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
      };

      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      });

      // Send to backend
      await pushAPI.subscribe(tenant?.slug, { subscription: subscription.toJSON() });
      setPushSubscribed(true);
      return subscription;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['push-subscriptions'] });
      queryClient.invalidateQueries({ queryKey: ['push-stats'] });
      toast.success('Push bildirimlere abone olundu!');
    },
    onError: (err) => {
      toast.error('Push abonelik hatasi: ' + (err.message || 'Bilinmeyen hata'));
    },
  });

  const unsubscribeMutation = useMutation({
    mutationFn: async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      if (reg) {
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
          await sub.unsubscribe();
          await pushAPI.unsubscribe(tenant?.slug, { endpoint: sub.endpoint });
        }
      }
      setPushSubscribed(false);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['push-subscriptions'] });
      queryClient.invalidateQueries({ queryKey: ['push-stats'] });
      toast.success('Push abonelik iptal edildi');
    },
  });

  const sendPush = useMutation({
    mutationFn: (data) => pushAPI.send(tenant?.slug, data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['push-logs'] });
      queryClient.invalidateQueries({ queryKey: ['push-stats'] });
      setSendDialog(false);
      setPushData({ title: '', body: '', user_id: '' });
      const d = res.data;
      toast.success(`Push gonderildi: ${d.sent} basarili, ${d.failed} basarisiz`);
    },
    onError: () => toast.error('Push gonderme hatasi'),
  });

  const subscriptions = subsData?.data || [];
  const logs = logsData?.data || [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Push Notifications</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Web push bildirim yonetimi ve istatistikleri</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Abone Sayisi</p>
                <p className="text-2xl font-bold">{stats?.total_subscribers || 0}</p>
              </div>
              <Users className="w-8 h-8 text-blue-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Toplam Kampanya</p>
                <p className="text-2xl font-bold">{stats?.total_campaigns || 0}</p>
              </div>
              <Send className="w-8 h-8 text-emerald-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Gonderilen Push</p>
                <p className="text-2xl font-bold">{stats?.total_pushes_sent || 0}</p>
              </div>
              <BellRing className="w-8 h-8 text-amber-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Teslimat Orani</p>
                <p className="text-2xl font-bold">{stats?.delivery_rate || 0}%</p>
              </div>
              <BarChart3 className="w-8 h-8 text-purple-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Browser Push Subscription */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <Bell className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Bu Tarayicida Push Bildirimler</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  {!pushSupported
                    ? 'Bu tarayici push bildirimleri desteklemiyor'
                    : pushSubscribed
                    ? 'Push bildirimlere abone oldunuz'
                    : 'Push bildirimlere abone olun'}
                </p>
              </div>
            </div>
            {pushSupported && (
              pushSubscribed ? (
                <Button variant="outline" onClick={() => unsubscribeMutation.mutate()} disabled={unsubscribeMutation.isPending}>
                  <XCircle className="w-4 h-4 mr-1" /> Abonelikten Cik
                </Button>
              ) : (
                <Button onClick={() => subscribeMutation.mutate()} disabled={subscribeMutation.isPending}>
                  <BellRing className="w-4 h-4 mr-1" /> Abone Ol
                </Button>
              )
            )}
          </div>
        </CardContent>
      </Card>

      {/* Send Push */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Push Bildirim Gonder</CardTitle>
          <Dialog open={sendDialog} onOpenChange={setSendDialog}>
            <DialogTrigger asChild>
              <Button size="sm"><Send className="w-4 h-4 mr-1" /> Yeni Push Gonder</Button>
            </DialogTrigger>
            <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <DialogHeader><DialogTitle>Push Bildirim Gonder</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <Input placeholder="Baslik" value={pushData.title} onChange={e => setPushData({...pushData, title: e.target.value})} />
                <Input placeholder="Mesaj icerigi" value={pushData.body} onChange={e => setPushData({...pushData, body: e.target.value})} />
                <Input placeholder="Kullanici ID (bos birakirsaniz herkese gider)" value={pushData.user_id} onChange={e => setPushData({...pushData, user_id: e.target.value})} />
                <Button onClick={() => sendPush.mutate(pushData)} disabled={!pushData.title || !pushData.body || sendPush.isPending}>
                  <Send className="w-4 h-4 mr-1" /> Gonder
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardHeader>
      </Card>

      {/* Active Subscriptions */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader>
          <CardTitle className="text-lg">Aktif Abonelikler ({subscriptions.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {subscriptions.map(sub => (
              <div key={sub.id} className="p-3 rounded-lg border border-[hsl(var(--border))] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Smartphone className="w-5 h-5 text-[hsl(var(--muted-foreground))]" />
                  <div>
                    <p className="text-sm font-medium">{sub.user_name || 'Anonim'}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{sub.subscription?.endpoint?.substring(0, 60)}...</p>
                  </div>
                </div>
                <Badge variant={sub.active ? 'default' : 'secondary'}>
                  {sub.active ? 'Aktif' : 'Pasif'}
                </Badge>
              </div>
            ))}
            {subscriptions.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">Henuz abone yok</p>}
          </div>
        </CardContent>
      </Card>

      {/* Push Log */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader>
          <CardTitle className="text-lg">Gonderim Gecmisi</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {logs.map(log => (
              <div key={log.id} className="p-3 rounded-lg border border-[hsl(var(--border))] flex items-center justify-between">
                <div>
                  <p className="font-medium">{log.title}</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{log.body}</p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <Badge variant="outline"><CheckCircle className="w-3 h-3 mr-1 text-emerald-400" /> {log.sent_count}</Badge>
                  {log.failed_count > 0 && <Badge variant="outline"><XCircle className="w-3 h-3 mr-1 text-red-400" /> {log.failed_count}</Badge>}
                  <span className="text-[hsl(var(--muted-foreground))]">{new Date(log.sent_at).toLocaleDateString('tr-TR')}</span>
                </div>
              </div>
            ))}
            {logs.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">Henuz push gonderilmemis</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
