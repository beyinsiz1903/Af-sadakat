import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Shield, User, Clock, ChevronRight } from 'lucide-react';
import { formatDate, timeAgo } from '../lib/utils';

const actionColors = {
  'room_created': 'bg-emerald-500/10 text-emerald-400',
  'room_deleted': 'bg-rose-500/10 text-rose-400',
  'room_qr_regenerated': 'bg-amber-500/10 text-amber-400',
  'table_created': 'bg-emerald-500/10 text-emerald-400',
  'table_deleted': 'bg-rose-500/10 text-rose-400',
  'table_qr_regenerated': 'bg-amber-500/10 text-amber-400',
  'order_status_changed': 'bg-blue-500/10 text-blue-400',
  'offer_created': 'bg-purple-500/10 text-purple-400',
  'plan_upgraded': 'bg-amber-500/10 text-amber-400',
  'menu_item_created': 'bg-emerald-500/10 text-emerald-400',
  'menu_category_created': 'bg-emerald-500/10 text-emerald-400',
  'data_export': 'bg-blue-500/10 text-blue-400',
  'data_forget': 'bg-rose-500/10 text-rose-400',
  'logout': 'bg-gray-500/10 text-gray-400',
  // Sprint 3
  'conversation_assigned': 'bg-blue-500/10 text-blue-400',
  'conversation_closed': 'bg-gray-500/10 text-gray-400',
  'conversation_reopened': 'bg-emerald-500/10 text-emerald-400',
  'agent_message_sent': 'bg-indigo-500/10 text-indigo-400',
  'ai_suggestion_generated': 'bg-purple-500/10 text-purple-400',
  'connectors_pull_now': 'bg-blue-500/10 text-blue-400',
  'review_reply_created': 'bg-emerald-500/10 text-emerald-400',
  // Sprint 4
  'CRM_CONTACT_CREATED': 'bg-emerald-500/10 text-emerald-400',
  'CRM_CONTACT_UPDATED': 'bg-blue-500/10 text-blue-400',
  'CRM_CONTACT_MERGED': 'bg-amber-500/10 text-amber-400',
  'CRM_NOTE_ADDED': 'bg-gray-500/10 text-gray-400',
  'CRM_CONTACT_LINKED': 'bg-blue-500/10 text-blue-400',
  'CRM_CONTACTS_EXPORTED': 'bg-purple-500/10 text-purple-400',
  'LOYALTY_RULES_UPDATED': 'bg-amber-500/10 text-amber-400',
  'LOYALTY_ENROLLED': 'bg-emerald-500/10 text-emerald-400',
  'LOYALTY_ADJUSTED': 'bg-amber-500/10 text-amber-400',
  'LOYALTY_REDEEMED': 'bg-rose-500/10 text-rose-400',
  'LOYALTY_EARNED': 'bg-emerald-500/10 text-emerald-400',
};

export default function AuditLogPage() {
  const tenant = useAuthStore((s) => s.tenant);

  const { data: logsData } = useQuery({
    queryKey: ['audit-logs', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/audit-logs`, { params: { limit: 100 } }).then(r => r.data),
    enabled: !!tenant?.slug,
    refetchInterval: 15000,
  });

  const logs = logsData?.data || [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Track all admin and staff actions - {logsData?.total || 0} events
        </p>
      </div>

      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <ScrollArea className="h-[calc(100vh-220px)]">
          <div className="divide-y divide-[hsl(var(--border))]">
            {logs.map(log => {
              const colorClass = actionColors[log.action] || 'bg-gray-500/10 text-gray-400';
              return (
                <div key={log.id} className="flex items-center gap-4 px-5 py-3 hover:bg-[hsl(var(--accent))] transition-colors" data-testid={`audit-log-${log.id}`}>
                  <div className="w-10 h-10 rounded-lg bg-[hsl(var(--secondary))] flex items-center justify-center flex-shrink-0">
                    <Shield className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge className={`${colorClass} border-0 text-xs`}>
                        {log.action?.replace(/_/g, ' ')}
                      </Badge>
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        {log.entity_type} 
                        {log.entity_id ? ` #${log.entity_id.substring(0, 8)}` : ''}
                      </span>
                    </div>
                    {log.details && Object.keys(log.details).length > 0 && (
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
                        {Object.entries(log.details).map(([k, v]) => `${k}: ${v}`).join(' | ')}
                      </p>
                    )}
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{timeAgo(log.created_at)}</p>
                    <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{formatDate(log.created_at)}</p>
                  </div>
                </div>
              );
            })}
            {logs.length === 0 && (
              <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
                <Shield className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p>No audit events yet</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </Card>
    </div>
  );
}
