import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Settings, Info } from 'lucide-react';
import { categoryConfig } from '../constants';
import { useGuest } from '../GuestContext';

const prefItems = [
  { key: 'housekeeping', en: 'Housekeeping', tr: 'Kat Hizmeti' },
  { key: 'maintenance', en: 'Technical Service', tr: 'Teknik Servis' },
  { key: 'room_service', en: 'Room Service / Orders', tr: 'Oda Servisi / Siparişler' },
  { key: 'laundry', en: 'Laundry', tr: 'Çamaşır/Ütü' },
  { key: 'spa', en: 'Spa & Wellness', tr: 'Spa & Masaj' },
  { key: 'transport', en: 'Transport', tr: 'Transfer' },
  { key: 'wakeup', en: 'Wake-up Call', tr: 'Uyandırma' },
  { key: 'reception', en: 'Reception', tr: 'Resepsiyon' },
];

export default function NotifPrefsDialog({ open, onOpenChange, notifPrefs, onPrefChange }) {
  const { lang, t } = useGuest();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            {t('Notification Preferences', 'Bildirim Tercihleri')}
          </DialogTitle>
        </DialogHeader>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mb-3">
          {t('Choose which notifications you want to receive:', 'Hangi bildirimleri almak istediğinizi seçin:')}
        </p>
        <div className="space-y-2">
          {prefItems.map(item => {
            const catConf = categoryConfig[item.key] || {};
            const CatIcon = catConf.icon || Info;
            return (
              <button
                key={item.key}
                onClick={() => onPrefChange(item.key)}
                className="w-full flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--secondary))]/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${catConf.bg || 'bg-blue-500/10'}`}>
                    <CatIcon className={`w-4 h-4 ${catConf.color || 'text-blue-400'}`} />
                  </div>
                  <span className="text-sm font-medium">{lang === 'tr' ? item.tr : item.en}</span>
                </div>
                <div className={`w-10 h-6 rounded-full transition-colors flex items-center px-1 ${notifPrefs[item.key] ? 'bg-[hsl(var(--primary))] justify-end' : 'bg-[hsl(var(--muted))] justify-start'}`}>
                  <div className="w-4 h-4 bg-white rounded-full shadow" />
                </div>
              </button>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
