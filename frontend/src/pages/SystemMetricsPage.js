import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Server, Database, Users, MessageSquare, ClipboardList, UtensilsCrossed, Star, CalendarDays, Zap, DollarSign } from 'lucide-react';

export default function SystemMetricsPage() {
  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => api.get('/system/status').then(r => r.data),
    refetchInterval: 30000,
  });

  const { data: metrics } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: () => api.get('/system/metrics').then(r => r.data),
    refetchInterval: 15000,
  });

  const metricCards = metrics ? [
    { label: 'Active Tenants', value: metrics.active_tenants ?? metrics.total_tenants, icon: Server, color: 'text-blue-400' },
    { label: 'Total Users', value: metrics.total_users, icon: Users, color: 'text-emerald-400' },
    { label: 'Requests Handled', value: metrics.total_requests_handled, icon: ClipboardList, color: 'text-amber-400' },
    { label: 'Orders Processed', value: metrics.total_orders_processed, icon: UtensilsCrossed, color: 'text-pink-400' },
    { label: 'Messages', value: metrics.total_messages_processed, icon: MessageSquare, color: 'text-purple-400' },
    { label: 'Reviews', value: metrics.total_reviews, icon: Star, color: 'text-amber-400' },
    { label: 'Reservations', value: metrics.total_reservations, icon: CalendarDays, color: 'text-indigo-400' },
    { label: 'AI Replies', value: metrics.ai_replies_generated, icon: Zap, color: 'text-emerald-400' },
    { label: 'MRR', value: `$${metrics.mrr}`, icon: DollarSign, color: 'text-emerald-400' },
  ] : [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">System Metrics</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Platform health and investor metrics</p>
        </div>
        {status && (
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${status.status === 'operational' ? 'bg-emerald-400' : 'bg-rose-400'} pulse-dot`} />
            <span className="text-sm capitalize">{status.status}</span>
            <Badge variant="secondary">v{status.version}</Badge>
            <Badge className={status.database === 'connected' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}>
              DB: {status.database}
            </Badge>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {metricCards.map(m => {
          const Icon = m.icon;
          return (
            <Card key={m.label} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">{m.label}</p>
                    <p className="text-2xl font-bold mt-1">{m.value}</p>
                  </div>
                  <Icon className={`w-8 h-8 ${m.color} opacity-40`} />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
