import React, { useState, useEffect } from 'react';
import { useGuest } from '../GuestContext';
import { guestServicesAPI } from '../../../lib/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { LogOut, Loader2, Check, Star } from 'lucide-react';
import { toast } from 'sonner';

export default function CheckoutDialog({ open, onOpenChange }) {
  const { tenantSlug, roomCode, t } = useGuest();
  const [folio, setFolio] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [rating, setRating] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (open && !folio) {
      setLoading(true);
      guestServicesAPI.getRoomFolio(tenantSlug, roomCode)
        .then(res => setFolio(res.data))
        .catch(() => setFolio({ items: [], total: 0 }))
        .finally(() => setLoading(false));
    }
  }, [open]);

  const handleCheckout = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.expressCheckout(tenantSlug, roomCode, {
        folio_confirmed: confirmed, feedback, rating, payment_method: 'room_charge'
      });
      setDone(true);
      toast.success(t('Checkout request submitted!', 'Cikis talebiniz alindi!'));
    } catch (e) { toast.error(t('Failed', 'Hata')); }
    finally { setSubmitting(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-sm max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LogOut className="w-5 h-5" /> {t('Express Check-out', 'Hizli Cikis')}
          </DialogTitle>
        </DialogHeader>

        {done ? (
          <div className="text-center py-6">
            <Check className="w-12 h-12 mx-auto mb-3 text-emerald-400" />
            <h3 className="text-lg font-bold mb-1">{t('Check-out Submitted', 'Cikis Talebi Alindi')}</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {t('Front desk will process your checkout. Please return your key cards.', 'Resepsiyon cikinizi isleme alacak. Lutfen anahtar kartlarinizi birakmayi unutmayin.')}
            </p>
          </div>
        ) : loading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
        ) : (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium mb-2">{t('Your Folio Summary', 'Folyo Ozetiniz')}</h4>
              {folio?.items?.length > 0 ? (
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {folio.items.map((item, i) => (
                    <div key={i} className="flex items-center justify-between text-xs bg-[hsl(var(--secondary))] rounded px-2 py-1.5">
                      <span>{item.description || item.type}</span>
                      <span className="font-medium">{item.amount?.toLocaleString()} TRY</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[hsl(var(--muted-foreground))]">{t('No charges', 'Harcama yok')}</p>
              )}
              <div className="flex justify-between mt-2 pt-2 border-t border-[hsl(var(--border))] font-bold text-sm">
                <span>{t('Total', 'Toplam')}</span>
                <span>{(folio?.total || 0).toLocaleString()} TRY</span>
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} className="rounded" />
              {t('I confirm the folio is correct', 'Folyonun dogru oldugunu onayliyorum')}
            </label>

            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">{t('Rate your stay (optional)', 'Konaklamanizi puanlayin (opsiyonel)')}</p>
              <div className="flex gap-1">
                {[1,2,3,4,5].map(s => (
                  <button key={s} onClick={() => setRating(s)}>
                    <Star className={`w-6 h-6 ${s <= rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'}`} />
                  </button>
                ))}
              </div>
            </div>

            <Input placeholder={t('Any feedback? (optional)', 'Geri bildiriminiz? (opsiyonel)')} value={feedback} onChange={e => setFeedback(e.target.value)} />

            <Button className="w-full" disabled={!confirmed || submitting} onClick={handleCheckout}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : t('Submit Check-out', 'Cikis Talebini Gonder')}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
