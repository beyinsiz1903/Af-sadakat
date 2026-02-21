import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { reportsAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { BarChart3, Users, Star, Clock, TrendingUp, Bot, Shield, FlaskConical, Trophy } from 'lucide-react';

export default function ReportsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const [tab, setTab] = useState('department');
  const [days, setDays] = useState(30);

  const { data: deptPerf = [] } = useQuery({
    queryKey: ['dept-perf', tenant?.slug, days],
    queryFn: () => reportsAPI.departmentPerformance(tenant?.slug, { days }).then(r => r.data),
    enabled: !!tenant?.slug && tab === 'department',
  });

  const { data: satisfaction } = useQuery({
    queryKey: ['satisfaction', tenant?.slug, days],
    queryFn: () => reportsAPI.guestSatisfaction(tenant?.slug, { days }).then(r => r.data),
    enabled: !!tenant?.slug && tab === 'satisfaction',
  });

  const { data: staffProd = [] } = useQuery({
    queryKey: ['staff-prod', tenant?.slug, days],
    queryFn: () => reportsAPI.staffProductivity(tenant?.slug, { days }).then(r => r.data),
    enabled: !!tenant?.slug && tab === 'staff',
  });

  const { data: peakData } = useQuery({
    queryKey: ['peak-demand', tenant?.slug, days],
    queryFn: () => reportsAPI.peakDemand(tenant?.slug, { days }).then(r => r.data),
    enabled: !!tenant?.slug && tab === 'peak',
  });

  const { data: aiPerf } = useQuery({
    queryKey: ['ai-perf', tenant?.slug],
    queryFn: () => reportsAPI.aiPerformance(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug && tab === 'ai',
  });

  const tabs = [
    { id: 'department', label: 'Department', icon: Shield },
    { id: 'satisfaction', label: 'Guest Satisfaction', icon: Star },
    { id: 'staff', label: 'Staff', icon: Users },
    { id: 'peak', label: 'Peak Demand', icon: TrendingUp },
    { id: 'ai', label: 'AI Performance', icon: Bot },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Advanced Reports</h1>
        <Select value={String(days)} onValueChange={(v) => setDays(+v)}>
          <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex gap-2 flex-wrap">
        {tabs.map(t => (
          <Button key={t.id} variant={tab === t.id ? 'default' : 'outline'} size="sm" onClick={() => setTab(t.id)}>
            <t.icon className="w-4 h-4 mr-1" />{t.label}
          </Button>
        ))}
      </div>

      {tab === 'department' && (
        <div className="space-y-3">
          {deptPerf.map((dept, i) => (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{dept.department}</h3>
                  <Badge variant="outline">{dept.code}</Badge>
                </div>
                <div className="grid grid-cols-5 gap-4 text-center">
                  <div><p className="text-lg font-bold">{dept.total_requests}</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Total</p></div>
                  <div><p className="text-lg font-bold text-emerald-400">{dept.resolution_rate}%</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Resolved</p></div>
                  <div><p className="text-lg font-bold">{dept.open}</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Open</p></div>
                  <div><p className="text-lg font-bold text-blue-400">{dept.avg_resolution_minutes}m</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Avg Time</p></div>
                  <div><p className="text-lg font-bold text-amber-400">{dept.avg_rating > 0 ? `${dept.avg_rating}★` : '-'}</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Rating</p></div>
                </div>
              </CardContent>
            </Card>
          ))}
          {deptPerf.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">No data for this period</p>}
        </div>
      )}

      {tab === 'satisfaction' && satisfaction && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]"><CardContent className="p-4 text-center"><p className="text-2xl font-bold">{satisfaction.total_rated_requests}</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Rated Requests</p></CardContent></Card>
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]"><CardContent className="p-4 text-center"><p className="text-2xl font-bold">{satisfaction.total_reviews}</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Reviews</p></CardContent></Card>
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]"><CardContent className="p-4 text-center"><p className="text-2xl font-bold">{satisfaction.total_surveys}</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Surveys</p></CardContent></Card>
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]"><CardContent className="p-4 text-center"><p className="text-2xl font-bold text-[hsl(var(--primary))]">{satisfaction.nps_score}</p><p className="text-xs text-[hsl(var(--muted-foreground))]">NPS Score</p></CardContent></Card>
          </div>
          {satisfaction.category_ratings && Object.keys(satisfaction.category_ratings).length > 0 && (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardHeader><CardTitle>Category Ratings</CardTitle></CardHeader>
              <CardContent>
                {Object.entries(satisfaction.category_ratings).map(([cat, rating]) => (
                  <div key={cat} className="flex items-center justify-between py-2 border-b border-[hsl(var(--border))] last:border-0">
                    <span className="text-sm capitalize">{cat}</span>
                    <div className="flex items-center gap-1"><Star className="w-4 h-4 text-amber-400" /><span className="font-bold">{rating}</span></div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {tab === 'staff' && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-[hsl(var(--border))]">
              <th className="text-left py-2">Staff</th>
              <th className="text-center">Assigned</th>
              <th className="text-center">Resolved</th>
              <th className="text-center">Rate</th>
              <th className="text-center">Avg Time</th>
              <th className="text-center">Rating</th>
            </tr></thead>
            <tbody>
              {staffProd.map((s, i) => (
                <tr key={i} className="border-b border-[hsl(var(--border))]">
                  <td className="py-2 font-medium">{s.staff_name}</td>
                  <td className="text-center">{s.total_assigned}</td>
                  <td className="text-center text-emerald-400">{s.resolved}</td>
                  <td className="text-center">{s.resolution_rate}%</td>
                  <td className="text-center text-blue-400">{s.avg_resolution_minutes}m</td>
                  <td className="text-center text-amber-400">{s.avg_rating > 0 ? `${s.avg_rating}★` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'peak' && peakData && (
        <div className="space-y-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle>Hourly Distribution</CardTitle></CardHeader>
            <CardContent>
              <div className="flex items-end gap-1 h-32">
                {Object.entries(peakData.hourly_distribution || {}).map(([hour, data]) => {
                  const maxVal = Math.max(...Object.values(peakData.hourly_distribution || {}).map(d => d.requests + d.orders), 1);
                  const height = ((data.requests + data.orders) / maxVal) * 100;
                  return (
                    <div key={hour} className="flex-1 flex flex-col items-center">
                      <div className="w-full bg-[hsl(var(--primary))] rounded-t" style={{ height: `${height}%`, minHeight: height > 0 ? '2px' : 0 }} />
                      <span className="text-[8px] mt-1 text-[hsl(var(--muted-foreground))]">{hour}</span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle>Daily Distribution</CardTitle></CardHeader>
            <CardContent>
              <div className="flex items-end gap-4 h-24 justify-center">
                {Object.entries(peakData.daily_distribution || {}).map(([day, count]) => {
                  const maxVal = Math.max(...Object.values(peakData.daily_distribution || {}), 1);
                  return (
                    <div key={day} className="flex flex-col items-center">
                      <div className="w-10 bg-[hsl(var(--primary))] rounded-t" style={{ height: `${(count / maxVal) * 100}%`, minHeight: count > 0 ? '2px' : 0 }} />
                      <span className="text-xs mt-1">{day}</span>
                      <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{count}</span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {tab === 'ai' && aiPerf && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'AI Messages', value: aiPerf.total_ai_messages },
            { label: 'AI Sessions', value: aiPerf.total_ai_sessions },
            { label: 'Tokens Used', value: aiPerf.total_tokens_used },
            { label: 'AI Offers', value: aiPerf.ai_offers_created },
            { label: 'AI Paid Offers', value: aiPerf.ai_offers_paid },
            { label: 'Conversion', value: `${aiPerf.ai_conversion_rate}%` },
            { label: 'Monthly Usage', value: `${aiPerf.monthly_usage}/${aiPerf.monthly_limit}` },
          ].map((s, i) => (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4 text-center">
                <p className="text-xl font-bold">{s.value}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">{s.label}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
