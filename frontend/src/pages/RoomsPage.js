import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { roomsAPI, departmentsAPI, serviceCategoriesAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { BedDouble, Plus, Trash2, QrCode, Copy, Download, FileText } from 'lucide-react';
import { toast } from 'sonner';

export default function RoomsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [newRoom, setNewRoom] = useState({ room_number: '', room_type: 'standard', floor: '' });
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: rooms = [] } = useQuery({
    queryKey: ['rooms', tenant?.slug],
    queryFn: () => roomsAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const createMutation = useMutation({
    mutationFn: (data) => roomsAPI.create(tenant?.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['rooms']);
      toast.success('Room created');
      setNewRoom({ room_number: '', room_type: 'standard', floor: '' });
      setDialogOpen(false);
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => roomsAPI.delete(tenant?.slug, id),
    onSuccess: () => {
      queryClient.invalidateQueries(['rooms']);
      toast.success('Room deleted');
    },
  });

  const copyQrLink = (room) => {
    const url = `${window.location.origin}${room.qr_link}`;
    navigator.clipboard.writeText(url);
    toast.success('QR link copied!');
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Rooms</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{rooms.length} rooms configured</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-room-btn"><Plus className="w-4 h-4 mr-2" /> Add Room</Button>
          </DialogTrigger>
          <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <DialogHeader><DialogTitle>Add New Room</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Room Number</label>
                <Input value={newRoom.room_number} onChange={(e) => setNewRoom({...newRoom, room_number: e.target.value})} placeholder="101" className="bg-[hsl(var(--secondary))]" data-testid="room-number-input" />
              </div>
              <div>
                <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Type</label>
                <Select value={newRoom.room_type} onValueChange={(v) => setNewRoom({...newRoom, room_type: v})}>
                  <SelectTrigger className="bg-[hsl(var(--secondary))]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">Standard</SelectItem>
                    <SelectItem value="deluxe">Deluxe</SelectItem>
                    <SelectItem value="suite">Suite</SelectItem>
                    <SelectItem value="penthouse">Penthouse</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Floor</label>
                <Input value={newRoom.floor} onChange={(e) => setNewRoom({...newRoom, floor: e.target.value})} placeholder="1" className="bg-[hsl(var(--secondary))]" />
              </div>
              <Button onClick={() => createMutation.mutate(newRoom)} disabled={!newRoom.room_number} className="w-full" data-testid="create-room-btn">
                Create Room
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <Table>
          <TableHeader>
            <TableRow className="border-[hsl(var(--border))]">
              <TableHead>Room</TableHead>
              <TableHead>Code</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Floor</TableHead>
              <TableHead>QR Link</TableHead>
              <TableHead className="w-[80px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rooms.map(room => (
              <TableRow key={room.id} className="border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))]">
                <TableCell className="font-medium">{room.room_number}</TableCell>
                <TableCell><code className="text-xs bg-[hsl(var(--secondary))] px-2 py-1 rounded">{room.room_code}</code></TableCell>
                <TableCell className="capitalize">{room.room_type}</TableCell>
                <TableCell>{room.floor}</TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" className="text-xs h-7" onClick={() => copyQrLink(room)} data-testid={`copy-qr-${room.room_code}`}>
                      <Copy className="w-3 h-3 mr-1" /> Copy
                    </Button>
                    <Button variant="ghost" size="sm" className="text-xs h-7" onClick={() => {
                      const url = `${process.env.REACT_APP_BACKEND_URL}/api/admin/rooms/${room.id}/qr.png`;
                      window.open(url, '_blank');
                    }} data-testid={`download-qr-${room.room_code}`}>
                      <Download className="w-3 h-3 mr-1" /> QR
                    </Button>
                  </div>
                </TableCell>
                <TableCell>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-[hsl(var(--destructive))]" onClick={() => deleteMutation.mutate(room.id)}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {rooms.length === 0 && (
              <TableRow><TableCell colSpan={6} className="text-center py-8 text-[hsl(var(--muted-foreground))]">No rooms yet. Add your first room above.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
