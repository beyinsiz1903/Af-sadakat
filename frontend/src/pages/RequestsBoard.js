import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { requestsAPI, departmentsAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { statusColors, priorityColors, timeAgo, formatDate } from '../lib/utils';
import { ClipboardList, Clock, User, ArrowRight, AlertTriangle, Star } from 'lucide-react';
import { toast } from 'sonner';

const STATUSES = ['OPEN', 'IN_PROGRESS', 'DONE', 'CLOSED'];

export default function RequestsBoard() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [deptFilter, setDeptFilter] = useState('all');
  const [selectedRequest, setSelectedRequest] = useState(null);

  const { data: depts } = useQuery({
    queryKey: ['departments', tenant?.slug],
    queryFn: () => departmentsAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: requestsData, refetch } = useQuery({
    queryKey: ['requests', tenant?.slug, deptFilter],
    queryFn: () => requestsAPI.list(tenant?.slug, {
      department: deptFilter === 'all' ? undefined : deptFilter,
      limit: 200
    }).then(r => r.data),
    enabled: !!tenant?.slug,
    refetchInterval: 10000,
  });

  const requests = requestsData?.data || [];

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => requestsAPI.update(tenant?.slug, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['requests']);
      toast.success('Request updated');
    },
  });

  // WebSocket listener
  useEffect(() => {
    if (!window.__ws) return;
    const unsub = window.__ws.on('guest_request', () => {
      refetch();
    });
    return unsub;
  }, [refetch]);

  const handleStatusChange = (requestId, newStatus) => {
    updateMutation.mutate({ id: requestId, data: { status: newStatus } });
  };

  const groupedByStatus = STATUSES.reduce((acc, status) => {
    acc[status] = requests.filter(r => r.status === status);
    return acc;
  }, {});

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Guest Requests</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Manage and track all hotel guest requests</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={deptFilter} onValueChange={setDeptFilter}>
            <SelectTrigger className="w-[180px] bg-[hsl(var(--card))]" data-testid="dept-filter">
              <SelectValue placeholder="All Departments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Departments</SelectItem>
              {(depts || []).map(d => (
                <SelectItem key={d.code} value={d.code}>{d.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {STATUSES.map(status => (
          <div key={status} className="space-y-3" data-testid={`requests-board-column-${status.toLowerCase()}`}>
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <Badge className={`${statusColors[status]} border text-xs font-medium`}>{status.replace('_', ' ')}</Badge>
                <span className="text-sm text-[hsl(var(--muted-foreground))]">{groupedByStatus[status]?.length || 0}</span>
              </div>
            </div>
            <ScrollArea className="h-[calc(100vh-260px)]">
              <div className="space-y-3 pr-2">
                {(groupedByStatus[status] || []).map(req => (
                  <Card
                    key={req.id}
                    className="bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all cursor-pointer hover:translate-y-[-1px] hover:shadow-lg"
                    onClick={() => setSelectedRequest(req)}
                    data-testid={`request-card-${req.id}`}
                  >
                    <CardContent className="p-4 space-y-3">
                      <div className="flex items-start justify-between">
                        <Badge className={`${priorityColors[req.priority]} text-xs`}>{req.priority}</Badge>
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">{timeAgo(req.created_at)}</span>
                      </div>
                      <p className="text-sm font-medium line-clamp-2">{req.description}</p>
                      <div className="flex items-center gap-3 text-xs text-[hsl(var(--muted-foreground))]">
                        <span className="flex items-center gap-1"><ClipboardList className="w-3 h-3" /> {req.room_number}</span>
                        <span className="capitalize">{req.category?.replace('_', ' ')}</span>
                      </div>
                      {req.guest_name && (
                        <div className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
                          <User className="w-3 h-3" /> {req.guest_name}
                        </div>
                      )}
                      {req.rating && (
                        <div className="flex items-center gap-1">
                          {[...Array(5)].map((_, i) => (
                            <Star key={i} className={`w-3 h-3 ${i < req.rating ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />
                          ))}
                        </div>
                      )}
                      {/* Quick status action */}
                      {status !== 'CLOSED' && (
                        <div className="pt-2 border-t border-[hsl(var(--border))]">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="w-full text-xs h-8"
                            onClick={(e) => {
                              e.stopPropagation();
                              const nextStatus = STATUSES[STATUSES.indexOf(status) + 1];
                              if (nextStatus) handleStatusChange(req.id, nextStatus);
                            }}
                            data-testid={`request-advance-${req.id}`}
                          >
                            <ArrowRight className="w-3 h-3 mr-1" />
                            Move to {STATUSES[STATUSES.indexOf(status) + 1]?.replace('_', ' ')}
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
                {(groupedByStatus[status] || []).length === 0 && (
                  <div className="text-center py-8 text-sm text-[hsl(var(--muted-foreground))]">
                    No requests
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        ))}
      </div>

      {/* Request Detail Dialog */}
      <Dialog open={!!selectedRequest} onOpenChange={(open) => !open && setSelectedRequest(null)}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-lg">
          {selectedRequest && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  <Badge className={`${statusColors[selectedRequest.status]} border`}>{selectedRequest.status.replace('_', ' ')}</Badge>
                  Room {selectedRequest.room_number}
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium mb-1">Description</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">{selectedRequest.description}</p>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-[hsl(var(--muted-foreground))] text-xs">Category</p>
                    <p className="capitalize">{selectedRequest.category?.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <p className="text-[hsl(var(--muted-foreground))] text-xs">Department</p>
                    <p>{selectedRequest.department_code}</p>
                  </div>
                  <div>
                    <p className="text-[hsl(var(--muted-foreground))] text-xs">Guest</p>
                    <p>{selectedRequest.guest_name || 'Anonymous'}</p>
                  </div>
                  <div>
                    <p className="text-[hsl(var(--muted-foreground))] text-xs">Priority</p>
                    <Badge className={`${priorityColors[selectedRequest.priority]} text-xs`}>{selectedRequest.priority}</Badge>
                  </div>
                  <div>
                    <p className="text-[hsl(var(--muted-foreground))] text-xs">Created</p>
                    <p>{formatDate(selectedRequest.created_at)}</p>
                  </div>
                  {selectedRequest.first_response_at && (
                    <div>
                      <p className="text-[hsl(var(--muted-foreground))] text-xs">First Response</p>
                      <p>{formatDate(selectedRequest.first_response_at)}</p>
                    </div>
                  )}
                </div>
                {selectedRequest.notes && (
                  <div>
                    <p className="text-sm font-medium mb-1">Notes</p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">{selectedRequest.notes}</p>
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  {STATUSES.filter(s => s !== selectedRequest.status).map(s => (
                    <Button
                      key={s}
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        handleStatusChange(selectedRequest.id, s);
                        setSelectedRequest(null);
                      }}
                    >
                      {s.replace('_', ' ')}
                    </Button>
                  ))}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
