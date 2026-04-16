import React from 'react';
import { Card, CardContent } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { CheckCircle2, Star, Heart, Car, Shirt, CalendarDays } from 'lucide-react';
import { statusColors, timeAgo } from '../../../lib/utils';
import { categoryConfig, statusSteps } from '../constants';
import { useGuest } from '../GuestContext';

export default function RequestsTab({ requests, myBookings, ratingForm, setRatingForm, onRate, onShowRequestForm }) {
  const { lang, t } = useGuest();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{t('My Requests', 'Taleplerim')}</h3>
        <Button size="sm" onClick={onShowRequestForm}>{t('New Request', 'Yeni Talep')}</Button>
      </div>

      {requests.length === 0 && (
        <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
          <CheckCircle2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">{t('No requests yet', 'Henuz talep yok')}</p>
        </div>
      )}

      {requests.map(req => {
        const cat = categoryConfig[req.category] || categoryConfig.other;
        const Icon = cat.icon;
        const stepIndex = statusSteps.indexOf(req.status);
        return (
          <Card key={req.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <div className="flex items-start gap-3 mb-3">
                <div className={`w-9 h-9 rounded-lg ${cat.bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-4 h-4 ${cat.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{req.description}</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{timeAgo(req.created_at)}</p>
                </div>
                <Badge className={`${statusColors[req.status]} text-[10px]`}>{req.status.replace('_', ' ')}</Badge>
              </div>
              <div className="flex items-center gap-1 mb-2">
                {statusSteps.map((step, i) => (
                  <React.Fragment key={step}>
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] ${
                      i <= stepIndex ? 'bg-[hsl(var(--primary))] text-white' : 'bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))]'
                    }`}>
                      {i <= stepIndex ? <CheckCircle2 className="w-3 h-3" /> : i + 1}
                    </div>
                    {i < statusSteps.length - 1 && <div className={`flex-1 h-0.5 ${i < stepIndex ? 'bg-[hsl(var(--primary))]' : 'bg-[hsl(var(--secondary))]'}`} />}
                  </React.Fragment>
                ))}
              </div>
              {req.status === 'DONE' && !req.rating && (
                <div className="border-t border-[hsl(var(--border))] pt-2 mt-2">
                  <p className="text-[10px] text-[hsl(var(--muted-foreground))] mb-1">{t('Rate this service:', 'Bu hizmeti degerlendirin:')}</p>
                  <div className="flex gap-1 mb-1">
                    {[1,2,3,4,5].map(n => (
                      <button key={n} onClick={() => setRatingForm({...ratingForm, requestId: req.id, rating: n})}>
                        <Star className={`w-5 h-5 ${ratingForm.requestId === req.id && ratingForm.rating >= n ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />
                      </button>
                    ))}
                  </div>
                  {ratingForm.requestId === req.id && ratingForm.rating > 0 && (
                    <Button size="sm" className="mt-1 h-7 text-xs" onClick={() => onRate(req.id)}>
                      {t('Submit Rating', 'Gonder')}
                    </Button>
                  )}
                </div>
              )}
              {req.rating && (
                <div className="flex items-center gap-1 text-xs text-amber-400 mt-1">
                  {[...Array(req.rating)].map((_, i) => <Star key={i} className="w-3 h-3 fill-amber-400" />)}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}

      {myBookings.spa_bookings?.length > 0 && (
        <>
          <h4 className="font-semibold text-sm mt-4 flex items-center gap-2">
            <Heart className="w-4 h-4 text-pink-400" /> {t('Spa Bookings', 'Spa Randevulari')}
          </h4>
          {myBookings.spa_bookings.map(b => (
            <Card key={b.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{b.service_type}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{b.preferred_date} {b.preferred_time} · {b.persons} {t('person', 'kisi')}</p>
                  </div>
                  <Badge className={b.status === 'CONFIRMED' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}>{b.status}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </>
      )}

      {myBookings.transport_requests?.length > 0 && (
        <>
          <h4 className="font-semibold text-sm mt-4 flex items-center gap-2">
            <Car className="w-4 h-4 text-orange-400" /> {t('Transport Requests', 'Transfer Talepleri')}
          </h4>
          {myBookings.transport_requests.map(tr => (
            <Card key={tr.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{tr.transport_type} → {tr.destination}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{tr.pickup_date} {tr.pickup_time} · {tr.passengers} {t('passengers', 'yolcu')}</p>
                  </div>
                  <Badge className={tr.status === 'CONFIRMED' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}>{tr.status}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </>
      )}

      {myBookings.laundry_requests?.length > 0 && (
        <>
          <h4 className="font-semibold text-sm mt-4 flex items-center gap-2">
            <Shirt className="w-4 h-4 text-cyan-400" /> {t('Laundry Requests', 'Camasir Talepleri')}
          </h4>
          {myBookings.laundry_requests.map(lr => (
            <Card key={lr.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{lr.service_type} - {lr.items_description || t('Laundry', 'Camasir')}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{timeAgo(lr.created_at)}</p>
                  </div>
                  <Badge className={lr.status === 'DONE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}>{lr.status}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </>
      )}

      {(() => {
        const rezList = myBookings.restaurant_reservations || [];
        return rezList.length > 0 ? (
          <>
            <h4 className="font-semibold text-sm mt-4 flex items-center gap-2">
              <CalendarDays className="w-4 h-4 text-violet-400" /> {t('Restaurant Reservations', 'Restoran Rezervasyonlari')}
            </h4>
            {rezList.map(rz => (
              <Card key={rz.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">{rz.restaurant_name}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{rz.date} {rz.time} · {rz.party_size} {t('guests', 'kisi')}</p>
                    </div>
                    <Badge className={rz.status === 'confirmed' ? 'bg-emerald-500/20 text-emerald-400' : rz.status === 'cancelled' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}>{rz.status}</Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </>
        ) : null;
      })()}
    </div>
  );
}
