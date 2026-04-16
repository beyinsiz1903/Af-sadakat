import React, { useState } from 'react';
import { useGuest } from '../GuestContext';
import { guestServicesAPI, uploadAPI } from '../../../lib/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { ClipboardCheck, Loader2, Check, Upload, Camera } from 'lucide-react';
import { toast } from 'sonner';

export default function CheckinDialog({ open, onOpenChange }) {
  const { tenantSlug, roomCode, t } = useGuest();
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [idPhoto, setIdPhoto] = useState(null);
  const [form, setForm] = useState({
    guest_name: '', guest_email: '', guest_phone: '',
    nationality: '', id_type: 'passport', id_number: '',
    arrival_time: '', special_requests: '', terms_accepted: false,
  });

  const handleSubmit = async () => {
    if (!form.guest_name || !form.terms_accepted) return;
    setSubmitting(true);
    try {
      let id_photo_id = '';
      if (idPhoto) {
        const fd = new FormData();
        fd.append('file', idPhoto);
        fd.append('entity_type', 'checkin');
        fd.append('room_code', roomCode);
        try {
          const upRes = await uploadAPI.guestUpload(tenantSlug, fd);
          id_photo_id = upRes.data?.file_id || '';
        } catch (ue) { console.error('Upload failed:', ue); }
      }
      await guestServicesAPI.digitalCheckin(tenantSlug, roomCode, { ...form, id_photo_id });
      setDone(true);
      toast.success(t('Check-in submitted!', 'Check-in gonderildi!'));
    } catch (e) { toast.error(t('Failed', 'Hata')); }
    finally { setSubmitting(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-sm max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5" /> {t('Digital Check-in', 'Dijital Check-in')}
          </DialogTitle>
        </DialogHeader>

        {done ? (
          <div className="text-center py-6">
            <Check className="w-12 h-12 mx-auto mb-3 text-emerald-400" />
            <h3 className="text-lg font-bold mb-1">{t('Check-in Submitted', 'Check-in Alindi')}</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {t('Everything is set! We will have your room ready.', 'Her sey hazir! Odanizi sizin icin hazirlayacagiz.')}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <Input placeholder={t('Full Name *', 'Ad Soyad *')} value={form.guest_name} onChange={e => setForm({...form, guest_name: e.target.value})} />
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder={t('Phone', 'Telefon')} value={form.guest_phone} onChange={e => setForm({...form, guest_phone: e.target.value})} />
              <Input placeholder={t('Email', 'E-posta')} value={form.guest_email} onChange={e => setForm({...form, guest_email: e.target.value})} />
            </div>
            <Input placeholder={t('Nationality', 'Uyruk')} value={form.nationality} onChange={e => setForm({...form, nationality: e.target.value})} />
            <div className="grid grid-cols-2 gap-2">
              <select value={form.id_type} onChange={e => setForm({...form, id_type: e.target.value})}
                className="bg-[hsl(var(--secondary))] border border-[hsl(var(--border))] rounded-md px-2 py-2 text-sm">
                <option value="passport">{t('Passport', 'Pasaport')}</option>
                <option value="id_card">{t('ID Card', 'Kimlik Karti')}</option>
                <option value="drivers_license">{t("Driver's License", 'Surucu Belgesi')}</option>
              </select>
              <Input placeholder={t('ID Number', 'Belge No')} value={form.id_number} onChange={e => setForm({...form, id_number: e.target.value})} />
            </div>
            <Input type="time" value={form.arrival_time} onChange={e => setForm({...form, arrival_time: e.target.value})} />
            <p className="text-xs text-[hsl(var(--muted-foreground))] -mt-2">{t('Estimated arrival time', 'Tahmini varis saati')}</p>

            <div>
              <label className="flex items-center gap-2 text-sm cursor-pointer bg-[hsl(var(--secondary))] rounded-lg p-3 border border-dashed border-[hsl(var(--border))]">
                <Camera className="w-5 h-5 text-[hsl(var(--muted-foreground))]" />
                <span className="flex-1 text-[hsl(var(--muted-foreground))]">
                  {idPhoto ? idPhoto.name : t('Upload ID photo (optional)', 'Kimlik fotografi yukle (opsiyonel)')}
                </span>
                <input type="file" accept="image/*" className="hidden" onChange={e => setIdPhoto(e.target.files?.[0] || null)} />
              </label>
            </div>

            <Input placeholder={t('Special Requests', 'Ozel Istekler')} value={form.special_requests} onChange={e => setForm({...form, special_requests: e.target.value})} />

            <label className="flex items-start gap-2 text-xs cursor-pointer">
              <input type="checkbox" checked={form.terms_accepted} onChange={e => setForm({...form, terms_accepted: e.target.checked})} className="rounded mt-0.5" />
              <span>{t('I confirm the information above is correct and I accept the hotel terms & conditions.', 'Yukaridaki bilgilerin dogru oldugunu onayliyorum ve otel kosullarini kabul ediyorum.')}</span>
            </label>

            <Button className="w-full" disabled={!form.guest_name || !form.terms_accepted || submitting} onClick={handleSubmit}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : t('Submit Check-in', 'Check-in Gonder')}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
