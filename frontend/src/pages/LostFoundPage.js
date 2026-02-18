import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { lostFoundAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Search, Package, CheckCircle2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const statusColors = {
  stored: 'bg-blue-500/20 text-blue-400',
  returned: 'bg-emerald-500/20 text-emerald-400',
  claimed: 'bg-amber-500/20 text-amber-400',
  disposed: 'bg-gray-500/20 text-gray-400',
};

export default function LostFoundPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [showDialog, setShowDialog] = useState(false);
  const [filter, setFilter] = useState('all');
  const [form, setForm] = useState({ description: '', category: 'other', location_found: '', room_number: '', storage_location: '', notes: '' });

  const { data: result, isLoading } = useQuery({
    queryKey: ['lost-found', tenant?.slug, filter],
    queryFn: () => lostFoundAPI.list(tenant?.slug, filter !== 'all' ? { status: filter } : {}).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: stats } = useQuery({
    queryKey: ['lost-found-stats', tenant?.slug],
    queryFn: () => lostFoundAPI.getStats(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const items = result?.data || [];

  const createItem = useMutation({
    mutationFn: (data) => lostFoundAPI.create(tenant?.slug, data),
    onSuccess: () => { queryClient.invalidateQueries(['lost-found']); queryClient.invalidateQueries(['lost-found-stats']); setShowDialog(false); toast.success('Item recorded'); },
  });

  const updateItem = useMutation({
    mutationFn: ({ id, data }) => lostFoundAPI.update(tenant?.slug, id, data),
    onSuccess: () => { queryClient.invalidateQueries(['lost-found']); queryClient.invalidateQueries(['lost-found-stats']); toast.success('Updated'); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Lost & Found</h1>
        <Button onClick={() => setShowDialog(true)}>+ Record Item</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {stats && [
          { label: 'Stored', value: stats.stored, color: 'text-blue-400' },
          { label: 'Returned', value: stats.returned, color: 'text-emerald-400' },
          { label: 'Claimed', value: stats.claimed, color: 'text-amber-400' },
          { label: 'Disposed', value: stats.disposed, color: 'text-gray-400' },
        ].map((s, i) => (
          <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4 text-center">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {['all', 'stored', 'returned', 'claimed', 'disposed'].map(f => (
          <Button key={f} size="sm" variant={filter === f ? 'default' : 'outline'} onClick={() => setFilter(f)}>
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </Button>
        ))}
      </div>

      {/* Items */}
      <div className="space-y-3">
        {items.map(item => (
          <Card key={item.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <Package className="w-5 h-5 text-[hsl(var(--primary))] mt-0.5" />
                  <div>
                    <p className="font-medium text-sm">{item.description}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {item.category} • {item.location_found} {item.room_number && `• Room ${item.room_number}`}
                    </p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      Found: {item.found_date} by {item.found_by}
                      {item.storage_location && ` • Stored: ${item.storage_location}`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={statusColors[item.status]}>{item.status}</Badge>
                  {item.status === 'stored' && (
                    <Select onValueChange={(v) => updateItem.mutate({ id: item.id, data: { status: v } })}>
                      <SelectTrigger className="h-7 w-28 text-xs"><SelectValue placeholder="Action" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="returned">Mark Returned</SelectItem>
                        <SelectItem value="claimed">Mark Claimed</SelectItem>
                        <SelectItem value="disposed">Dispose</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <DialogHeader><DialogTitle>Record Lost & Found Item</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Textarea value={form.description} onChange={(e) => setForm({...form, description: e.target.value})} placeholder="Item description" />
            <Select value={form.category} onValueChange={(v) => setForm({...form, category: v})}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="electronics">Electronics</SelectItem>
                <SelectItem value="clothing">Clothing</SelectItem>
                <SelectItem value="documents">Documents</SelectItem>
                <SelectItem value="jewelry">Jewelry</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
            <div className="grid grid-cols-2 gap-2">
              <Input value={form.location_found} onChange={(e) => setForm({...form, location_found: e.target.value})} placeholder="Location found" />
              <Input value={form.room_number} onChange={(e) => setForm({...form, room_number: e.target.value})} placeholder="Room number" />
            </div>
            <Input value={form.storage_location} onChange={(e) => setForm({...form, storage_location: e.target.value})} placeholder="Storage location" />
            <Button className="w-full" onClick={() => createItem.mutate({ ...form, item_type: 'found' })} disabled={!form.description}>Record Item</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
