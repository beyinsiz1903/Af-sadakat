import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Textarea } from '../../../components/ui/textarea';
import { Heart, Loader2 } from 'lucide-react';
import { useGuest } from '../GuestContext';

export default function SpaDialog({ open, onOpenChange, spaServices, spaForm, setSpaForm, guestName, setGuestName, submitting, onSubmit }) {
  const { t } = useGuest();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{t('Spa & Wellness Booking', 'Spa Randevusu')}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          {spaServices.map(s => (
            <button key={s.id} onClick={() => setSpaForm({...spaForm, service_type: s.name})}
              className={`w-full text-left p-3 rounded-lg border transition-all ${spaForm.service_type === s.name ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]' : 'border-[hsl(var(--border))]'}`}>
              <div className="flex justify-between"><span className="text-sm font-medium">{s.name}</span><span className="text-sm font-bold text-[hsl(var(--primary))]">{s.price} TRY</span></div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">{s.description} • {s.duration_minutes} min</p>
            </button>
          ))}
          <div className="grid grid-cols-2 gap-2">
            <Input type="date" value={spaForm.preferred_date} onChange={(e) => setSpaForm({...spaForm, preferred_date: e.target.value})} className="bg-[hsl(var(--secondary))]" />
            <Input type="time" value={spaForm.preferred_time} onChange={(e) => setSpaForm({...spaForm, preferred_time: e.target.value})} className="bg-[hsl(var(--secondary))]" />
          </div>
          <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} placeholder={t('Your name', 'Adiniz')} className="bg-[hsl(var(--secondary))]" />
          <Textarea value={spaForm.notes} onChange={(e) => setSpaForm({...spaForm, notes: e.target.value})} placeholder={t('Notes', 'Notlar')} className="bg-[hsl(var(--secondary))]" />
          <Button className="w-full" onClick={onSubmit} disabled={!spaForm.service_type || submitting}>
            {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Heart className="w-4 h-4 mr-2" />}
            {t('Book Spa', 'Randevu Al')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
