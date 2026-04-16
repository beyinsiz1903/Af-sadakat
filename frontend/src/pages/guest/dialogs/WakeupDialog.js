import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Textarea } from '../../../components/ui/textarea';
import { AlarmClock, Loader2 } from 'lucide-react';
import { useGuest } from '../GuestContext';

export default function WakeupDialog({ open, onOpenChange, wakeupForm, setWakeupForm, submitting, onSubmit }) {
  const { t } = useGuest();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md">
        <DialogHeader><DialogTitle>{t('Wake-up Call', 'Uyandirma Servisi')}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Input type="date" value={wakeupForm.wakeup_date} onChange={(e) => setWakeupForm({...wakeupForm, wakeup_date: e.target.value})} className="bg-[hsl(var(--secondary))]" />
            <Input type="time" value={wakeupForm.wakeup_time} onChange={(e) => setWakeupForm({...wakeupForm, wakeup_time: e.target.value})} className="bg-[hsl(var(--secondary))]" />
          </div>
          <Textarea value={wakeupForm.notes} onChange={(e) => setWakeupForm({...wakeupForm, notes: e.target.value})} placeholder={t('Notes (e.g. second call after 5 min)', 'Notlar')} className="bg-[hsl(var(--secondary))]" />
          <Button className="w-full" onClick={onSubmit} disabled={submitting}>
            {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <AlarmClock className="w-4 h-4 mr-2" />}
            {t('Set Wake-up Call', 'Uyandirma Ayarla')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
