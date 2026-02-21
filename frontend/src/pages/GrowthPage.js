import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Share2, MousePointerClick, UserPlus, Gift, Copy, ExternalLink, TrendingUp, Users, MessageSquare, Bot, DollarSign, Building2, CreditCard, BarChart3 } from 'lucide-react';
import { toast } from 'sonner';

function InvestorStatCard({ label, value, icon: Icon, color, bg, subtitle }) {
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

export default function GrowthPage() {
  const tenant = useAuthStore((s) => s.tenant);

  const { data: growth } = useQuery({
    queryKey: ['growth', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/growth/stats`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: investor } = useQuery({
    queryKey: ['investor-metrics'],
    queryFn: () => api.get('/system/investor-metrics').then(r => r.data),
  });

  const referralCode = growth?.referral?.code || '';
  const referralUrl = `${window.location.origin}/r/${referralCode}`;

  const copyLink = () => {
    navigator.clipboard.writeText(referralUrl);
    toast.success('Referans linki kopyalandi!');
  };

  const fmtCurrency = (val) => `$${(val || 0).toLocaleString()}`;

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Buyume & Referans</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Aginizi buyutun, oduller kazanin ve yatirimci metriklerini gorun</p>
      </div>

      <Tabs defaultValue="referral">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="referral">Referans Programi</TabsTrigger>
          <TabsTrigger value="investor">Yatirimci Metrikleri</TabsTrigger>
          <TabsTrigger value="demo">Demo Modu</TabsTrigger>
        </TabsList>

        <TabsContent value="referral" className="mt-4 space-y-4">
          {/* Referral Link */}
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-[hsl(var(--primary)/0.1)] flex items-center justify-center">
                  <Share2 className="w-6 h-6 text-[hsl(var(--primary))]" />
                </div>
                <div>
                  <h3 className="font-bold">Referans Linkiniz</h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Paylasin ve her kayit icin 50 AI kredi kazanin</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-[hsl(var(--secondary))] rounded-lg px-4 py-2.5 font-mono text-sm truncate border border-[hsl(var(--border))]">
                  {referralUrl}
                </div>
                <Button size="sm" onClick={copyLink} className="shrink-0 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.9)]">
                  <Copy className="w-4 h-4 mr-1" /> Kopyala
                </Button>
              </div>
              <div className="mt-3">
                <Badge variant="outline" className="font-mono">{referralCode}</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Referral Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <InvestorStatCard label="Tiklama" value={growth?.total_clicks || 0} icon={MousePointerClick} color="text-blue-400" bg="bg-blue-500/10" />
            <InvestorStatCard label="Kayit" value={growth?.total_signups || 0} icon={UserPlus} color="text-emerald-400" bg="bg-emerald-500/10" />
            <InvestorStatCard label="Kazanilan Odul" value={`${growth?.total_rewards || 0} AI Kredi`} icon={Gift} color="text-amber-400" bg="bg-amber-500/10" />
          </div>

          {/* Referral Events */}
          {growth?.events && growth.events.length > 0 && (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardHeader><CardTitle className="text-sm">Referans Gecmisi</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {growth.events.map(e => (
                    <div key={e.id} className="flex items-center justify-between py-2 border-b border-[hsl(var(--border))] last:border-0">
                      <div>
                        <p className="text-sm">Yeni kayit referansinizla</p>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">{new Date(e.created_at).toLocaleDateString('tr-TR')}</p>
                      </div>
                      <Badge className="bg-emerald-500/20 text-emerald-400">+{e.reward} AI Kredi</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="investor" className="mt-4 space-y-4">
          {investor ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <InvestorStatCard label="MRR" value={fmtCurrency(investor.mrr)} icon={DollarSign} color="text-emerald-400" bg="bg-emerald-500/10" subtitle={`ARR: ${fmtCurrency(investor.arr)}`} />
                <InvestorStatCard label="Aktif Tenant" value={investor.active_tenants} icon={Building2} color="text-blue-400" bg="bg-blue-500/10" subtitle={`Toplam: ${investor.total_tenants}`} />
                <InvestorStatCard label="Islenen Mesaj" value={investor.total_messages_processed?.toLocaleString() || 0} icon={MessageSquare} color="text-amber-400" bg="bg-amber-500/10" />
                <InvestorStatCard label="AI Cevap" value={investor.ai_replies_generated?.toLocaleString() || 0} icon={Bot} color="text-purple-400" bg="bg-purple-500/10" />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <InvestorStatCard label="Toplam Kullanici" value={investor.total_users} icon={Users} color="text-indigo-400" bg="bg-indigo-500/10" />
                <InvestorStatCard label="Toplam Iletisim" value={investor.total_contacts?.toLocaleString() || 0} icon={Users} color="text-pink-400" bg="bg-pink-500/10" />
                <InvestorStatCard label="Toplam Rezervasyon" value={investor.total_reservations} icon={CreditCard} color="text-teal-400" bg="bg-teal-500/10" />
                <InvestorStatCard label="Toplam Gelir" value={`${(investor.total_revenue_processed || 0).toLocaleString()} TRY`} icon={TrendingUp} color="text-emerald-400" bg="bg-emerald-500/10" />
              </div>

              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardHeader><CardTitle className="text-sm">Plan Dagilimi</CardTitle></CardHeader>
                <CardContent>
                  <div className="flex gap-4">
                    {investor.plan_distribution && Object.entries(investor.plan_distribution).map(([plan, count]) => (
                      <div key={plan} className="flex items-center gap-2">
                        <Badge className={`capitalize ${plan === 'enterprise' ? 'bg-purple-500/20 text-purple-400' : plan === 'pro' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>
                          {plan}: {count}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardHeader><CardTitle className="text-sm">Buyume (Son 30 Gun)</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between"><span className="text-sm">Yeni Tenant</span><span className="font-semibold">{investor.new_tenants_30d || 0}</span></div>
                      <div className="flex justify-between"><span className="text-sm">Yeni Iletisim</span><span className="font-semibold">{investor.new_contacts_30d || 0}</span></div>
                      <div className="flex justify-between"><span className="text-sm">Sadakat Uyeleri</span><span className="font-semibold">{investor.loyalty_members || 0}</span></div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardHeader><CardTitle className="text-sm">Operasyonel Metrikler</CardTitle></CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between"><span className="text-sm">Toplam Talep</span><span className="font-semibold">{investor.total_requests_handled || 0}</span></div>
                      <div className="flex justify-between"><span className="text-sm">Toplam Siparis</span><span className="font-semibold">{investor.total_orders_processed || 0}</span></div>
                      <div className="flex justify-between"><span className="text-sm">Toplam Yorum</span><span className="font-semibold">{investor.total_reviews || 0}</span></div>
                      <div className="flex justify-between"><span className="text-sm">Toplam Konusma</span><span className="font-semibold">{investor.total_conversations || 0}</span></div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">Metrikler yukleniyor...</div>
          )}
        </TabsContent>

        <TabsContent value="demo" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <BarChart3 className="w-8 h-8 text-[hsl(var(--primary))]" />
                <div>
                  <h3 className="font-bold">Demo Modu</h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Yeni kullanicilar icin hazir demo verisi ile sistemi tanitin</p>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-[hsl(var(--secondary)/0.5)] border border-[hsl(var(--border))]">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  Demo modu, yeni tenant kaydolduklarinda otomatik olarak ornek verilerle doldurulur:
                </p>
                <ul className="mt-2 space-y-1 text-sm">
                  <li>• 5 oda, 3 masa, departmanlar</li>
                  <li>• Ornek misafir talepleri ve siparisler</li>
                  <li>• AI satis ayarlari ve oda ucretleri</li>
                  <li>• Sadakat programi ve rozet sistemi</li>
                  <li>• Ornek konusmalar ve yorumlar</li>
                </ul>
              </div>
              <Button className="mt-4" variant="outline" onClick={() => toast.info('Demo verisi yeni tenant kayitlarinda otomatik olusturulur')}>
                Demo Bilgi
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
