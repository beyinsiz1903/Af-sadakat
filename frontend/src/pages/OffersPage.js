import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { offersAPI, reservationsAPI, paymentsAPI, propertiesAPI, contactsAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import {
  Gift, CreditCard, CalendarDays, Plus, Link2, CheckCircle2, Send, XCircle,
  Copy, ExternalLink, Download, Clock, Ban, Loader2
} from 'lucide-react';
import { formatDate, formatCurrency } from '../lib/utils';
import { toast } from 'sonner';

const statusColors = {
  DRAFT: 'bg-gray-500/10 text-gray-400 border-gray-500/25',
  SENT: 'bg-blue-500/10 text-blue-400 border-blue-500/25',
  PAID: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  EXPIRED: 'bg-rose-500/10 text-rose-400 border-rose-500/25',
  CANCELLED: 'bg-orange-500/10 text-orange-400 border-orange-500/25',
  CONFIRMED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
};

export default function OffersPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [newOffer, setNewOffer] = useState({
    guest_name: '', guest_email: '', guest_phone: '',
    room_type: 'standard', check_in: '', check_out: '',
    price: '', currency: 'TRY', notes: '', guests_count: '2'
  });

  const { data: offersData } = useQuery({
    queryKey: ['offers-v2', tenant?.slug, statusFilter],
    queryFn: () => offersAPI.list(tenant?.slug, { status: statusFilter || undefined }).then(r => r.data),
    enabled: !!tenant?.slug,
  });
  const offers = offersData?.data || [];
  const totalOffers = offersData?.total || 0;

  const { data: reservationsData } = useQuery({
    queryKey: ['reservations-v2', tenant?.slug],
    queryFn: () => reservationsAPI.list(tenant?.slug, {}).then(r => r.data),
    enabled: !!tenant?.slug,
  });
  const reservations = reservationsData?.data || [];

  const { data: properties = [] } = useQuery({
    queryKey: ['properties', tenant?.slug],
    queryFn: () => propertiesAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const createMutation = useMutation({
    mutationFn: (data) => offersAPI.create(tenant?.slug, {
      guest_name: data.guest_name,
      guest_email: data.guest_email,
      guest_phone: data.guest_phone,
      room_type: data.room_type,
      check_in: data.check_in,
      check_out: data.check_out,
      price_total: parseFloat(data.price),
      currency: data.currency,
      notes: data.notes,
      guests_count: parseInt(data.guests_count) || 2,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries(['offers-v2']);
      toast.success('Offer created');
      setDialogOpen(false);
      setNewOffer({ guest_name: '', guest_email: '', guest_phone: '', room_type: 'standard', check_in: '', check_out: '', price: '', currency: 'TRY', notes: '', guests_count: '2' });
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to create offer'),
  });

  const sendMutation = useMutation({
    mutationFn: (id) => offersAPI.send(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries(['offers-v2']); toast.success('Offer sent'); },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const cancelMutation = useMutation({
    mutationFn: (id) => offersAPI.cancel(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries(['offers-v2']); toast.success('Offer cancelled'); },
  });

  const createPaymentLinkMutation = useMutation({
    mutationFn: (id) => offersAPI.createPaymentLink(tenant?.slug, id),
    onSuccess: (res) => {
      queryClient.invalidateQueries(['offers-v2']);
      const url = res.data?.url;
      if (url) {
        navigator.clipboard.writeText(url).then(() => toast.success('Payment link created & copied!')).catch(() => toast.success('Payment link created'));
      } else {
        toast.success('Payment link created');
      }
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const simulatePaymentMutation = useMutation({
    mutationFn: (paymentLinkId) => paymentsAPI.mockSucceed({ paymentLinkId }),
    onSuccess: () => {
      queryClient.invalidateQueries(['offers-v2', 'reservations-v2']);
      toast.success('Payment simulated! Reservation created.');
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const cancelReservationMutation = useMutation({
    mutationFn: (id) => reservationsAPI.cancel(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries(['reservations-v2']); toast.success('Reservation cancelled'); },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const handleExportCSV = async () => {
    try {
      const res = await reservationsAPI.exportCSV(tenant?.slug, {});
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'reservations.csv';
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('CSV exported');
    } catch (e) {
      toast.error('Export failed');
    }
  };

  const copyPaymentUrl = (url) => {
    navigator.clipboard.writeText(url).then(() => toast.success('URL copied!'));
  };

  // Stats
  const sentCount = offers.filter(o => o.status === 'SENT').length;
  const paidCount = offers.filter(o => o.status === 'PAID').length;
  const conversionRate = sentCount + paidCount > 0 ? Math.round((paidCount / (sentCount + paidCount)) * 100) : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Offers & Reservations</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{totalOffers} offers, {reservations.length} reservations</p>
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
                <Input type="number" value={newOffer.guests_count} onChange={(e) => setNewOffer({...newOffer, guests_count: e.target.value})} placeholder="Guests" className="bg-[hsl(var(--secondary))]" />
                <Select value={newOffer.currency} onValueChange={(v) => setNewOffer({...newOffer, currency: v})}>
                  <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="TRY">TRY</SelectItem>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Check-in</label>
                  <Input type="date" value={newOffer.check_in} onChange={(e) => setNewOffer({...newOffer, check_in: e.target.value})} className="bg-[hsl(var(--secondary))]" />
                </div>
                <div>
                  <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Check-out</label>
                  <Input type="date" value={newOffer.check_out} onChange={(e) => setNewOffer({...newOffer, check_out: e.target.value})} className="bg-[hsl(var(--secondary))]" />
                </div>
              </div>
              <Input type="number" value={newOffer.price} onChange={(e) => setNewOffer({...newOffer, price: e.target.value})} placeholder="Total Price" className="bg-[hsl(var(--secondary))]" data-testid="offer-price" />
              <Textarea value={newOffer.notes} onChange={(e) => setNewOffer({...newOffer, notes: e.target.value})} placeholder="Notes / Inclusions" className="bg-[hsl(var(--secondary))]" />
              <Button onClick={() => createMutation.mutate(newOffer)} disabled={!newOffer.guest_name || !newOffer.price || createMutation.isPending} className="w-full" data-testid="submit-offer-btn">
                {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Create Offer
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Offers Sent</p>
            <p className="text-2xl font-bold text-blue-400">{sentCount}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Paid Offers</p>
            <p className="text-2xl font-bold text-emerald-400">{paidCount}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Reservations</p>
            <p className="text-2xl font-bold text-purple-400">{reservations.filter(r => r.status === 'CONFIRMED').length}</p>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Conversion Rate</p>
            <p className="text-2xl font-bold text-amber-400">{conversionRate}%</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="offers">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="offers"><Gift className="w-4 h-4 mr-2" /> Offers ({totalOffers})</TabsTrigger>
          <TabsTrigger value="reservations"><CalendarDays className="w-4 h-4 mr-2" /> Reservations ({reservations.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="offers" className="mt-4">
          {/* Status filter */}
          <div className="flex gap-2 mb-4">
            {['', 'DRAFT', 'SENT', 'PAID', 'EXPIRED', 'CANCELLED'].map(s => (
              <Button key={s} size="sm" variant={statusFilter === s ? 'default' : 'outline'}
                onClick={() => setStatusFilter(s)} className="text-xs">
                {s || 'All'}
              </Button>
            ))}
          </div>
          <div className="space-y-3">
            {offers.map(offer => (
              <Card key={offer.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold">{offer.guest_name || 'Guest'}</h3>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        {offer.room_type} | {offer.check_in} to {offer.check_out} | {offer.guests_count || 1} guest(s)
                      </p>
                      {offer.source === 'INBOX' && (
                        <Badge className="bg-indigo-500/10 text-indigo-400 border-indigo-500/25 border text-xs mt-1">From Inbox</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={`${statusColors[offer.status] || ''} border text-xs`}>{offer.status}</Badge>
                      <span className="font-bold">{formatCurrency(offer.price_total || offer.price)} {offer.currency}</span>
                    </div>
                  </div>
                  {offer.notes && <p className="text-sm text-[hsl(var(--muted-foreground))] mb-3">{offer.notes}</p>}
                  {offer.expires_at && offer.status === 'SENT' && (
                    <p className="text-xs text-amber-400 mb-2 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> Expires: {new Date(offer.expires_at).toLocaleString()}
                    </p>
                  )}
                  <div className="flex gap-2 flex-wrap">
                    {offer.status === 'DRAFT' && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => sendMutation.mutate(offer.id)}>
                          <Send className="w-3 h-3 mr-1" /> Send Offer
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => createPaymentLinkMutation.mutate(offer.id)}>
                          <Link2 className="w-3 h-3 mr-1" /> Create Payment Link
                        </Button>
                        <Button size="sm" variant="ghost" className="text-rose-400" onClick={() => cancelMutation.mutate(offer.id)}>
                          <Ban className="w-3 h-3 mr-1" /> Cancel
                        </Button>
                      </>
                    )}
                    {offer.status === 'SENT' && (
                      <>
                        {!offer.payment_link_id && (
                          <Button size="sm" variant="outline" onClick={() => createPaymentLinkMutation.mutate(offer.id)}>
                            <Link2 className="w-3 h-3 mr-1" /> Create Payment Link
                          </Button>
                        )}
                        {offer.payment_link_id && offer.payment_link?.url && (
                          <>
                            <Button size="sm" variant="outline" onClick={() => copyPaymentUrl(offer.payment_link.url)}>
                              <Copy className="w-3 h-3 mr-1" /> Copy Payment URL
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => window.open(offer.payment_link.url, '_blank')}>
                              <ExternalLink className="w-3 h-3 mr-1" /> Open
                            </Button>
                          </>
                        )}
                        {offer.payment_link_id && (
                          <Button size="sm" onClick={() => simulatePaymentMutation.mutate(offer.payment_link_id)} data-testid={`simulate-payment-${offer.id}`}>
                            <CreditCard className="w-3 h-3 mr-1" /> Simulate Payment
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" className="text-rose-400" onClick={() => cancelMutation.mutate(offer.id)}>
                          <Ban className="w-3 h-3 mr-1" /> Cancel
                        </Button>
                      </>
                    )}
                    {offer.status === 'PAID' && (
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
                <p>No offers found. Create your first offer above.</p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="reservations" className="mt-4">
          <div className="flex justify-end mb-3">
            <Button size="sm" variant="outline" onClick={handleExportCSV}>
              <Download className="w-3 h-3 mr-1" /> Export CSV
            </Button>
          </div>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <Table>
              <TableHeader>
                <TableRow className="border-[hsl(var(--border))]">
                  <TableHead>Confirmation</TableHead>
                  <TableHead>Guest</TableHead>
                  <TableHead>Room</TableHead>
                  <TableHead>Check-in</TableHead>
                  <TableHead>Check-out</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reservations.map(res => (
                  <TableRow key={res.id} className="border-[hsl(var(--border))]">
                    <TableCell>
                      <code className="text-xs font-mono bg-[hsl(var(--secondary))] px-2 py-1 rounded">{res.confirmation_code}</code>
                    </TableCell>
                    <TableCell className="font-medium">{res.guest_name}</TableCell>
                    <TableCell className="capitalize">{res.room_type}</TableCell>
                    <TableCell>{res.check_in}</TableCell>
                    <TableCell>{res.check_out}</TableCell>
                    <TableCell>{formatCurrency(res.price_total || res.price)} {res.currency}</TableCell>
                    <TableCell>
                      <Badge className={`${statusColors[res.status] || ''} border text-xs`}>{res.status}</Badge>
                    </TableCell>
                    <TableCell>
                      {res.status === 'CONFIRMED' && (
                        <Button size="sm" variant="ghost" className="text-rose-400"
                          onClick={() => cancelReservationMutation.mutate(res.id)}>
                          <XCircle className="w-3 h-3 mr-1" /> Cancel
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {reservations.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-[hsl(var(--muted-foreground))]">No reservations yet</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
