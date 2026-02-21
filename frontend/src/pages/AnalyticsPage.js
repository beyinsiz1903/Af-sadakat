import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { TrendingUp, TrendingDown, Users, Clock, Sparkles, Gift, BarChart3, Star, Repeat, DollarSign, Target, UserCheck, BedDouble, Bot } from 'lucide-react';
import { Progress } from '../components/ui/progress';

function StatCard({ label, value, icon: Icon, color, bg, subtitle }) {
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">{label}</p>
            <p className="text-xl font-bold">{value}</p>
            {subtitle && <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{subtitle}</p>}
          </div>
          <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center`}>
            <Icon className={`w-4.5 h-4.5 ${color}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  const tenant = useAuthStore((s) => s.tenant);

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/analytics`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: revenue } = useQuery({
    queryKey: ['revenue-analytics', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/analytics/revenue`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: staffPerf } = useQuery({
    queryKey: ['staff-performance', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/analytics/staff-performance`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  if (isLoading || !analytics) {
    return (
      <div className="animate-fade-in">
        <h1 className="text-2xl font-bold mb-4">Analitik & Zeka</h1>
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] animate-pulse">
              <CardContent className="p-6"><div className="h-16 bg-[hsl(var(--secondary))] rounded" /></CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const fmtCurrency = (val) => new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(val || 0);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Analitik & Zeka</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Gelir, operasyon, personel ve AI performans gorselleri</p>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="overview">Genel Bakis</TabsTrigger>
          <TabsTrigger value="revenue">Gelir Analitigi</TabsTrigger>
          <TabsTrigger value="staff">Personel Performansi</TabsTrigger>
          <TabsTrigger value="operations">Operasyonlar</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <StatCard label="Toplam Gelir" value={fmtCurrency(analytics.revenue?.total)} icon={TrendingUp} color="text-emerald-400" bg="bg-emerald-500/10" />
            <StatCard label="Tekrar Misafir Orani" value={`${analytics.guests?.repeat_rate || 0}%`} icon={Repeat} color="text-blue-400" bg="bg-blue-500/10" />
            <StatCard label="Ort. Cozum Suresi" value={`${analytics.operations?.avg_resolution_time_min || 0} dk`} icon={Clock} color="text-amber-400" bg="bg-amber-500/10" />
            <StatCard label="AI Verimlilik" value={`${analytics.ai?.efficiency_pct || 0}%`} icon={Sparkles} color="text-purple-400" bg="bg-purple-500/10" />
            <StatCard label="Sadakat Tutma" value={`${analytics.guests?.loyalty_retention || 0}%`} icon={Gift} color="text-pink-400" bg="bg-pink-500/10" />
            <StatCard label="Toplam Iletisim" value={analytics.guests?.total_contacts || 0} icon={Users} color="text-indigo-400" bg="bg-indigo-500/10" />
          </div>

          {analytics.operations?.category_breakdown && Object.keys(analytics.operations.category_breakdown).length > 0 && (
            <Card className="mt-4 bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardHeader><CardTitle className="text-sm">Kategori Dagilimi</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(analytics.operations.category_breakdown).map(([cat, count]) => (
                    <div key={cat} className="flex items-center justify-between">
                      <span className="text-sm capitalize">{cat}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-32 bg-[hsl(var(--secondary))] rounded-full h-2">
                          <div className="bg-[hsl(var(--primary))] h-2 rounded-full" style={{ width: `${Math.min(100, count * 10)}%` }} />
                        </div>
                        <span className="text-sm text-[hsl(var(--muted-foreground))] w-8 text-right">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="revenue" className="mt-4">
          {revenue ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard label="Toplam Gelir" value={fmtCurrency(revenue.total_revenue)} icon={DollarSign} color="text-emerald-400" bg="bg-emerald-500/10"
                  subtitle={`${revenue.revenue_change_pct > 0 ? '+' : ''}${revenue.revenue_change_pct}% degisim`} />
                <StatCard label="Upsell Donusum" value={`${revenue.upsell_conversion_rate}%`} icon={Target} color="text-blue-400" bg="bg-blue-500/10"
                  subtitle={`${revenue.offers_converted}/${revenue.offers_sent} teklif`} />
                <StatCard label="RevPAR" value={fmtCurrency(revenue.revpar)} icon={BedDouble} color="text-amber-400" bg="bg-amber-500/10"
                  subtitle={`${revenue.room_count} oda`} />
                <StatCard label="AI Teklifler" value={revenue.ai_offers_created || 0} icon={Bot} color="text-purple-400" bg="bg-purple-500/10"
                  subtitle={`${revenue.ai_offers_converted || 0} donusturuldu`} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardHeader><CardTitle className="text-sm">Gelir Kaynagi</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Siparis Geliri</span>
                        <span className="font-semibold">{fmtCurrency(revenue.order_revenue)}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Rezervasyon Geliri</span>
                        <span className="font-semibold">{fmtCurrency(revenue.reservation_revenue)}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardHeader><CardTitle className="text-sm">Gunluk Gelir ({revenue.period_days} gun)</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {(revenue.daily_revenue || []).map(d => (
                        <div key={d.date} className="flex justify-between items-center text-sm">
                          <span className="text-[hsl(var(--muted-foreground))]">{d.date}</span>
                          <span>{fmtCurrency(d.total)} ({d.count} adet)</span>
                        </div>
                      ))}
                      {(!revenue.daily_revenue || revenue.daily_revenue.length === 0) && (
                        <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">Veri yok</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">Gelir verisi yukleniyor...</div>
          )}
        </TabsContent>

        <TabsContent value="staff" className="mt-4">
          {staffPerf ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <StatCard label="Toplam Personel" value={staffPerf.total_staff} icon={Users} color="text-blue-400" bg="bg-blue-500/10" />
                <StatCard label="Takim Verimliligi" value={`${staffPerf.avg_team_efficiency}%`} icon={Target} color="text-emerald-400" bg="bg-emerald-500/10" />
                <StatCard label="Donem" value={`${staffPerf.period_days} gun`} icon={Clock} color="text-amber-400" bg="bg-amber-500/10" />
              </div>

              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-[hsl(var(--border))]">
                        <TableHead>Personel</TableHead>
                        <TableHead>Rol</TableHead>
                        <TableHead>Atanan</TableHead>
                        <TableHead>Cozulen</TableHead>
                        <TableHead>Cozum %</TableHead>
                        <TableHead>Ort. Yanit</TableHead>
                        <TableHead>Puan</TableHead>
                        <TableHead>Verimlilik</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(staffPerf.staff || []).map((s, idx) => (
                        <TableRow key={s.user_id} className="border-[hsl(var(--border))]">
                          <TableCell className="font-medium">
                            <div className="flex items-center gap-2">
                              {idx === 0 && <span className="text-lg">🥇</span>}
                              {idx === 1 && <span className="text-lg">🥈</span>}
                              {idx === 2 && <span className="text-lg">🥉</span>}
                              {s.name}
                            </div>
                          </TableCell>
                          <TableCell><Badge variant="outline" className="text-xs capitalize">{s.role}</Badge></TableCell>
                          <TableCell>{s.assigned_requests}</TableCell>
                          <TableCell>{s.resolved_requests}</TableCell>
                          <TableCell>{s.resolution_rate}%</TableCell>
                          <TableCell>{s.avg_response_time_min} dk</TableCell>
                          <TableCell>
                            {s.avg_rating > 0 ? (
                              <div className="flex items-center gap-1">
                                <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                                <span>{s.avg_rating}</span>
                              </div>
                            ) : '-'}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={s.efficiency_score} className="h-1.5 w-16" />
                              <span className="text-sm">{s.efficiency_score}</span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                      {(!staffPerf.staff || staffPerf.staff.length === 0) && (
                        <TableRow><TableCell colSpan={8} className="text-center text-[hsl(var(--muted-foreground))] py-8">Personel verisi yok</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">Personel verisi yukleniyor...</div>
          )}
        </TabsContent>

        <TabsContent value="operations" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardHeader><CardTitle className="text-sm">Siparis Durumu</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {analytics.operations?.order_by_status && Object.entries(analytics.operations.order_by_status).map(([status, count]) => (
                    <div key={status} className="flex justify-between items-center">
                      <Badge variant="outline" className="capitalize text-xs">{status}</Badge>
                      <span className="text-sm font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardHeader><CardTitle className="text-sm">AI Performans</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between"><span className="text-sm">AI Cevaplari (Bu Ay)</span><span className="font-semibold">{analytics.ai?.replies_this_month || 0}</span></div>
                  <div className="flex justify-between"><span className="text-sm">Toplam Konusma</span><span className="font-semibold">{analytics.ai?.total_conversations || 0}</span></div>
                  <div className="flex justify-between"><span className="text-sm">AI Verimlilik</span><span className="font-semibold">{analytics.ai?.efficiency_pct || 0}%</span></div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
