import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { guestServicesAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { CalendarDays, Clock, Users, CheckCircle2, XCircle, UtensilsCrossed, Loader2, MapPin } from 'lucide-react';
import { toast } from 'sonner';

const statusColors = {
  pending: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  confirmed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  cancelled: 'bg-red-500/20 text-red-400 border-red-500/30',
  completed: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  no_show: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

export default function RestaurantReservationsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().split('T')[0]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [restaurantFilter, setRestaurantFilter] = useState('all');
  const [detailDialog, setDetailDialog] = useState(null);
  const [tableNumber, setTableNumber] = useState('');

  const { data: restaurants = [] } = useQuery({
    queryKey: ['admin-restaurants', tenant?.slug],
    queryFn: () => guestServicesAPI.listRestaurantsAdmin(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const params = {};
  if (dateFilter) params.date = dateFilter;
  if (statusFilter !== 'all') params.status = statusFilter;
  if (restaurantFilter !== 'all') params.restaurant_id = restaurantFilter;

  const { data: reservations = [], isLoading } = useQuery({
    queryKey: ['restaurant-reservations', tenant?.slug, dateFilter, statusFilter, restaurantFilter],
    queryFn: () => guestServicesAPI.listRestaurantReservations(tenant?.slug, params).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const updateReservation = useMutation({
    mutationFn: ({ id, data }) => guestServicesAPI.updateRestaurantReservation(tenant?.slug, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['restaurant-reservations']);
      toast.success('Reservation updated');
      setDetailDialog(null);
    },
  });

  const pendingCount = reservations.filter(r => r.status === 'pending').length;
  const confirmedCount = reservations.filter(r => r.status === 'confirmed').length;
  const totalGuests = reservations.filter(r => ['pending', 'confirmed'].includes(r.status)).reduce((sum, r) => sum + (r.party_size || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Restaurant Reservations</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Manage à la carte restaurant bookings</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <CalendarDays className="w-5 h-5 mx-auto mb-1 text-violet-400" />
            <p className="text-2xl font-bold">{reservations.length}</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Total Today</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <Clock className="w-5 h-5 mx-auto mb-1 text-amber-400" />
            <p className="text-2xl font-bold">{pendingCount}</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Pending</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <CheckCircle2 className="w-5 h-5 mx-auto mb-1 text-emerald-400" />
            <p className="text-2xl font-bold">{confirmedCount}</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Confirmed</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4 text-center">
            <Users className="w-5 h-5 mx-auto mb-1 text-blue-400" />
            <p className="text-2xl font-bold">{totalGuests}</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Expected Guests</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-3 items-center flex-wrap">
        <Input type="date" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} className="w-44" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-36"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="confirmed">Confirmed</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="no_show">No Show</SelectItem>
          </SelectContent>
        </Select>
        <Select value={restaurantFilter} onValueChange={setRestaurantFilter}>
          <SelectTrigger className="w-48"><SelectValue placeholder="Restaurant" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Restaurants</SelectItem>
            {restaurants.map(r => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Timeline View */}
      {isLoading ? <Loader2 className="w-6 h-6 animate-spin" /> : (
        <div className="space-y-2">
          {reservations.length === 0 && (
            <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
              <UtensilsCrossed className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No reservations for this date</p>
            </div>
          )}
          {reservations.map(rez => (
            <Card key={rez.id} className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all cursor-pointer ${rez.status === 'pending' ? 'border-l-2 border-l-amber-400' : ''}`}
              onClick={() => { setDetailDialog(rez); setTableNumber(rez.table_number || ''); }}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="text-center min-w-[60px]">
                      <p className="text-lg font-bold text-[hsl(var(--primary))]">{rez.time}</p>
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{rez.date}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-sm">{rez.guest_name || 'Guest'}</p>
                        <Badge className="text-[10px]" variant="outline">Room {rez.room_number}</Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                        <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {rez.party_size} guests</span>
                        <span className="flex items-center gap-1"><UtensilsCrossed className="w-3 h-3" /> {rez.restaurant_name}</span>
                        {rez.seating_preference && rez.seating_preference !== 'no_preference' && (
                          <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {rez.seating_preference}</span>
                        )}
                        {rez.occasion && rez.occasion !== 'none' && (
                          <Badge className="text-[9px] bg-pink-500/10 text-pink-400">{rez.occasion}</Badge>
                        )}
                        {rez.table_number && (
                          <Badge className="text-[9px] bg-blue-500/10 text-blue-400">Table {rez.table_number}</Badge>
                        )}
                      </div>
                      {rez.special_requests && (
                        <p className="text-[10px] text-amber-400 mt-1">Note: {rez.special_requests}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={statusColors[rez.status]}>{rez.status}</Badge>
                    {rez.status === 'pending' && (
                      <div className="flex gap-1">
                        <Button size="sm" className="h-7 bg-emerald-600 hover:bg-emerald-700" onClick={(e) => { e.stopPropagation(); updateReservation.mutate({ id: rez.id, data: { status: 'confirmed' } }); }}>
                          <CheckCircle2 className="w-3 h-3 mr-1" /> Confirm
                        </Button>
                        <Button size="sm" variant="ghost" className="h-7 text-red-400" onClick={(e) => { e.stopPropagation(); updateReservation.mutate({ id: rez.id, data: { status: 'cancelled' } }); }}>
                          <XCircle className="w-3 h-3" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Detail Dialog */}
      <Dialog open={!!detailDialog} onOpenChange={() => setDetailDialog(null)}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <DialogHeader><DialogTitle>Reservation Detail</DialogTitle></DialogHeader>
          {detailDialog && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Guest</p><p className="font-medium">{detailDialog.guest_name || '-'}</p></div>
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Room</p><p className="font-medium">{detailDialog.room_number}</p></div>
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Restaurant</p><p className="font-medium">{detailDialog.restaurant_name}</p></div>
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Party Size</p><p className="font-medium">{detailDialog.party_size} guests</p></div>
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Date & Time</p><p className="font-medium">{detailDialog.date} at {detailDialog.time}</p></div>
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Status</p><Badge className={statusColors[detailDialog.status]}>{detailDialog.status}</Badge></div>
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Seating</p><p className="font-medium">{detailDialog.seating_preference || '-'}</p></div>
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Occasion</p><p className="font-medium">{detailDialog.occasion || '-'}</p></div>
                {detailDialog.guest_phone && <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Phone</p><p className="font-medium">{detailDialog.guest_phone}</p></div>}
              </div>
              {detailDialog.special_requests && (
                <div><p className="text-xs text-[hsl(var(--muted-foreground))]">Special Requests</p><p className="text-sm bg-[hsl(var(--secondary))] rounded-lg p-2 mt-1">{detailDialog.special_requests}</p></div>
              )}
              <div>
                <label className="text-xs text-[hsl(var(--muted-foreground))]">Assign Table</label>
                <div className="flex gap-2 mt-1">
                  <Input value={tableNumber} onChange={(e) => setTableNumber(e.target.value)} placeholder="Table number" className="flex-1" />
                  <Button size="sm" onClick={() => updateReservation.mutate({ id: detailDialog.id, data: { table_number: tableNumber } })}>Assign</Button>
                </div>
              </div>
              <div className="flex gap-2">
                <Select onValueChange={(v) => updateReservation.mutate({ id: detailDialog.id, data: { status: v } })}>
                  <SelectTrigger><SelectValue placeholder="Change Status" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="confirmed">Confirmed</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                    <SelectItem value="no_show">No Show</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
