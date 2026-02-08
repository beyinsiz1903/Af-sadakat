import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { propertiesAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Building2, Plus, MapPin, Phone, Mail, CheckCircle2, XCircle, Pencil } from 'lucide-react';
import { toast } from 'sonner';

export default function PropertiesPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editProperty, setEditProperty] = useState(null);
  const [form, setForm] = useState({ name: '', slug: '', address: '', phone: '', email: '', timezone: 'Europe/Istanbul' });

  const { data: properties = [] } = useQuery({
    queryKey: ['properties', tenant?.slug],
    queryFn: () => propertiesAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const createMutation = useMutation({
    mutationFn: (data) => propertiesAPI.create(tenant?.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['properties']);
      toast.success('Property created');
      setCreateOpen(false);
      setForm({ name: '', slug: '', address: '', phone: '', email: '', timezone: 'Europe/Istanbul' });
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to create'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => propertiesAPI.update(tenant?.slug, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['properties']);
      toast.success('Property updated');
      setEditOpen(false);
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to update'),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }) => active
      ? propertiesAPI.activate(tenant?.slug, id)
      : propertiesAPI.deactivate(tenant?.slug, id),
    onSuccess: () => {
      queryClient.invalidateQueries(['properties']);
      toast.success('Property status updated');
    },
  });

  const handleEdit = (prop) => {
    setEditProperty(prop);
    setForm({ name: prop.name, slug: prop.slug, address: prop.address || '', phone: prop.phone || '', email: prop.email || '', timezone: prop.timezone || 'Europe/Istanbul' });
    setEditOpen(true);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Properties</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Manage your hotel properties ({properties.length} total)
          </p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button data-testid="create-property-btn"><Plus className="w-4 h-4 mr-2" /> Add Property</Button>
          </DialogTrigger>
          <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-lg">
            <DialogHeader><DialogTitle>Add Property</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} placeholder="Property Name" className="bg-[hsl(var(--secondary))]" />
              <Input value={form.slug} onChange={(e) => setForm({...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-')})} placeholder="Slug (e.g. main-building)" className="bg-[hsl(var(--secondary))]" />
              <Input value={form.address} onChange={(e) => setForm({...form, address: e.target.value})} placeholder="Address" className="bg-[hsl(var(--secondary))]" />
              <div className="grid grid-cols-2 gap-3">
                <Input value={form.phone} onChange={(e) => setForm({...form, phone: e.target.value})} placeholder="Phone" className="bg-[hsl(var(--secondary))]" />
                <Input value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} placeholder="Email" className="bg-[hsl(var(--secondary))]" />
              </div>
              <Button onClick={() => createMutation.mutate(form)} disabled={!form.name || !form.slug || createMutation.isPending} className="w-full">
                {createMutation.isPending ? 'Creating...' : 'Create Property'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-lg">
          <DialogHeader><DialogTitle>Edit Property</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} placeholder="Property Name" className="bg-[hsl(var(--secondary))]" />
            <Input value={form.address} onChange={(e) => setForm({...form, address: e.target.value})} placeholder="Address" className="bg-[hsl(var(--secondary))]" />
            <div className="grid grid-cols-2 gap-3">
              <Input value={form.phone} onChange={(e) => setForm({...form, phone: e.target.value})} placeholder="Phone" className="bg-[hsl(var(--secondary))]" />
              <Input value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} placeholder="Email" className="bg-[hsl(var(--secondary))]" />
            </div>
            <Button onClick={() => updateMutation.mutate({ id: editProperty?.id, data: form })} disabled={updateMutation.isPending} className="w-full">
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <Table>
          <TableHeader>
            <TableRow className="border-[hsl(var(--border))]">
              <TableHead>Property</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Address</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {properties.map(prop => (
              <TableRow key={prop.id} className="border-[hsl(var(--border))]">
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-[hsl(var(--primary))]" />
                    <span className="font-medium">{prop.name}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <code className="text-xs bg-[hsl(var(--secondary))] px-2 py-1 rounded">{prop.slug}</code>
                </TableCell>
                <TableCell>
                  {prop.address && (
                    <div className="flex items-center gap-1 text-sm text-[hsl(var(--muted-foreground))]">
                      <MapPin className="w-3 h-3" /> {prop.address}
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  <div className="space-y-1 text-xs text-[hsl(var(--muted-foreground))]">
                    {prop.phone && <div className="flex items-center gap-1"><Phone className="w-3 h-3" /> {prop.phone}</div>}
                    {prop.email && <div className="flex items-center gap-1"><Mail className="w-3 h-3" /> {prop.email}</div>}
                  </div>
                </TableCell>
                <TableCell>
                  {prop.is_active ? (
                    <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/25 border text-xs">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Active
                    </Badge>
                  ) : (
                    <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/25 border text-xs">
                      <XCircle className="w-3 h-3 mr-1" /> Inactive
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button size="sm" variant="ghost" onClick={() => handleEdit(prop)}>
                      <Pencil className="w-3 h-3" />
                    </Button>
                    <Button size="sm" variant="ghost"
                      onClick={() => toggleActiveMutation.mutate({ id: prop.id, active: !prop.is_active })}>
                      {prop.is_active ? <XCircle className="w-3 h-3 text-rose-400" /> : <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {properties.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-[hsl(var(--muted-foreground))]">
                  <Building2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No properties yet. Add your first property above.</p>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
