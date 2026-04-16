import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Bell, Settings, Loader2, CheckCircle2, Info } from 'lucide-react';
import { timeAgo } from '../../../lib/utils';
import { categoryConfig } from '../constants';
import { useGuest } from '../GuestContext';

export default function NotificationPanel({
  open, onOpenChange, notifications, pushSubscribed, pushLoading,
  onPushToggle, onShowPrefs
}) {
  const { lang, t } = useGuest();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Bell className="w-5 h-5" />
              {t('Notifications', 'Bildirimler')}
            </span>
            <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onShowPrefs}>
              <Settings className="w-4 h-4" />
            </Button>
          </DialogTitle>
        </DialogHeader>

        {!pushSubscribed ? (
          <div className="text-center py-6">
            <Bell className="w-12 h-12 mx-auto mb-3 text-[hsl(var(--muted-foreground))]" />
            <h3 className="font-semibold mb-2">{t('Enable Notifications', 'Bildirimleri Aç')}</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
              {t(
                'Get notified when your request status changes — "Your laundry is ready", "Your order is on its way!"',
                'Talep durumunuz değiştiğinde bildirim alın — "Çamaşırlarınız hazır", "Siparişiniz yola çıktı!"'
              )}
            </p>
            <Button onClick={onPushToggle} disabled={pushLoading} className="w-full">
              {pushLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Bell className="w-4 h-4 mr-2" />}
              {t('Enable Push Notifications', 'Bildirimleri Etkinleştir')}
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between px-2 py-1.5 mb-2 bg-emerald-500/10 rounded-lg">
              <span className="text-xs text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {t('Notifications active', 'Bildirimler aktif')}
              </span>
              <Button size="sm" variant="ghost" className="h-6 text-xs text-red-400" onClick={onPushToggle} disabled={pushLoading}>
                {pushLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : t('Disable', 'Kapat')}
              </Button>
            </div>

            {notifications.length === 0 ? (
              <div className="text-center py-6 text-sm text-[hsl(var(--muted-foreground))]">
                {t('No notifications yet', 'Henüz bildirim yok')}
              </div>
            ) : (
              notifications.map((n, i) => {
                const catConf = categoryConfig[n.service_type] || {};
                const CatIcon = catConf.icon || Info;
                return (
                  <div key={n.id || i} className={`flex items-start gap-3 p-3 rounded-lg ${n.read ? 'bg-[hsl(var(--secondary))]/50' : 'bg-[hsl(var(--secondary))]'}`}>
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${catConf.bg || 'bg-blue-500/10'}`}>
                      <CatIcon className={`w-4 h-4 ${catConf.color || 'text-blue-400'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{lang === 'tr' ? n.title_tr : n.title_en}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{lang === 'tr' ? n.body_tr : n.body_en}</p>
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-1">{timeAgo(n.created_at)}</p>
                    </div>
                    {!n.read && <div className="w-2 h-2 bg-[hsl(var(--primary))] rounded-full mt-2 flex-shrink-0" />}
                  </div>
                );
              })
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
