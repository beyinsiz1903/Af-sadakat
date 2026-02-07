import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { tablesAPI } from '../lib/api';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Plus, Trash2, Copy } from 'lucide-react';
import { toast } from 'sonner';

export default function TablesPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [newTable, setNewTable] = useState({ table_number: '', capacity: 4, section: '' });
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: tables = [] } = useQuery({
    queryKey: ['tables', tenant?.slug],
    queryFn: () => tablesAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const createMutation = useMutation({
    mutationFn: (data) => tablesAPI.create(tenant?.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['tables']);
      toast.success('Table created');
      setNewTable({ table_number: '', capacity: 4, section: '' });
      setDialogOpen(false);
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => tablesAPI.delete(tenant?.slug, id),
    onSuccess: () => {
      queryClient.invalidateQueries(['tables']);
      toast.success('Table deleted');
    },
  });

  const copyQrLink = (table) => {
    const url = `${window.location.origin}${table.qr_link}`;
    navigator.clipboard.writeText(url);
    toast.success('QR link copied!');
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tables</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{tables.length} tables configured</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-table-btn"><Plus className="w-4 h-4 mr-2" /> Add Table</Button>
          </DialogTrigger>
          <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <DialogHeader><DialogTitle>Add New Table</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Table Number</label>
                <Input value={newTable.table_number} onChange={(e) => setNewTable({...newTable, table_number: e.target.value})} placeholder="1" className="bg-[hsl(var(--secondary))]" data-testid="table-number-input" />
              </div>
              <div>
                <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Capacity</label>
                <Input type="number" value={newTable.capacity} onChange={(e) => setNewTable({...newTable, capacity: parseInt(e.target.value) || 4})} className="bg-[hsl(var(--secondary))]" />
              </div>
              <div>
                <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Section</label>
                <Input value={newTable.section} onChange={(e) => setNewTable({...newTable, section: e.target.value})} placeholder="terrace" className="bg-[hsl(var(--secondary))]" />
              </div>
              <Button onClick={() => createMutation.mutate(newTable)} disabled={!newTable.table_number} className="w-full" data-testid="create-table-btn">
                Create Table
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <Table>
          <TableHeader>
            <TableRow className="border-[hsl(var(--border))]">
              <TableHead>Table</TableHead>
              <TableHead>Code</TableHead>
              <TableHead>Capacity</TableHead>
              <TableHead>Section</TableHead>
              <TableHead>QR Link</TableHead>
              <TableHead className="w-[80px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tables.map(table => (
              <TableRow key={table.id} className="border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))]">
                <TableCell className="font-medium">{table.table_number}</TableCell>
                <TableCell><code className="text-xs bg-[hsl(var(--secondary))] px-2 py-1 rounded">{table.table_code}</code></TableCell>
                <TableCell>{table.capacity}</TableCell>
                <TableCell className="capitalize">{table.section}</TableCell>
                <TableCell>
                  <Button variant="ghost" size="sm" className="text-xs h-7" onClick={() => copyQrLink(table)}>
                    <Copy className="w-3 h-3 mr-1" /> Copy Link
                  </Button>
                </TableCell>
                <TableCell>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-[hsl(var(--destructive))]" onClick={() => deleteMutation.mutate(table.id)}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {tables.length === 0 && (
              <TableRow><TableCell colSpan={6} className="text-center py-8 text-[hsl(var(--muted-foreground))]">No tables yet.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
