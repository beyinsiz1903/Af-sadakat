import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { notificationsAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Bell, BellOff, Check, CheckCheck, Loader2, Sparkles, UtensilsCrossed, Wrench, MessageCircle, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { timeAgo } from '../lib/utils';

const typeIcons = {
  NEW_ROOM_SERVICE_ORDER: UtensilsCrossed,
  NEW_SPA_BOOKING: Sparkles,
  NEW_TRANSPORT_REQUEST: MessageCircle,
  NEW_LAUNDRY_REQUEST: Sparkles,
  SLA_BREACH: AlertTriangle,
  CUSTOM: Bell,
};

export default function NotificationCenterPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('all');

  const { data: result, isLoading } = useQuery({
    queryKey: ['notifications', tenant?.slug, filter],
    queryFn: () => notificationsAPI.list(tenant?.slug, filter === 'unread' ? { unread_only: true } : {}).then(r => r.data),
    enabled: !!tenant?.slug,
    refetchInterval: 10000,
  });

  const notifications = result?.data || [];
  const unreadCount = result?.unread_count || 0;

  const markRead = useMutation({
    mutationFn: (id) => notificationsAPI.markRead(tenant?.slug, id),
    onSuccess: () => queryClient.invalidateQueries(['notifications']),
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationsAPI.markAllRead(tenant?.slug),
    onSuccess: () => { queryClient.invalidateQueries(['notifications']); toast.success('All marked as read'); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">Notifications</h1>
          {unreadCount > 0 && <Badge className="bg-red-500 text-white">{unreadCount} unread</Badge>}
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant={filter === 'all' ? 'default' : 'outline'} onClick={() => setFilter('all')}>All</Button>
          <Button size="sm" variant={filter === 'unread' ? 'default' : 'outline'} onClick={() => setFilter('unread')}>Unread</Button>
          {unreadCount > 0 && <Button size="sm" variant="outline" onClick={() => markAllRead.mutate()}><CheckCheck className="w-4 h-4 mr-1" />Mark All Read</Button>}
        </div>
      </div>

      {isLoading ? <Loader2 className="w-6 h-6 animate-spin" /> :
        <div className="space-y-2">
          {notifications.map(notif => {
            const Icon = typeIcons[notif.type] || Bell;
            return (
              <Card key={notif.id} className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] ${!notif.read ? 'border-l-2 border-l-[hsl(var(--primary))]' : ''}`}>
                <CardContent className="p-3 flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${!notif.read ? 'bg-[hsl(var(--primary)/0.1)]' : 'bg-[hsl(var(--secondary))]'}`}>
                    <Icon className={`w-4 h-4 ${!notif.read ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--muted-foreground))]'}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${!notif.read ? 'font-semibold' : ''}`}>{notif.title}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{notif.body}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{timeAgo(notif.created_at)}</span>
                      {notif.department_code && <Badge variant="outline" className="text-[9px]">{notif.department_code}</Badge>}
                      {notif.priority === 'urgent' && <Badge className="bg-red-500/20 text-red-400 text-[9px]">Urgent</Badge>}
                    </div>
                  </div>
                  {!notif.read && (
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => markRead.mutate(notif.id)}>
                      <Check className="w-4 h-4" />
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
          {notifications.length === 0 && (
            <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
              <BellOff className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No notifications</p>
            </div>
          )}
        </div>
      }
    </div>
  );
}
