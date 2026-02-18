import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { housekeepingAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Sparkles, CheckCircle2, Clock, AlertTriangle, Wrench, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const statusColors = {
  clean: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  dirty: 'bg-red-500/20 text-red-400 border-red-500/30',
  in_progress: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  inspecting: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  maintenance: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  unknown: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

export default function HousekeepingPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('board');
  const [showChecklistDialog, setShowChecklistDialog] = useState(false);
  const [newChecklist, setNewChecklist] = useState({ name: '', room_type: 'all', items: '' });

  const { data: roomStatus = [], isLoading } = useQuery({
    queryKey: ['hk-rooms', tenant?.slug],
    queryFn: () => housekeepingAPI.getRoomStatus(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: stats } = useQuery({
    queryKey: ['hk-stats', tenant?.slug],
    queryFn: () => housekeepingAPI.getStats(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: checklists = [] } = useQuery({
    queryKey: ['hk-checklists', tenant?.slug],
    queryFn: () => housekeepingAPI.listChecklists(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const updateStatus = useMutation({
    mutationFn: ({ roomId, data }) => housekeepingAPI.updateRoomHKStatus(tenant?.slug, roomId, data),
    onSuccess: () => { queryClient.invalidateQueries(['hk-rooms']); queryClient.invalidateQueries(['hk-stats']); toast.success('Status updated'); },
  });

  const createChecklist = useMutation({
    mutationFn: (data) => housekeepingAPI.createChecklist(tenant?.slug, data),
    onSuccess: () => { queryClient.invalidateQueries(['hk-checklists']); setShowChecklistDialog(false); toast.success('Checklist created'); },
  });

  const kpis = stats ? [
    { label: 'Clean', value: stats.clean, color: 'text-emerald-400', icon: CheckCircle2 },
    { label: 'Dirty', value: stats.dirty, color: 'text-red-400', icon: AlertTriangle },
    { label: 'In Progress', value: stats.in_progress, color: 'text-blue-400', icon: Clock },
    { label: 'Maintenance', value: stats.maintenance, color: 'text-purple-400', icon: Wrench },
    { label: 'Tasks Today', value: `${stats.tasks_completed}/${stats.tasks_today}`, color: 'text-amber-400', icon: Sparkles },
  ] : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Housekeeping</h1>
        <div className="flex gap-2">
          <Button variant={tab === 'board' ? 'default' : 'outline'} size="sm" onClick={() => setTab('board')}>Room Board</Button>
          <Button variant={tab === 'checklists' ? 'default' : 'outline'} size="sm" onClick={() => setTab('checklists')}>Checklists</Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-5 gap-3">
        {kpis.map((kpi, i) => {
          const Icon = kpi.icon;
          return (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4 text-center">
                <Icon className={`w-5 h-5 mx-auto mb-1 ${kpi.color}`} />
                <p className="text-2xl font-bold">{kpi.value}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">{kpi.label}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {tab === 'board' && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {isLoading ? <Loader2 className="w-6 h-6 animate-spin" /> :
            roomStatus.map(room => {
              const hk = room.hk_status || {};
              const st = hk.cleaning_status || 'unknown';
              return (
                <Card key={room.id} className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all`}>
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-sm">#{room.room_number}</span>
                      <Badge className={`${statusColors[st]} text-[10px]`}>{st}</Badge>
                    </div>
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))] mb-2">{room.room_type} • {room.floor || '-'}</p>
                    <Select value={st} onValueChange={(v) => updateStatus.mutate({ roomId: room.id, data: { cleaning_status: v } })}>
                      <SelectTrigger className="h-7 text-[10px]"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="clean">Clean</SelectItem>
                        <SelectItem value="dirty">Dirty</SelectItem>
                        <SelectItem value="in_progress">In Progress</SelectItem>
                        <SelectItem value="inspecting">Inspecting</SelectItem>
                        <SelectItem value="maintenance">Maintenance</SelectItem>
                      </SelectContent>
                    </Select>
                  </CardContent>
                </Card>
              );
            })
          }
        </div>
      )}

      {tab === 'checklists' && (
        <div className="space-y-4">
          <Button onClick={() => setShowChecklistDialog(true)}>+ New Checklist</Button>
          {checklists.map(cl => (
            <Card key={cl.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{cl.name}</h3>
                  <Badge variant="outline">{cl.room_type}</Badge>
                </div>
                <div className="space-y-1">
                  {(cl.items || []).map((item, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <div className={`w-4 h-4 rounded border ${item.required ? 'border-[hsl(var(--primary))]' : 'border-[hsl(var(--border))]'} flex items-center justify-center`}>
                        {item.required && <CheckCircle2 className="w-3 h-3 text-[hsl(var(--primary))]" />}
                      </div>
                      <span>{item.text}</span>
                      {item.required && <Badge className="text-[9px]" variant="outline">Required</Badge>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showChecklistDialog} onOpenChange={setShowChecklistDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <DialogHeader><DialogTitle>New Checklist</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input value={newChecklist.name} onChange={(e) => setNewChecklist({...newChecklist, name: e.target.value})} placeholder="Checklist name" />
            <Select value={newChecklist.room_type} onValueChange={(v) => setNewChecklist({...newChecklist, room_type: v})}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Room Types</SelectItem>
                <SelectItem value="standard">Standard</SelectItem>
                <SelectItem value="deluxe">Deluxe</SelectItem>
                <SelectItem value="suite">Suite</SelectItem>
              </SelectContent>
            </Select>
            <Textarea value={newChecklist.items} onChange={(e) => setNewChecklist({...newChecklist, items: e.target.value})} placeholder="One item per line" rows={6} />
            <Button onClick={() => createChecklist.mutate({
              name: newChecklist.name, room_type: newChecklist.room_type,
              items: newChecklist.items.split('\n').filter(l => l.trim()).map(l => ({ text: l.trim(), required: true }))
            })}>Create</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
