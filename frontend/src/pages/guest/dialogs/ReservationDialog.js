import React, { useState } from 'react';
import { useGuest } from '../GuestContext';
import { guestAPI } from '../../../lib/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { CalendarDays, Loader2, Check, Users, BedDouble } from 'lucide-react';
import { toast } from 'sonner';

export default function ReservationDialog({ open, onOpenChange }) {
  const { tenantSlug, lang, guestName: ctxName, guestPhone: ctxPhone, t } = useGuest();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [rooms, setRooms] = useState([]);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [form, setForm] = useState({
    check_in: '', check_out: '', guests_count: 1,
    guest_name: ctxName || '', guest_phone: ctxPhone || '', guest_email: '',
    special_requests: ''
  });
  const [confirmation, setConfirmation] = useState(null);

  const handleSearch = async () => {
    if (!form.check_in || !form.check_out) return;
    setLoading(true);
    try {
      const res = await guestAPI.checkAvailability(tenantSlug, {
        check_in: form.check_in, check_out: form.check_out, guests: form.guests_count
      });
      setRooms(res.data?.available_rooms || []);
      setStep(2);
    } catch (e) { toast.error(t('Failed to check availability', 'Musaitlik kontrol edilemedi')); }
    finally { setLoading(false); }
  };

  const handleReserve = async () => {
    if (!selectedRoom || !form.guest_name) return;
    setSubmitting(true);
    try {
      const res = await guestAPI.createGuestReservation(tenantSlug, {
        ...form, room_type: selectedRoom.room_type
      });
      setConfirmation(res.data);
      setStep(3);
      toast.success(t('Reservation created!', 'Rezervasyon olusturuldu!'));
    } catch (e) { toast.error(e.response?.data?.detail || t('Failed', 'Hata')); }
    finally { setSubmitting(false); }
  };

  const reset = () => {
    setStep(1); setRooms([]); setSelectedRoom(null); setConfirmation(null);
    setForm({ check_in: '', check_out: '', guests_count: 1, guest_name: ctxName || '', guest_phone: ctxPhone || '', guest_email: '', special_requests: '' });
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if(!o) reset(); }}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-sm max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BedDouble className="w-5 h-5" /> {t('Book a Room', 'Oda Rezervasyonu')}
          </DialogTitle>
        </DialogHeader>

        {step === 1 && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-[hsl(var(--muted-foreground))]">{t('Check-in', 'Giris')}</label>
                <Input type="date" value={form.check_in} onChange={e => setForm({...form, check_in: e.target.value})} />
              </div>
              <div>
                <label className="text-xs text-[hsl(var(--muted-foreground))]">{t('Check-out', 'Cikis')}</label>
                <Input type="date" value={form.check_out} onChange={e => setForm({...form, check_out: e.target.value})} min={form.check_in} />
              </div>
            </div>
            <div>
              <label className="text-xs text-[hsl(var(--muted-foreground))]">{t('Guests', 'Misafir Sayisi')}</label>
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                <Input type="number" min={1} max={6} value={form.guests_count} onChange={e => setForm({...form, guests_count: parseInt(e.target.value) || 1})} className="w-20" />
              </div>
            </div>
            <Button className="w-full" disabled={!form.check_in || !form.check_out || loading} onClick={handleSearch}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : t('Search Availability', 'Musaitlik Ara')}
            </Button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            {rooms.length === 0 ? (
              <p className="text-sm text-center text-[hsl(var(--muted-foreground))] py-4">{t('No rooms available for selected dates', 'Secilen tarihlerde uygun oda yok')}</p>
            ) : (
              <div className="space-y-2">
                {rooms.map((rm, i) => (
                  <button key={i} onClick={() => setSelectedRoom(rm)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${selectedRoom?.room_type === rm.room_type ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/10' : 'border-[hsl(var(--border))] bg-[hsl(var(--secondary))]'}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-sm font-medium">{rm.display_name}</p>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">{rm.rooms_available} {t('rooms left', 'oda kaldi')} | {rm.nights} {t('nights', 'gece')}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-[hsl(var(--primary))]">{rm.total_price?.toLocaleString()} {rm.currency}</p>
                        <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{rm.base_price?.toLocaleString()}/{t('night', 'gece')}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {selectedRoom && (
              <div className="space-y-2 pt-2 border-t border-[hsl(var(--border))]">
                <Input placeholder={t('Your Name', 'Adiniz')} value={form.guest_name} onChange={e => setForm({...form, guest_name: e.target.value})} />
                <Input placeholder={t('Phone', 'Telefon')} value={form.guest_phone} onChange={e => setForm({...form, guest_phone: e.target.value})} />
                <Input placeholder={t('Email', 'E-posta')} value={form.guest_email} onChange={e => setForm({...form, guest_email: e.target.value})} />
                <Input placeholder={t('Special Requests (optional)', 'Ozel Istekler (opsiyonel)')} value={form.special_requests} onChange={e => setForm({...form, special_requests: e.target.value})} />
                <Button className="w-full" disabled={!form.guest_name || submitting} onClick={handleReserve}>
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : t('Confirm Reservation', 'Rezervasyonu Onayla')}
                </Button>
              </div>
            )}
            <button className="w-full text-xs text-[hsl(var(--muted-foreground))] hover:underline" onClick={() => { setStep(1); setRooms([]); setSelectedRoom(null); }}>
              {t('Change dates', 'Tarihleri degistir')}
            </button>
          </div>
        )}

        {step === 3 && confirmation && (
          <div className="text-center py-4 space-y-3">
            <Check className="w-12 h-12 mx-auto text-emerald-400" />
            <h3 className="text-lg font-bold">{t('Reservation Confirmed!', 'Rezervasyon Onaylandi!')}</h3>
            <div className="bg-[hsl(var(--secondary))] rounded-lg p-3 text-sm space-y-1">
              <p>{t('Confirmation Code', 'Onay Kodu')}: <strong className="text-[hsl(var(--primary))]">{confirmation.confirmation_code}</strong></p>
              <p>{selectedRoom?.display_name} | {form.check_in} → {form.check_out}</p>
              <p>{selectedRoom?.total_price?.toLocaleString()} {selectedRoom?.currency}</p>
            </div>
            <Button variant="outline" className="w-full" onClick={() => { onOpenChange(false); reset(); }}>
              {t('Close', 'Kapat')}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
