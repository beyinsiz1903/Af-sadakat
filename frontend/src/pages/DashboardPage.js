import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { tenantAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ClipboardList, UtensilsCrossed, Users, MessageSquare, BedDouble, TableProperties, Star, Zap } from 'lucide-react';

export default function DashboardPage() {
  const tenant = useAuthStore((s) => s.tenant);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats', tenant?.slug],
    queryFn: () => tenantAPI.stats(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
    refetchInterval: 15000,
  });

  if (isLoading || !stats) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div><h1 className="text-2xl font-bold">Dashboard</h1></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] animate-pulse">
              <CardContent className="p-6"><div className="h-16 bg-[hsl(var(--secondary))] rounded" /></CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const kpis = [
    { label: 'Open Requests', value: stats.requests.open, icon: ClipboardList, color: 'text-[hsl(var(--info))]', bgColor: 'bg-[hsl(var(--info)/0.1)]' },
    { label: 'Active Orders', value: stats.orders.active, icon: UtensilsCrossed, color: 'text-[hsl(var(--warning))]', bgColor: 'bg-[hsl(var(--warning)/0.1)]' },
    { label: 'Contacts', value: stats.contacts, icon: Users, color: 'text-[hsl(var(--primary))]', bgColor: 'bg-[hsl(var(--primary)/0.1)]' },
    { label: 'Conversations', value: stats.conversations, icon: MessageSquare, color: 'text-[hsl(var(--success))]', bgColor: 'bg-[hsl(var(--success)/0.1)]' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-[hsl(var(--muted-foreground))] text-sm mt-1">Welcome back. Here's what's happening at {tenant?.name}.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-colors">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">{kpi.label}</p>
                    <p className="text-3xl font-bold mt-1" data-testid={`kpi-${kpi.label.toLowerCase().replace(/\s/g, '-')}`}>{kpi.value}</p>
                  </div>
                  <div className={`w-11 h-11 rounded-xl ${kpi.bgColor} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${kpi.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Request Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Total Requests</span>
              <Badge variant="secondary">{stats.requests.total}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">In Progress</span>
              <Badge className="bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border-[hsl(var(--primary)/0.25)]">{stats.requests.in_progress}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Completed</span>
              <Badge className="bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.25)]">{stats.requests.done}</Badge>
            </div>
            {stats.avg_rating > 0 && (
              <div className="flex items-center justify-between pt-2 border-t border-[hsl(var(--border))]">
                <span className="text-sm flex items-center gap-1.5"><Star className="w-4 h-4 text-amber-400" /> Avg Rating</span>
                <span className="font-semibold">{stats.avg_rating}/5 <span className="text-xs text-[hsl(var(--muted-foreground))]">({stats.rating_count})</span></span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Resources</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm flex items-center gap-2"><BedDouble className="w-4 h-4" /> Rooms</span>
              <span className="text-sm font-medium">{stats.rooms} / {stats.limits?.max_rooms}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm flex items-center gap-2"><TableProperties className="w-4 h-4" /> Tables</span>
              <span className="text-sm font-medium">{stats.tables} / {stats.limits?.max_tables}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm flex items-center gap-2"><Users className="w-4 h-4" /> Users</span>
              <span className="text-sm font-medium">{stats.usage?.users} / {stats.limits?.max_users}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">AI Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm flex items-center gap-2"><Zap className="w-4 h-4 text-amber-400" /> AI Replies This Month</span>
              <span className="text-sm font-medium">{stats.usage?.ai_replies_this_month} / {stats.limits?.monthly_ai_replies}</span>
            </div>
            <div className="w-full bg-[hsl(var(--secondary))] rounded-full h-2 mt-2">
              <div
                className="bg-[hsl(var(--primary))] h-2 rounded-full transition-all"
                style={{ width: `${Math.min((stats.usage?.ai_replies_this_month / stats.limits?.monthly_ai_replies) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Provider: Mock Template v1</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
