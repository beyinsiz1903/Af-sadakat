import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Gift, CreditCard, CalendarDays, Plus, Link, CheckCircle2, Clock, Send, Loader2 } from 'lucide-react';
import { formatDate, formatCurrency } from '../lib/utils';
import { toast } from 'sonner';

const offerStatusColors = {
  draft: 'bg-gray-500/10 text-gray-400 border-gray-500/25',
  sent: 'bg-blue-500/10 text-blue-400 border-blue-500/25',
  accepted: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  expired: 'bg-rose-500/10 text-rose-400 border-rose-500/25',
};

export default function OffersPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newOffer, setNewOffer] = useState({
    guest_name: '', guest_email: '', guest_phone: '',
    room_type: 'standard', check_in: '', check_out: '',
    price: '', currency: 'TRY', notes: ''
  });

  const { data: offers = [] } = useQuery({
    queryKey: ['offers', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/offers`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: reservations = [] } = useQuery({
    queryKey: ['reservations', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/reservations`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const createOfferMutation = useMutation({
    mutationFn: (data) => api.post(`/tenants/${tenant?.slug}/offers`, { ...data, price: parseFloat(data.price), created_by: user?.id }),
    onSuccess: () => {
      queryClient.invalidateQueries(['offers']);
      toast.success('Offer created');
      setDialogOpen(false);
      setNewOffer({ guest_name: '', guest_email: '', guest_phone: '', room_type: 'standard', check_in: '', check_out: '', price: '', currency: 'TRY', notes: '' });
    },
  });

  const generateLinkMutation = useMutation({
    mutationFn: (offerId) => api.post(`/tenants/${tenant?.slug}/offers/${offerId}/generate-payment-link`),
    onSuccess: () => {
      queryClient.invalidateQueries(['offers']);
      toast.success('Payment link generated (stub)');
    },
  });

  const simulatePaymentMutation = useMutation({
    mutationFn: (linkId) => api.post(`/payments/mock/succeed/${linkId}`),
    onSuccess: () => {
      queryClient.invalidateQueries(['offers', 'reservations']);
      toast.success('Payment simulated! Reservation created.');
    },
  });

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Offers & Reservations</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{offers.length} offers, {reservations.length} reservations</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="create-offer-btn"><Plus className="w-4 h-4 mr-2" /> Create Offer</Button>
          </DialogTrigger>
          <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-lg">
            <DialogHeader><DialogTitle>Create Offer</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Input value={newOffer.guest_name} onChange={(e) => setNewOffer({...newOffer, guest_name: e.target.value})} placeholder="Guest Name" className="bg-[hsl(var(--secondary))]" data-testid="offer-guest-name" />
                <Input value={newOffer.guest_email} onChange={(e) => setNewOffer({...newOffer, guest_email: e.target.value})} placeholder="Email" className="bg-[hsl(var(--secondary))]" />
              </div>
              <Input value={newOffer.guest_phone} onChange={(e) => setNewOffer({...newOffer, guest_phone: e.target.value})} placeholder="Phone" className="bg-[hsl(var(--secondary))]" />
              <div className="grid grid-cols-3 gap-3">
                <Select value={newOffer.room_type} onValueChange={(v) => setNewOffer({...newOffer, room_type: v})}>
                  <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">Standard</SelectItem>
                    <SelectItem value="deluxe">Deluxe</SelectItem>
                    <SelectItem value="suite">Suite</SelectItem>
                  </SelectContent>
                </Select>
                <Input type="date" value={newOffer.check_in} onChange={(e) => setNewOffer({...newOffer, check_in: e.target.value})} className="bg-[hsl(var(--secondary))]" />
                <Input type="date" value={newOffer.check_out} onChange={(e) => setNewOffer({...newOffer, check_out: e.target.value})} className="bg-[hsl(var(--secondary))]" />
              </div>
              <Input type="number" value={newOffer.price} onChange={(e) => setNewOffer({...newOffer, price: e.target.value})} placeholder="Price (TRY)" className="bg-[hsl(var(--secondary))]" data-testid="offer-price" />
              <Textarea value={newOffer.notes} onChange={(e) => setNewOffer({...newOffer, notes: e.target.value})} placeholder="Notes / Inclusions" className="bg-[hsl(var(--secondary))]" />
              <Button onClick={() => createOfferMutation.mutate(newOffer)} disabled={!newOffer.guest_name || !newOffer.price} className="w-full" data-testid="submit-offer-btn">
                Create Offer
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Tabs defaultValue="offers">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="offers"><Gift className="w-4 h-4 mr-2" /> Offers ({offers.length})</TabsTrigger>
          <TabsTrigger value="reservations"><CalendarDays className="w-4 h-4 mr-2" /> Reservations ({reservations.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="offers" className="mt-4">
          <div className="space-y-3">
            {offers.map(offer => (
              <Card key={offer.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold">{offer.guest_name}</h3>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        {offer.room_type} - {offer.check_in} to {offer.check_out}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={`${offerStatusColors[offer.status]} border text-xs`}>{offer.status}</Badge>
                      <span className="font-bold">{formatCurrency(offer.price)}</span>
                    </div>
                  </div>
                  {offer.notes && <p className="text-sm text-[hsl(var(--muted-foreground))] mb-3">{offer.notes}</p>}
                  <div className="flex gap-2">
                    {offer.status === 'draft' && (
                      <Button size="sm" variant="outline" onClick={() => generateLinkMutation.mutate(offer.id)} data-testid={`generate-link-${offer.id}`}>
                        <Link className="w-3 h-3 mr-1" /> Generate Payment Link
                      </Button>
                    )}
                    {offer.status === 'sent' && offer.payment_link_id && (
                      <Button size="sm" onClick={() => simulatePaymentMutation.mutate(offer.payment_link_id)} data-testid={`simulate-payment-${offer.id}`}>
                        <CreditCard className="w-3 h-3 mr-1" /> Simulate Payment
                      </Button>
                    )}
                    {offer.status === 'accepted' && (
                      <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/25 border">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> Reservation Created
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
            {offers.length === 0 && (
              <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
                <Gift className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No offers yet. Create your first offer above.</p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="reservations" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <Table>
              <TableHeader>
                <TableRow className="border-[hsl(var(--border))]">
                  <TableHead>Guest</TableHead>
                  <TableHead>Room</TableHead>
                  <TableHead>Check-in</TableHead>
                  <TableHead>Check-out</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reservations.map(res => (
                  <TableRow key={res.id} className="border-[hsl(var(--border))]">
                    <TableCell className="font-medium">{res.guest_name}</TableCell>
                    <TableCell className="capitalize">{res.room_type}</TableCell>
                    <TableCell>{res.check_in}</TableCell>
                    <TableCell>{res.check_out}</TableCell>
                    <TableCell>{formatCurrency(res.price)}</TableCell>
                    <TableCell><Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/25 border text-xs">{res.status}</Badge></TableCell>
                  </TableRow>
                ))}
                {reservations.length === 0 && (
                  <TableRow><TableCell colSpan={6} className="text-center py-8 text-[hsl(var(--muted-foreground))]">No reservations yet</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
