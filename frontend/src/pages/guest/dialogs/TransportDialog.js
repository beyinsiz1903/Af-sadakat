import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Car, Loader2 } from 'lucide-react';
import { useGuest } from '../GuestContext';

export default function TransportDialog({ open, onOpenChange, transportForm, setTransportForm, guestName, setGuestName, submitting, onSubmit }) {
  const { t } = useGuest();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md">
        <DialogHeader><DialogTitle>{t('Transport Request', 'Transfer Talebi')}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <Select value={transportForm.transport_type} onValueChange={(v) => setTransportForm({...transportForm, transport_type: v})}>
            <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="taxi">{t('Taxi', 'Taksi')}</SelectItem>
              <SelectItem value="airport_transfer">{t('Airport Transfer', 'Havalimani Transfer')}</SelectItem>
              <SelectItem value="shuttle">{t('Hotel Shuttle', 'Otel Servisi')}</SelectItem>
              <SelectItem value="car_rental">{t('Car Rental', 'Arac Kiralama')}</SelectItem>
            </SelectContent>
          </Select>
          <Input value={transportForm.destination} onChange={(e) => setTransportForm({...transportForm, destination: e.target.value})} placeholder={t('Destination', 'Varilacak Yer')} className="bg-[hsl(var(--secondary))]" />
          <div className="grid grid-cols-2 gap-2">
            <Input type="date" value={transportForm.pickup_date} onChange={(e) => setTransportForm({...transportForm, pickup_date: e.target.value})} className="bg-[hsl(var(--secondary))]" />
            <Input type="time" value={transportForm.pickup_time} onChange={(e) => setTransportForm({...transportForm, pickup_time: e.target.value})} className="bg-[hsl(var(--secondary))]" />
          </div>
          <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} placeholder={t('Your name', 'Adiniz')} className="bg-[hsl(var(--secondary))]" />
          <Button className="w-full" onClick={onSubmit} disabled={submitting}>
            {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Car className="w-4 h-4 mr-2" />}
            {t('Request Transport', 'Transfer Talep Et')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
