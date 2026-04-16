import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { CalendarDays, Loader2 } from 'lucide-react';
import { guestServicesAPI } from '../../../lib/api';
import { useGuest } from '../GuestContext';

export default function RestaurantDialog({
  open, onOpenChange, restaurants, restaurantForm, setRestaurantForm,
  selectedRestaurant, setSelectedRestaurant, availableSlots, setAvailableSlots,
  guestName, setGuestName, guestPhone, setGuestPhone, submitting, onSubmit
}) {
  const { tenantSlug, t } = useGuest();

  const checkSlots = async (date, partySize) => {
    if (date && restaurantForm.restaurant_id) {
      try {
        const res = await guestServicesAPI.checkAvailability(tenantSlug, restaurantForm.restaurant_id, { date, party_size: partySize });
        setAvailableSlots(res.data?.slots || []);
      } catch(e) { setAvailableSlots([]); }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{t('Restaurant Reservation', 'Restoran Rezervasyonu')}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium mb-2 text-[hsl(var(--muted-foreground))]">{t('Select Restaurant', 'Restoran Secin')}</p>
            {restaurants.map(r => (
              <button key={r.id} onClick={() => {
                setSelectedRestaurant(r);
                setRestaurantForm({...restaurantForm, restaurant_id: r.id, restaurant_name: r.name});
                setAvailableSlots([]);
              }}
                className={`w-full text-left p-3 mb-2 rounded-lg border transition-all ${
                  restaurantForm.restaurant_id === r.id ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]' : 'border-[hsl(var(--border))]'
                }`}>
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-semibold">{r.name}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{r.cuisine_type} · {r.location}</p>
                  </div>
                  <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{r.open_time}-{r.close_time}</span>
                </div>
                {r.description && <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{r.description}</p>}
                {r.dress_code && <p className="text-[10px] text-amber-400 mt-1">Dress code: {r.dress_code}</p>}
              </button>
            ))}
            {restaurants.length === 0 && (
              <p className="text-sm text-center text-[hsl(var(--muted-foreground))] py-4">{t('No restaurants available', 'Restoran bulunamadi')}</p>
            )}
          </div>

          {restaurantForm.restaurant_id && (<>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-[hsl(var(--muted-foreground))]">{t('Date', 'Tarih')}</label>
                <Input type="date" value={restaurantForm.date} onChange={async (e) => {
                  const date = e.target.value;
                  setRestaurantForm({...restaurantForm, date, time: ''});
                  checkSlots(date, restaurantForm.party_size);
                }} className="bg-[hsl(var(--secondary))]" />
              </div>
              <div>
                <label className="text-xs text-[hsl(var(--muted-foreground))]">{t('Guests', 'Kisi Sayisi')}</label>
                <Select value={String(restaurantForm.party_size)} onValueChange={async (v) => {
                  const ps = parseInt(v);
                  setRestaurantForm({...restaurantForm, party_size: ps, time: ''});
                  checkSlots(restaurantForm.date, ps);
                }}>
                  <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {[1,2,3,4,5,6,7,8,10,12].map(n => <SelectItem key={n} value={String(n)}>{n} {t('guests', 'kisi')}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {availableSlots.length > 0 && (
              <div>
                <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">{t('Select Time', 'Saat Secin')}</label>
                <div className="grid grid-cols-4 gap-1.5">
                  {availableSlots.map(slot => (
                    <button key={slot.time} disabled={!slot.is_available}
                      onClick={() => setRestaurantForm({...restaurantForm, time: slot.time})}
                      className={`py-2 px-1 rounded-lg text-center text-xs font-medium transition-all ${
                        restaurantForm.time === slot.time
                          ? 'bg-[hsl(var(--primary))] text-white'
                          : slot.is_available
                            ? 'bg-[hsl(var(--secondary))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]'
                            : 'bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))] opacity-40 cursor-not-allowed'
                      }`}>
                      {slot.time}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} placeholder={t('Your name', 'Adiniz')} className="bg-[hsl(var(--secondary))]" />
              <Input value={guestPhone} onChange={(e) => setGuestPhone(e.target.value)} placeholder={t('Phone', 'Telefon')} className="bg-[hsl(var(--secondary))]" />
            </div>

            <Select value={restaurantForm.seating_preference} onValueChange={(v) => setRestaurantForm({...restaurantForm, seating_preference: v})}>
              <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue placeholder={t('Seating Preference', 'Oturma Tercihi')} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="no_preference">{t('No Preference', 'Fark Etmez')}</SelectItem>
                <SelectItem value="window">{t('Window', 'Pencere Kenari')}</SelectItem>
                <SelectItem value="terrace">{t('Terrace', 'Teras')}</SelectItem>
                <SelectItem value="indoor">{t('Indoor', 'Ic Mekan')}</SelectItem>
                <SelectItem value="private">{t('Private Area', 'Ozel Alan')}</SelectItem>
              </SelectContent>
            </Select>

            <Select value={restaurantForm.occasion || "none"} onValueChange={(v) => setRestaurantForm({...restaurantForm, occasion: v === "none" ? "" : v})}>
              <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue placeholder={t('Occasion (Optional)', 'Ozel Gun (Opsiyonel)')} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">{t('None', 'Yok')}</SelectItem>
                <SelectItem value="birthday">{t('Birthday', 'Dogum Gunu')}</SelectItem>
                <SelectItem value="anniversary">{t('Anniversary', 'Yildonumu')}</SelectItem>
                <SelectItem value="business">{t('Business Dinner', 'Is Yemegi')}</SelectItem>
                <SelectItem value="romantic">{t('Romantic Dinner', 'Romantik Aksam Yemegi')}</SelectItem>
                <SelectItem value="celebration">{t('Celebration', 'Kutlama')}</SelectItem>
              </SelectContent>
            </Select>

            <Textarea value={restaurantForm.special_requests} onChange={(e) => setRestaurantForm({...restaurantForm, special_requests: e.target.value})}
              placeholder={t('Special requests (allergies, highchair, etc.)', 'Ozel istekler (alerji, mama sandalyesi vb.)')}
              className="bg-[hsl(var(--secondary))]" />

            <Button className="w-full" disabled={!restaurantForm.date || !restaurantForm.time || submitting} onClick={onSubmit}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CalendarDays className="w-4 h-4 mr-2" />}
              {t('Confirm Reservation', 'Rezervasyonu Onayla')}
            </Button>
          </>)}
        </div>
      </DialogContent>
    </Dialog>
  );
}
