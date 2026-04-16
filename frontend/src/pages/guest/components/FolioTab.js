import React from 'react';
import { Card, CardContent } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { Loader2, UtensilsCrossed, Coffee, Heart, Shirt, Car, Receipt } from 'lucide-react';
import { useGuest } from '../GuestContext';

const folioTypeIcons = {
  room_service: UtensilsCrossed,
  minibar: Coffee,
  spa: Heart,
  laundry: Shirt,
  transport: Car,
};

const folioTypeColors = {
  room_service: 'text-emerald-400 bg-emerald-500/10',
  minibar: 'text-teal-400 bg-teal-500/10',
  spa: 'text-pink-400 bg-pink-500/10',
  laundry: 'text-cyan-400 bg-cyan-500/10',
  transport: 'text-orange-400 bg-orange-500/10',
};

export default function FolioTab({ folioData, folioLoading, onRefresh }) {
  const { lang, t } = useGuest();

  if (folioLoading) return (
    <div className="text-center py-8">
      <Loader2 className="w-6 h-6 animate-spin mx-auto text-[hsl(var(--primary))]" />
    </div>
  );

  if (!folioData) return null;

  return (
    <div className="space-y-3">
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-semibold text-sm">{t('Room Folio', 'Oda Folyosu')}</h3>
            <Button size="sm" variant="ghost" className="text-xs h-7" onClick={onRefresh}>
              {t('Refresh', 'Yenile')}
            </Button>
          </div>
          {folioData.guest_name && (
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              {folioData.guest_name} &bull; {t('Room', 'Oda')} {folioData.room_number}
            </p>
          )}
          {(folioData.check_in || folioData.check_out) && (
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">
              {folioData.check_in} &rarr; {folioData.check_out}
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-[hsl(var(--primary)/0.15)] to-[hsl(var(--primary)/0.05)] border-[hsl(var(--primary)/0.3)]">
        <CardContent className="p-4 text-center">
          <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">{t('Total Charges', 'Toplam Harcama')}</p>
          <p className="text-3xl font-bold text-[hsl(var(--primary))]">
            {folioData.total.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} <span className="text-sm font-normal">TRY</span>
          </p>
          <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-1">
            {folioData.items.length} {t('items', 'kalem')}
          </p>
        </CardContent>
      </Card>

      {folioData.items.length === 0 ? (
        <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
          <Receipt className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">{t('No charges yet', 'Henuz harcama yok')}</p>
          <p className="text-xs mt-1">{t('Your room service orders, spa bookings and other charges will appear here.', 'Oda servisi siparisleriniz, spa randevulariniz ve diger harcamalariniz burada gorunecek.')}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {folioData.items.map(item => {
            const Icon = folioTypeIcons[item.type] || Receipt;
            const colors = folioTypeColors[item.type] || 'text-gray-400 bg-gray-500/10';
            const [textColor, bgColor] = colors.split(' ');
            return (
              <Card key={item.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-lg ${bgColor} flex items-center justify-center flex-shrink-0`}>
                      <Icon className={`w-4 h-4 ${textColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold">{lang === 'tr' ? item.type_label : item.type_label_en}</p>
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))] truncate">{item.description}</p>
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))]">
                        {new Date(item.date).toLocaleDateString(lang === 'tr' ? 'tr-TR' : 'en-US', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-sm font-bold">{item.amount > 0 ? item.amount.toLocaleString('tr-TR') : '-'} <span className="text-[10px] font-normal">TRY</span></p>
                      <Badge className="text-[9px] mt-0.5">{item.status}</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
