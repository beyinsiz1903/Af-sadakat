import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { requestsAPI, departmentsAPI } from '../lib/api';
import api from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { statusColors, priorityColors, timeAgo, formatDate } from '../lib/utils';
import { ClipboardList, Clock, User, AlertTriangle, Star, MessageSquare, Send } from 'lucide-react';
import { toast } from 'sonner';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const STATUSES = ['OPEN', 'IN_PROGRESS', 'DONE', 'CLOSED'];

function SortableRequestCard({ req, onClick }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: req.id,
    data: { status: req.status },
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        className="bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all cursor-grab active:cursor-grabbing"
        onClick={onClick}
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
        </CardContent>
      </Card>
    </div>
  );
}

function DroppableColumn({ status, items, onCardClick }) {
  return (
    <SortableContext items={items.map(i => i.id)} strategy={verticalListSortingStrategy}>
      <div className="space-y-3 min-h-[200px]" data-testid={`requests-board-column-${status.toLowerCase()}`}>
        {items.map(req => (
          <SortableRequestCard key={req.id} req={req} onClick={() => onCardClick(req)} />
        ))}
        {items.length === 0 && (
          <div className="text-center py-8 text-sm text-[hsl(var(--muted-foreground))] border-2 border-dashed border-[hsl(var(--border))] rounded-lg">
            Drop here
          </div>
        )}
      </div>
    </SortableContext>
  );
}

export default function RequestsBoard() {
  const tenant = useAuthStore((s) => s.tenant);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [deptFilter, setDeptFilter] = useState('all');
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [commentText, setCommentText] = useState('');
  const [activeId, setActiveId] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

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

  // Comments
  const { data: comments = [], refetch: refetchComments } = useQuery({
    queryKey: ['request-comments', tenant?.slug, selectedRequest?.id],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/requests/${selectedRequest?.id}/comments`).then(r => r.data),
    enabled: !!selectedRequest?.id && !!tenant?.slug,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => requestsAPI.update(tenant?.slug, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['requests']);
      toast.success('Request updated');
    },
  });

  const commentMutation = useMutation({
    mutationFn: ({ requestId, body }) => api.post(`/tenants/${tenant?.slug}/requests/${requestId}/comments`, {
      body, user_id: user?.id, user_name: user?.name
    }),
    onSuccess: () => {
      refetchComments();
      setCommentText('');
      toast.success('Comment added');
    },
  });

  // WebSocket listener
  useEffect(() => {
    if (!window.__ws) return;
    const unsub = window.__ws.on('guest_request', () => refetch());
    return unsub;
  }, [refetch]);

  const groupedByStatus = STATUSES.reduce((acc, status) => {
    acc[status] = requests.filter(r => r.status === status);
    return acc;
  }, {});

  // DnD handlers
  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    setActiveId(null);
    
    if (!over) return;
    
    const draggedReq = requests.find(r => r.id === active.id);
    if (!draggedReq) return;
    
    // Determine target status from drop zone
    const overId = over.id;
    const overReq = requests.find(r => r.id === overId);
    
    let targetStatus = null;
    if (overReq) {
      targetStatus = overReq.status;
    } else {
      // Dropped on empty column - check container
      for (const status of STATUSES) {
        if (groupedByStatus[status]?.some(r => r.id === overId)) {
          targetStatus = status;
          break;
        }
      }
    }
    
    if (targetStatus && targetStatus !== draggedReq.status) {
      updateMutation.mutate({ id: draggedReq.id, data: { status: targetStatus } });
    }
  };

  const handleDragOver = (event) => {
    const { active, over } = event;
    if (!over || !active) return;
    
    const activeReq = requests.find(r => r.id === active.id);
    if (!activeReq) return;
  };

  const activeReq = activeId ? requests.find(r => r.id === activeId) : null;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Guest Requests</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Drag cards between columns to update status</p>
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

      {/* Kanban Board with DnD */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragOver={handleDragOver}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {STATUSES.map(status => (
            <div key={status} className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <Badge className={`${statusColors[status]} border text-xs font-medium`}>{status.replace('_', ' ')}</Badge>
                  <span className="text-sm text-[hsl(var(--muted-foreground))]">{groupedByStatus[status]?.length || 0}</span>
                </div>
              </div>
              <ScrollArea className="h-[calc(100vh-260px)]">
                <DroppableColumn
                  status={status}
                  items={groupedByStatus[status] || []}
                  onCardClick={(req) => setSelectedRequest(req)}
                />
              </ScrollArea>
            </div>
          ))}
        </div>

        <DragOverlay>
          {activeReq ? (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--primary))] shadow-2xl w-[280px] opacity-90">
              <CardContent className="p-4">
                <Badge className={`${priorityColors[activeReq.priority]} text-xs`}>{activeReq.priority}</Badge>
                <p className="text-sm font-medium mt-2 line-clamp-2">{activeReq.description}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Room {activeReq.room_number}</p>
              </CardContent>
            </Card>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Request Detail Dialog with Comments */}
      <Dialog open={!!selectedRequest} onOpenChange={(open) => !open && setSelectedRequest(null)}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-lg max-h-[80vh] overflow-y-auto">
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
                </div>

                {/* Status Actions */}
                <div className="flex gap-2 flex-wrap">
                  {STATUSES.filter(s => s !== selectedRequest.status).map(s => (
                    <Button
                      key={s}
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        updateMutation.mutate({ id: selectedRequest.id, data: { status: s } });
                        setSelectedRequest(null);
                      }}
                    >
                      {s.replace('_', ' ')}
                    </Button>
                  ))}
                </div>

                {/* Comments Section */}
                <div className="border-t border-[hsl(var(--border))] pt-4">
                  <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" /> Comments ({comments.length})
                  </h4>
                  <div className="space-y-3 mb-3 max-h-[200px] overflow-y-auto">
                    {comments.map(c => (
                      <div key={c.id} className="bg-[hsl(var(--secondary))] rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium">{c.created_by_name || 'Staff'}</span>
                          <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{timeAgo(c.created_at)}</span>
                        </div>
                        <p className="text-sm">{c.body}</p>
                      </div>
                    ))}
                    {comments.length === 0 && (
                      <p className="text-xs text-[hsl(var(--muted-foreground))] text-center py-2">No comments yet</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      value={commentText}
                      onChange={(e) => setCommentText(e.target.value)}
                      placeholder="Add a comment..."
                      className="bg-[hsl(var(--secondary))] text-sm"
                      onKeyDown={(e) => e.key === 'Enter' && commentText.trim() && commentMutation.mutate({ requestId: selectedRequest.id, body: commentText })}
                      data-testid="comment-input"
                    />
                    <Button
                      size="sm"
                      onClick={() => commentText.trim() && commentMutation.mutate({ requestId: selectedRequest.id, body: commentText })}
                      disabled={!commentText.trim()}
                      data-testid="send-comment-btn"
                    >
                      <Send className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
