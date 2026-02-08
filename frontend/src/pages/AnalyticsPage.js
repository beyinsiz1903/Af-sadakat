import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { TrendingUp, Users, Clock, Sparkles, Gift, BarChart3, Star, Repeat } from 'lucide-react';

export default function AnalyticsPage() {
  const tenant = useAuthStore((s) => s.tenant);

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/analytics`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  if (isLoading || !analytics) {
    return <div className="animate-fade-in"><h1 className="text-2xl font-bold mb-4">Analytics</h1><div className="grid grid-cols-4 gap-4">{[1,2,3,4].map(i=><Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] animate-pulse"><CardContent className="p-6"><div className="h-16 bg-[hsl(var(--secondary))] rounded" /></CardContent></Card>)}</div></div>;
  }

  const kpis = [
    { label: 'Total Revenue', value: `${new Intl.NumberFormat('tr-TR', {style:'currency', currency:'TRY'}).format(analytics.revenue?.total || 0)}`, icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { label: 'Repeat Guest Rate', value: `${analytics.guests?.repeat_rate || 0}%`, icon: Repeat, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { label: 'Avg Resolution Time', value: `${analytics.operations?.avg_resolution_time_min || 0} min`, icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { label: 'AI Efficiency', value: `${analytics.ai?.efficiency_pct || 0}%`, icon: Sparkles, color: 'text-purple-400', bg: 'bg-purple-500/10' },
    { label: 'Loyalty Retention', value: `${analytics.guests?.loyalty_retention || 0}%`, icon: Gift, color: 'text-pink-400', bg: 'bg-pink-500/10' },
    { label: 'Total Contacts', value: analytics.guests?.total_contacts || 0, icon: Users, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Revenue, operations, and AI performance insights</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpis.map(kpi => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">{kpi.label}</p>
                    <p className="text-2xl font-bold mt-1">{kpi.value}</p>
                  </div>
                  <div className={`w-11 h-11 rounded-xl ${kpi.bg} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${kpi.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Revenue Breakdown */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3"><CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Revenue Breakdown</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm"><span>From Orders</span><span className="font-medium">{new Intl.NumberFormat('tr-TR', {style:'currency', currency:'TRY'}).format(analytics.revenue?.from_orders || 0)}</span></div>
            <div className="flex justify-between text-sm"><span>From Reservations</span><span className="font-medium">{new Intl.NumberFormat('tr-TR', {style:'currency', currency:'TRY'}).format(analytics.revenue?.from_reservations || 0)}</span></div>
            <div className="flex justify-between text-sm border-t border-[hsl(var(--border))] pt-2"><span className="font-medium">Total</span><span className="font-bold">{new Intl.NumberFormat('tr-TR', {style:'currency', currency:'TRY'}).format(analytics.revenue?.total || 0)}</span></div>
          </CardContent>
        </Card>

        {/* Request Categories */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3"><CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Request Categories</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(analytics.operations?.category_breakdown || {}).map(([cat, count]) => (
              <div key={cat} className="flex justify-between text-sm">
                <span className="capitalize">{cat.replace('_', ' ')}</span>
                <Badge variant="secondary">{count}</Badge>
              </div>
            ))}
            {Object.keys(analytics.operations?.category_breakdown || {}).length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))]">No data yet</p>}
          </CardContent>
        </Card>

        {/* Rating Distribution */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3"><CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Rating Distribution</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {[5,4,3,2,1].map(r => {
              const count = analytics.operations?.rating_distribution?.[String(r)] || 0;
              return (
                <div key={r} className="flex items-center gap-3 text-sm">
                  <span className="flex items-center gap-1 w-12"><Star className="w-3 h-3 text-amber-400" /> {r}</span>
                  <div className="flex-1 bg-[hsl(var(--secondary))] rounded-full h-2">
                    <div className="bg-amber-400 h-2 rounded-full" style={{width: `${Math.min(count * 20, 100)}%`}} />
                  </div>
                  <span className="w-8 text-right">{count}</span>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* AI Stats */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3"><CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">AI Performance</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm"><span>Replies This Month</span><span className="font-medium">{analytics.ai?.replies_this_month}</span></div>
            <div className="flex justify-between text-sm"><span>Total Conversations</span><span className="font-medium">{analytics.ai?.total_conversations}</span></div>
            <div className="flex justify-between text-sm"><span>Efficiency</span><Badge className="bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">{analytics.ai?.efficiency_pct}%</Badge></div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
