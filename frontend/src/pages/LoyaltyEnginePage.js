import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { loyaltyEngineAPI, loyaltyAnalyticsAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import {
  Crown, Star, Award, Shield, Users, TrendingUp, Gift, Target, Megaphone,
  Share2, CreditCard, QrCode, BarChart3, Brain, RefreshCw, Plus, Trash2,
  Edit, ChevronDown, ChevronUp, Mail, MessageSquare, Bell, Smartphone,
  Plane, Car, Clock, Sparkles, Sun, ArrowUpCircle, Utensils, Bed,
  AlertTriangle, CheckCircle, XCircle, Heart, Zap, Eye
} from 'lucide-react';

const TABS = [
  { id: 'overview', label: 'Genel Bakis', icon: BarChart3 },
  { id: 'point-rules', label: 'Puan Kurallari', icon: Target },
  { id: 'tiers', label: 'Seviye Yonetimi', icon: Crown },
  { id: 'rewards', label: 'Odul Katalogu', icon: Gift },
  { id: 'campaigns', label: 'Kampanyalar', icon: Megaphone },
  { id: 'referral', label: 'Referral', icon: Share2 },
  { id: 'digital-card', label: 'Dijital Kart', icon: CreditCard },
  { id: 'segmentation', label: 'Segmentasyon', icon: Brain },
  { id: 'analytics', label: 'Analitik', icon: TrendingUp },
  { id: 'communication', label: 'Iletisim', icon: Mail },
];

function StatCard({ label, value, icon: Icon, color = 'text-blue-400', bg = 'bg-blue-500/10', subtitle }) {
  return (
    <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center`}>
            <Icon className={`w-5 h-5 ${color}`} />
          </div>
          <div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
            <p className="text-xl font-bold">{value}</p>
            {subtitle && <p className="text-xs text-[hsl(var(--muted-foreground))]">{subtitle}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============ OVERVIEW TAB ============
function OverviewTab({ slug }) {
  const { data: overview, isLoading } = useQuery({
    queryKey: ['loyalty-overview', slug],
    queryFn: () => loyaltyEngineAPI.getOverview(slug).then(r => r.data),
    enabled: !!slug,
  });
  const { data: roi } = useQuery({
    queryKey: ['loyalty-roi', slug],
    queryFn: () => loyaltyAnalyticsAPI.getROI(slug).then(r => r.data),
    enabled: !!slug,
  });

  if (isLoading) return <div className="animate-pulse space-y-4"><div className="h-24 bg-[hsl(var(--secondary))] rounded-lg" /><div className="h-24 bg-[hsl(var(--secondary))] rounded-lg" /></div>;

  const o = overview || {};
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <StatCard label="Toplam Uye" value={o.total_members || 0} icon={Users} color="text-blue-400" bg="bg-blue-500/10" />
        <StatCard label="Yeni Uye (30g)" value={o.new_members_30d || 0} icon={TrendingUp} color="text-green-400" bg="bg-green-500/10" />
        <StatCard label="Dolasimdaki Puan" value={(o.points_in_circulation || 0).toLocaleString()} icon={Star} color="text-yellow-400" bg="bg-yellow-500/10" />
        <StatCard label="Redemption Orani" value={`${o.redemption_rate || 0}%`} icon={Gift} color="text-purple-400" bg="bg-purple-500/10" />
        <StatCard label="Toplam Referral" value={o.total_referrals || 0} icon={Share2} color="text-pink-400" bg="bg-pink-500/10" />
        <StatCard label="Aktif Kampanya" value={o.active_campaigns || 0} icon={Megaphone} color="text-orange-400" bg="bg-orange-500/10" />
        <StatCard label="Puan Kurali" value={o.point_rules_count || 0} icon={Target} color="text-cyan-400" bg="bg-cyan-500/10" />
        <StatCard label="Odul Cesidi" value={o.rewards_count || 0} icon={Gift} color="text-emerald-400" bg="bg-emerald-500/10" />
      </div>

      {/* Tier Distribution */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-lg">Seviye Dagilimi</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-4 flex-wrap">
            {(o.tier_distribution || []).map((t, i) => {
              const colors = { bronze: '#CD7F32', silver: '#C0C0C0', gold: '#FFD700', platinum: '#E5E4E2', Silver: '#C0C0C0', Gold: '#FFD700' };
              return (
                <div key={i} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--secondary))]">
                  <div className="w-4 h-4 rounded-full" style={{ backgroundColor: colors[t.tier] || '#888' }} />
                  <span className="font-medium capitalize">{t.tier}</span>
                  <Badge variant="outline">{t.count}</Badge>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* ROI Summary */}
      {roi && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader><CardTitle className="text-lg">ROI Ozeti</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="text-center p-3 rounded-lg bg-[hsl(var(--secondary))]">
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Program Maliyeti</p>
                <p className="text-lg font-bold">{(roi.program_cost_try || 0).toLocaleString()} TRY</p>
              </div>
              <div className="text-center p-3 rounded-lg bg-[hsl(var(--secondary))]">
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Tahmini Gelir</p>
                <p className="text-lg font-bold text-green-400">{(roi.estimated_revenue_try || 0).toLocaleString()} TRY</p>
              </div>
              <div className="text-center p-3 rounded-lg bg-[hsl(var(--secondary))]">
                <p className="text-xs text-[hsl(var(--muted-foreground))]">ROI</p>
                <p className="text-lg font-bold text-blue-400">{roi.roi_percentage || 0}%</p>
              </div>
              <div className="text-center p-3 rounded-lg bg-[hsl(var(--secondary))]">
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Redemption Orani</p>
                <p className="text-lg font-bold">{roi.redemption_rate || 0}%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ============ POINT RULES TAB ============
function PointRulesTab({ slug }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['point-rules', slug],
    queryFn: () => loyaltyEngineAPI.listPointRules(slug).then(r => r.data),
    enabled: !!slug,
  });
  const deleteMut = useMutation({
    mutationFn: (id) => loyaltyEngineAPI.deletePointRule(slug, id),
    onSuccess: () => { qc.invalidateQueries(['point-rules']); toast.success('Kural silindi'); },
  });

  const typeColors = { accommodation: 'bg-blue-500/20 text-blue-300', spend: 'bg-green-500/20 text-green-300', activity: 'bg-purple-500/20 text-purple-300', custom: 'bg-orange-500/20 text-orange-300' };
  const typeLabels = { accommodation: 'Konaklama', spend: 'Harcama', activity: 'Aktivite', custom: 'Ozel' };

  if (isLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">{data?.total || 0} aktif kural</p>
      </div>
      <div className="grid gap-3">
        {(data?.data || []).map(rule => (
          <Card key={rule.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center">
                    <Target className="w-5 h-5 text-[hsl(var(--primary))]" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{rule.name}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${typeColors[rule.rule_type] || ''}`}>
                        {typeLabels[rule.rule_type] || rule.rule_type}
                      </span>
                      {rule.multiplier_enabled && <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-300">Carpan Aktif</span>}
                    </div>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">{rule.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-xl font-bold text-yellow-400">+{rule.points}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">puan</p>
                  </div>
                  <Button size="sm" variant="ghost" className="text-red-400 hover:text-red-300" onClick={() => deleteMut.mutate(rule.id)}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              {rule.condition && Object.keys(rule.condition).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(rule.condition).map(([k, v]) => (
                    <Badge key={k} variant="outline" className="text-xs">{k}: {String(v)}</Badge>
                  ))}
                </div>
              )}
              {rule.applies_to_tiers && rule.applies_to_tiers.length > 0 && (
                <div className="mt-1 flex gap-1">
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">Seviyeler:</span>
                  {rule.applies_to_tiers.map(t => <Badge key={t} variant="outline" className="text-xs capitalize">{t}</Badge>)}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============ TIERS TAB ============
function TiersTab({ slug }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['tier-config', slug],
    queryFn: () => loyaltyEngineAPI.getTiers(slug).then(r => r.data),
    enabled: !!slug,
  });
  const evaluateMut = useMutation({
    mutationFn: () => loyaltyEngineAPI.evaluateTiers(slug),
    onSuccess: (res) => { toast.success(`Degerlendirme: ${res.data.upgraded} yukseltme, ${res.data.downgraded} dusurme`); },
  });

  const tierIcons = { shield: Shield, award: Award, star: Star, crown: Crown };
  if (isLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;

  const tiers = data?.tiers || [];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant={data?.auto_upgrade ? 'default' : 'outline'}>{data?.auto_upgrade ? 'Otomatik Yukseltme Aktif' : 'Manuel Yukseltme'}</Badge>
            <Badge variant={data?.auto_downgrade ? 'default' : 'outline'}>{data?.auto_downgrade ? 'Otomatik Dusurme Aktif' : 'Manuel Dusurme'}</Badge>
          </div>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Degerlendirme periyodu: {data?.evaluation_period || 'yearly'} | Dusurme suresi: {data?.downgrade_period_days || 365} gun</p>
        </div>
        <Button size="sm" onClick={() => evaluateMut.mutate()} disabled={evaluateMut.isPending}>
          <RefreshCw className={`w-4 h-4 mr-1 ${evaluateMut.isPending ? 'animate-spin' : ''}`} /> Tum Uyeleri Degerlendir
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {tiers.map((tier, idx) => {
          const TierIcon = tierIcons[tier.icon] || Shield;
          return (
            <Card key={idx} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1" style={{ backgroundColor: tier.color }} />
              <CardContent className="p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: tier.color + '20' }}>
                    <TierIcon className="w-6 h-6" style={{ color: tier.color }} />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg">{tier.name}</h3>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Min: {tier.min_points.toLocaleString()} puan</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 mb-3">
                  <Badge variant="outline">{tier.multiplier}x Carpan</Badge>
                  <Badge variant="outline" className="capitalize">{tier.slug}</Badge>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-medium text-[hsl(var(--muted-foreground))]">Avantajlar:</p>
                  {(tier.benefits || []).map((b, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-xs">
                      <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0" />
                      <span>{b}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ============ REWARDS TAB ============
function RewardsTab({ slug }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['rewards-enhanced', slug],
    queryFn: () => loyaltyEngineAPI.listRewardsEnhanced(slug).then(r => r.data),
    enabled: !!slug,
  });
  const [filter, setFilter] = useState('all');

  const deleteMut = useMutation({
    mutationFn: (id) => loyaltyEngineAPI.deleteRewardEnhanced(slug, id),
    onSuccess: () => { qc.invalidateQueries(['rewards-enhanced']); toast.success('Odul silindi'); },
  });

  if (isLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;

  const rewards = data?.data || [];
  const categories = [...new Set(rewards.map(r => r.category))];
  const filtered = filter === 'all' ? rewards : rewards.filter(r => r.category === filter);

  const catIcons = { konaklama: Bed, spa: Sparkles, restoran: Utensils, partner: Plane, hizmet: Clock, sezonsal: Sun, ozel: Crown, genel: Gift };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant={filter === 'all' ? 'default' : 'outline'} onClick={() => setFilter('all')}>Tumu ({rewards.length})</Button>
        {categories.map(c => (
          <Button key={c} size="sm" variant={filter === c ? 'default' : 'outline'} onClick={() => setFilter(c)} className="capitalize">{c}</Button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map(reward => {
          const CatIcon = catIcons[reward.category] || Gift;
          const tierColors = { bronze: '#CD7F32', silver: '#C0C0C0', gold: '#FFD700', platinum: '#E5E4E2' };
          return (
            <Card key={reward.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center">
                      <CatIcon className="w-5 h-5 text-[hsl(var(--primary))]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">{reward.name}</h3>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{reward.description}</p>
                    </div>
                  </div>
                  <Button size="sm" variant="ghost" className="text-red-400" onClick={() => deleteMut.mutate(reward.id)}><Trash2 className="w-3 h-3" /></Button>
                </div>
                <div className="flex flex-wrap gap-1 mb-2">
                  <Badge className="text-xs bg-yellow-500/20 text-yellow-300">{reward.points_cost} puan</Badge>
                  <Badge variant="outline" className="text-xs capitalize" style={{ borderColor: tierColors[reward.min_tier] }}>Min: {reward.min_tier}</Badge>
                  {reward.is_partner && <Badge className="text-xs bg-blue-500/20 text-blue-300">{reward.partner_name}</Badge>}
                  {reward.is_seasonal && <Badge className="text-xs bg-orange-500/20 text-orange-300">{reward.season}</Badge>}
                </div>
                <div className="flex justify-between text-xs text-[hsl(var(--muted-foreground))]">
                  <span>Stok: {reward.stock === -1 ? 'Sinirsiz' : reward.stock}</span>
                  <span>Kullanildi: {reward.redeemed_count}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ============ CAMPAIGNS TAB ============
function CampaignsTab({ slug }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['loyalty-campaigns', slug],
    queryFn: () => loyaltyEngineAPI.listCampaigns(slug).then(r => r.data),
    enabled: !!slug,
  });

  const deleteMut = useMutation({
    mutationFn: (id) => loyaltyEngineAPI.deleteCampaign(slug, id),
    onSuccess: () => { qc.invalidateQueries(['loyalty-campaigns']); toast.success('Kampanya silindi'); },
  });

  const statusColors = { active: 'bg-green-500/20 text-green-300', draft: 'bg-gray-500/20 text-gray-300', completed: 'bg-blue-500/20 text-blue-300', paused: 'bg-yellow-500/20 text-yellow-300' };
  const typeLabels = { seasonal: 'Sezonsal', birthday: 'Dogum Gunu', win_back: 'Geri Donus', tier_exclusive: 'Seviye Ozel', referral: 'Referral', general: 'Genel' };
  const channelIcons = { email: Mail, sms: MessageSquare, push: Bell, whatsapp: Smartphone, all: Megaphone };

  if (isLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;

  return (
    <div className="space-y-4">
      <div className="grid gap-4">
        {(data?.data || []).map(camp => {
          const ChannelIcon = channelIcons[camp.channel] || Megaphone;
          return (
            <Card key={camp.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center">
                      <ChannelIcon className="w-5 h-5 text-[hsl(var(--primary))]" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{camp.name}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[camp.status] || ''}`}>{camp.status}</span>
                        <Badge variant="outline" className="text-xs">{typeLabels[camp.campaign_type] || camp.campaign_type}</Badge>
                      </div>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">{camp.description}</p>
                    </div>
                  </div>
                  <Button size="sm" variant="ghost" className="text-red-400" onClick={() => deleteMut.mutate(camp.id)}><Trash2 className="w-3 h-3" /></Button>
                </div>
                <div className="flex gap-4 mt-3">
                  {camp.bonus_points > 0 && <Badge variant="outline">+{camp.bonus_points} puan</Badge>}
                  {camp.bonus_multiplier > 1 && <Badge variant="outline">{camp.bonus_multiplier}x carpan</Badge>}
                  {camp.target_tiers?.length > 0 && camp.target_tiers.map(t => <Badge key={t} variant="outline" className="capitalize">{t}</Badge>)}
                </div>
                <div className="grid grid-cols-3 gap-3 mt-3">
                  <div className="text-center p-2 rounded bg-[hsl(var(--secondary))]">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Gonderildi</p>
                    <p className="font-bold">{camp.sent_count}</p>
                  </div>
                  <div className="text-center p-2 rounded bg-[hsl(var(--secondary))]">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Acildi</p>
                    <p className="font-bold">{camp.opened_count}</p>
                  </div>
                  <div className="text-center p-2 rounded bg-[hsl(var(--secondary))]">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Donusum</p>
                    <p className="font-bold">{camp.converted_count}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ============ REFERRAL TAB ============
function ReferralTab({ slug }) {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['referral-stats', slug],
    queryFn: () => loyaltyEngineAPI.getReferralStats(slug).then(r => r.data),
    enabled: !!slug,
  });
  const { data: listData } = useQuery({
    queryKey: ['referral-list', slug],
    queryFn: () => loyaltyEngineAPI.listReferrals(slug).then(r => r.data),
    enabled: !!slug,
  });

  if (isLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;

  const config = stats?.config || {};
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Toplam Referral" value={stats?.total_referrals || 0} icon={Share2} color="text-blue-400" bg="bg-blue-500/10" />
        <StatCard label="Basarili" value={stats?.successful || 0} icon={CheckCircle} color="text-green-400" bg="bg-green-500/10" />
        <StatCard label="Bekleyen" value={stats?.pending || 0} icon={Clock} color="text-yellow-400" bg="bg-yellow-500/10" />
        <StatCard label="Dagitilan Puan" value={(stats?.total_points_given || 0).toLocaleString()} icon={Star} color="text-purple-400" bg="bg-purple-500/10" />
      </div>

      {/* Config */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-sm">Referral Ayarlari</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div><span className="text-[hsl(var(--muted-foreground))]">Davet Eden Puan:</span> <strong>{config.referrer_points}</strong></div>
            <div><span className="text-[hsl(var(--muted-foreground))]">Davet Edilen Puan:</span> <strong>{config.referee_points}</strong></div>
            <div><span className="text-[hsl(var(--muted-foreground))]">Max Referral:</span> <strong>{config.max_referrals_per_member}</strong></div>
            <div><span className="text-[hsl(var(--muted-foreground))]">Durum:</span> <Badge variant={config.enabled ? 'default' : 'outline'}>{config.enabled ? 'Aktif' : 'Pasif'}</Badge></div>
          </div>
        </CardContent>
      </Card>

      {/* Top Referrers */}
      {stats?.top_referrers?.length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader><CardTitle className="text-sm">En Iyi Davet Edenler</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {stats.top_referrers.map((r, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded bg-[hsl(var(--secondary))]">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold">{i + 1}.</span>
                    <span>{r.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline">{r.referral_count} referral</Badge>
                    <Badge className="bg-yellow-500/20 text-yellow-300">{r.points_earned} puan</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Referral List */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-sm">Son Referrallar</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {(listData?.data || []).map((ref, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-[hsl(var(--secondary))] text-sm">
                <div>
                  <span className="font-medium">{ref.referrer_name}</span>
                  <span className="text-[hsl(var(--muted-foreground))]"> → </span>
                  <span>{ref.referee_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{ref.referral_code}</Badge>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${ref.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}`}>{ref.status}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ============ DIGITAL CARD TAB ============
function DigitalCardTab({ slug }) {
  const { data: members } = useQuery({
    queryKey: ['loyalty-members-v2', slug],
    queryFn: async () => {
      const res = await loyaltyAnalyticsAPI.getSegments(slug);
      return res.data.member_segments || [];
    },
    enabled: !!slug,
  });
  const [selectedMember, setSelectedMember] = useState(null);
  const { data: card } = useQuery({
    queryKey: ['digital-card', slug, selectedMember],
    queryFn: () => loyaltyEngineAPI.getDigitalCard(slug, selectedMember).then(r => r.data),
    enabled: !!slug && !!selectedMember,
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-[hsl(var(--muted-foreground))]">Bir uye secin ve dijital sadakat kartini goruntuleyin</p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {(members || []).map(m => (
          <Button key={m.contact_id} size="sm" variant={selectedMember === m.contact_id ? 'default' : 'outline'}
            onClick={() => setSelectedMember(m.contact_id)}>
            {m.name}
          </Button>
        ))}
      </div>

      {card && (
        <div className="flex justify-center">
          <div className="w-full max-w-md rounded-2xl overflow-hidden shadow-2xl" style={{ background: `linear-gradient(135deg, ${card.tier_color}33, ${card.tier_color}11)` }}>
            <div className="p-6 border border-[hsl(var(--border))] rounded-2xl bg-[hsl(var(--card))/0.9] backdrop-blur">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold">{card.tenant_name}</h3>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Sadakat Karti</p>
                </div>
                <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: card.tier_color + '30' }}>
                  <Crown className="w-6 h-6" style={{ color: card.tier_color }} />
                </div>
              </div>
              <div className="mb-4">
                <p className="text-xl font-bold">{card.member_name}</p>
                <p className="text-sm" style={{ color: card.tier_color }}>{card.tier_name} Uye</p>
              </div>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 rounded-lg bg-[hsl(var(--secondary))]">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Puan</p>
                  <p className="text-2xl font-bold">{card.points_balance?.toLocaleString()}</p>
                </div>
                <div className="p-3 rounded-lg bg-[hsl(var(--secondary))]">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Carpan</p>
                  <p className="text-2xl font-bold">{card.tier_multiplier}x</p>
                </div>
              </div>
              {card.next_tier?.next_tier && (
                <div className="mb-4">
                  <div className="flex justify-between text-xs mb-1">
                    <span>Sonraki: {card.next_tier.next_tier}</span>
                    <span>{card.next_tier.points_needed} puan kaldi</span>
                  </div>
                  <div className="w-full h-2 bg-[hsl(var(--secondary))] rounded-full">
                    <div className="h-full rounded-full" style={{ width: `${card.next_tier.progress}%`, backgroundColor: card.tier_color }} />
                  </div>
                </div>
              )}
              {card.qr_code_base64 && (
                <div className="flex justify-center">
                  <img src={`data:image/png;base64,${card.qr_code_base64}`} alt="QR Code" className="w-32 h-32 rounded-lg" />
                </div>
              )}
              <div className="mt-3 flex gap-2 justify-center">
                <Button size="sm" variant="outline" className="text-xs"><Smartphone className="w-3 h-3 mr-1" /> Apple Wallet</Button>
                <Button size="sm" variant="outline" className="text-xs"><CreditCard className="w-3 h-3 mr-1" /> Google Pay</Button>
              </div>
              {card.referral_code && (
                <div className="mt-3 text-center">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Referral Kodu</p>
                  <Badge variant="outline" className="text-sm">{card.referral_code}</Badge>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============ SEGMENTATION TAB ============
function SegmentationTab({ slug }) {
  const { data: rfm, isLoading: rfmLoading } = useQuery({
    queryKey: ['rfm-analysis', slug],
    queryFn: () => loyaltyAnalyticsAPI.getRFM(slug).then(r => r.data),
    enabled: !!slug,
  });
  const { data: segments } = useQuery({
    queryKey: ['ai-segments', slug],
    queryFn: () => loyaltyAnalyticsAPI.getSegments(slug).then(r => r.data),
    enabled: !!slug,
  });
  const { data: churn } = useQuery({
    queryKey: ['churn-analysis', slug],
    queryFn: () => loyaltyAnalyticsAPI.getChurn(slug).then(r => r.data),
    enabled: !!slug,
  });
  const [subTab, setSubTab] = useState('rfm');

  if (rfmLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {[
          { id: 'rfm', label: 'RFM Analizi' },
          { id: 'segments', label: 'AI Segmentler' },
          { id: 'churn', label: 'Churn Tahmini' },
          { id: 'clv', label: 'CLV Analizi' },
        ].map(t => (
          <Button key={t.id} size="sm" variant={subTab === t.id ? 'default' : 'outline'} onClick={() => setSubTab(t.id)}>{t.label}</Button>
        ))}
      </div>

      {subTab === 'rfm' && rfm && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Ort. Recency (gun)" value={rfm.avg_rfm?.avg_recency || 0} icon={Clock} color="text-blue-400" bg="bg-blue-500/10" />
            <StatCard label="Ort. Frequency" value={rfm.avg_rfm?.avg_frequency || 0} icon={Zap} color="text-green-400" bg="bg-green-500/10" />
            <StatCard label="Ort. Monetary" value={rfm.avg_rfm?.avg_monetary || 0} icon={Star} color="text-yellow-400" bg="bg-yellow-500/10" />
          </div>
          {/* Segment Distribution */}
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-sm">RFM Segment Dagilimi</CardTitle></CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                {Object.entries(rfm.segment_distribution || {}).map(([seg, count]) => {
                  const segColors = { 'Sampiyon': 'bg-green-500/20 text-green-300', 'Sadik Musteri': 'bg-blue-500/20 text-blue-300', 'Yuksek Harcama': 'bg-purple-500/20 text-purple-300', 'Yeni Musteri': 'bg-cyan-500/20 text-cyan-300', 'Risk Altinda': 'bg-yellow-500/20 text-yellow-300', 'Kayip': 'bg-red-500/20 text-red-300' };
                  return (
                    <div key={seg} className={`px-4 py-2 rounded-lg ${segColors[seg] || 'bg-gray-500/20 text-gray-300'}`}>
                      <span className="font-medium">{seg}</span> <Badge variant="outline" className="ml-1">{count}</Badge>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
          {/* Member RFM Table */}
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-sm">Uye RFM Skorlari</CardTitle></CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[hsl(var(--muted-foreground))]">
                      <th className="p-2">Uye</th><th className="p-2">R</th><th className="p-2">F</th><th className="p-2">M</th><th className="p-2">Toplam</th><th className="p-2">Segment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(rfm.data || []).map((m, i) => (
                      <tr key={i} className="border-t border-[hsl(var(--border))]">
                        <td className="p-2 font-medium">{m.name}</td>
                        <td className="p-2">{m.r_score}</td>
                        <td className="p-2">{m.f_score}</td>
                        <td className="p-2">{m.m_score}</td>
                        <td className="p-2 font-bold">{m.total_score}</td>
                        <td className="p-2"><Badge variant="outline">{m.segment}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {subTab === 'segments' && segments && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {Object.entries(segments.segments || {}).map(([name, data]) => (
              <Card key={name} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4 text-center">
                  <div className="w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center" style={{ backgroundColor: data.color + '20' }}>
                    <Users className="w-5 h-5" style={{ color: data.color }} />
                  </div>
                  <h3 className="font-bold text-sm">{name}</h3>
                  <p className="text-2xl font-bold">{data.count}</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{data.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          {/* Personalized Offers */}
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-sm">Kisisellestirilmis Teklif Onerileri</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(segments.personalized_offers || {}).map(([seg, offer]) => (
                  <div key={seg} className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--secondary))]">
                    <span className="font-medium">{seg}</span>
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">{offer}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {subTab === 'churn' && churn && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard label="Ort. Churn Skoru" value={churn.avg_churn_score || 0} icon={AlertTriangle} color="text-orange-400" bg="bg-orange-500/10" />
            <StatCard label="Kritik Risk" value={churn.risk_distribution?.kritik || 0} icon={XCircle} color="text-red-400" bg="bg-red-500/10" />
            <StatCard label="Yuksek Risk" value={churn.risk_distribution?.yuksek || 0} icon={AlertTriangle} color="text-yellow-400" bg="bg-yellow-500/10" />
            <StatCard label="Dusuk Risk" value={churn.risk_distribution?.dusuk || 0} icon={CheckCircle} color="text-green-400" bg="bg-green-500/10" />
          </div>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-sm">Churn Risk Detay</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(churn.data || []).map((m, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--secondary))]">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ backgroundColor: m.risk_color + '20' }}>
                        <span className="text-xs font-bold" style={{ color: m.risk_color }}>{m.churn_score}</span>
                      </div>
                      <div>
                        <span className="font-medium">{m.name}</span>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">{m.days_inactive} gun inaktif | Son 90g: {m.recent_activity_90d} islem</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge style={{ backgroundColor: m.risk_color + '20', color: m.risk_color }}>{m.risk_label}</Badge>
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{m.recommended_action}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {subTab === 'clv' && <CLVSubTab slug={slug} />}
    </div>
  );
}

function CLVSubTab({ slug }) {
  const { data: clv, isLoading } = useQuery({
    queryKey: ['clv-analysis', slug],
    queryFn: () => loyaltyAnalyticsAPI.getCLV(slug).then(r => r.data),
    enabled: !!slug,
  });
  if (isLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <StatCard label="Ortalama CLV" value={`${clv?.avg_clv || 0} puan`} icon={TrendingUp} color="text-blue-400" bg="bg-blue-500/10" />
        <StatCard label="Toplam CLV" value={`${(clv?.total_clv || 0).toLocaleString()} puan`} icon={Star} color="text-green-400" bg="bg-green-500/10" />
      </div>
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-sm">Musteri Yasam Boyu Degeri</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[hsl(var(--muted-foreground))]">
                  <th className="p-2">Uye</th><th className="p-2">CLV</th><th className="p-2">Islem</th><th className="p-2">Omur (ay)</th><th className="p-2">Risk</th>
                </tr>
              </thead>
              <tbody>
                {(clv?.data || []).map((m, i) => (
                  <tr key={i} className="border-t border-[hsl(var(--border))]">
                    <td className="p-2 font-medium">{m.name}</td>
                    <td className="p-2 font-bold">{m.clv}</td>
                    <td className="p-2">{m.transaction_count}</td>
                    <td className="p-2">{m.lifespan_months}</td>
                    <td className="p-2"><Badge variant="outline">{m.risk_label}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ============ ANALYTICS TAB ============
function AnalyticsTab({ slug }) {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['loyalty-dashboard', slug],
    queryFn: () => loyaltyAnalyticsAPI.getDashboard(slug).then(r => r.data),
    enabled: !!slug,
  });
  const { data: cohort } = useQuery({
    queryKey: ['cohort-analysis', slug],
    queryFn: () => loyaltyAnalyticsAPI.getCohort(slug).then(r => r.data),
    enabled: !!slug,
  });

  if (isLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;

  const kpis = dashboard?.kpis || {};
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Toplam Uye" value={kpis.total_members || 0} icon={Users} color="text-blue-400" bg="bg-blue-500/10" />
        <StatCard label="Aktif Uye" value={kpis.active_members || 0} icon={Zap} color="text-green-400" bg="bg-green-500/10" subtitle={`${kpis.activity_rate || 0}% aktivite`} />
        <StatCard label="Kazanilan Puan" value={(kpis.points_earned || 0).toLocaleString()} icon={Star} color="text-yellow-400" bg="bg-yellow-500/10" />
        <StatCard label="Harcanan Puan" value={(kpis.points_spent || 0).toLocaleString()} icon={Gift} color="text-purple-400" bg="bg-purple-500/10" />
      </div>

      {/* Daily Activity */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-sm">Gunluk Puan Aktivitesi (Son 30 Gun)</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-end gap-1 h-32">
            {(dashboard?.daily_activity || []).map((day, i) => {
              const maxPts = Math.max(1, ...dashboard.daily_activity.map(d => d.points_earned));
              const height = (day.points_earned / maxPts) * 100;
              return (
                <div key={i} className="flex-1 flex flex-col items-center justify-end" title={`${day.date}: ${day.points_earned} puan`}>
                  <div className="w-full rounded-t bg-[hsl(var(--primary))]" style={{ height: `${Math.max(2, height)}%`, minHeight: '2px' }} />
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Cohort */}
      {cohort && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader><CardTitle className="text-sm">Kohort Analizi (Yeni vs Geri Donen)</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[hsl(var(--muted-foreground))]">
                    <th className="p-2">Ay</th><th className="p-2">Yeni Uye</th><th className="p-2">Aktif</th><th className="p-2">Geri Donen</th><th className="p-2">Retention</th>
                  </tr>
                </thead>
                <tbody>
                  {(cohort.data || []).map((c, i) => (
                    <tr key={i} className="border-t border-[hsl(var(--border))]">
                      <td className="p-2 font-medium">{c.month}</td>
                      <td className="p-2">{c.new_members}</td>
                      <td className="p-2">{c.active_members}</td>
                      <td className="p-2">{c.returning_members}</td>
                      <td className="p-2"><Badge variant="outline">{c.retention_rate}%</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ============ COMMUNICATION TAB ============
function CommunicationTab({ slug }) {
  const qc = useQueryClient();
  const { data: prefs, isLoading } = useQuery({
    queryKey: ['comm-prefs', slug],
    queryFn: () => loyaltyEngineAPI.getCommPrefs(slug).then(r => r.data),
    enabled: !!slug,
  });
  const updateMut = useMutation({
    mutationFn: (data) => loyaltyEngineAPI.updateCommPrefs(slug, data),
    onSuccess: () => { qc.invalidateQueries(['comm-prefs']); toast.success('Ayarlar guncellendi'); },
  });

  if (isLoading) return <div className="animate-pulse h-48 bg-[hsl(var(--secondary))] rounded-lg" />;

  const togglePref = (key) => {
    updateMut.mutate({ ...prefs, [key]: !prefs[key] });
  };

  const channels = [
    { key: 'email_enabled', label: 'Email', icon: Mail, desc: 'Email ile pazarlama ve bildirimler' },
    { key: 'sms_enabled', label: 'SMS', icon: MessageSquare, desc: 'SMS bildirimleri' },
    { key: 'whatsapp_enabled', label: 'WhatsApp', icon: Smartphone, desc: 'WhatsApp mesajlari' },
    { key: 'push_enabled', label: 'Push', icon: Bell, desc: 'Push bildirimleri' },
    { key: 'inapp_enabled', label: 'In-App', icon: Eye, desc: 'Uygulama ici mesajlar' },
  ];

  const automations = [
    { key: 'birthday_campaign', label: 'Dogum Gunu Kampanyasi', desc: 'Dogum gunlerinde otomatik mesaj ve bonus puan' },
    { key: 'anniversary_campaign', label: 'Yildonumu Kampanyasi', desc: 'Uyelik yildonumlerinde ozel teklif' },
    { key: 'tier_change_notification', label: 'Seviye Degisim Bildirimi', desc: 'Seviye yukseltme/dusurme bildirimler' },
  ];

  return (
    <div className="space-y-4">
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-sm">Iletisim Kanallari</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {channels.map(ch => {
              const Icon = ch.icon;
              const enabled = prefs?.[ch.key];
              return (
                <div key={ch.key} className={`p-4 rounded-lg border cursor-pointer transition-all ${enabled ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]' : 'border-[hsl(var(--border))] bg-[hsl(var(--secondary))]'}`}
                  onClick={() => togglePref(ch.key)}>
                  <div className="flex items-center gap-3">
                    <Icon className={`w-5 h-5 ${enabled ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--muted-foreground))]'}`} />
                    <div>
                      <p className="font-medium text-sm">{ch.label}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{ch.desc}</p>
                    </div>
                    <div className={`ml-auto w-10 h-5 rounded-full flex items-center px-0.5 transition-all ${enabled ? 'bg-[hsl(var(--primary))] justify-end' : 'bg-[hsl(var(--muted))] justify-start'}`}>
                      <div className="w-4 h-4 rounded-full bg-white" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-sm">Otomasyon Ayarlari</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-3">
            {automations.map(auto => {
              const enabled = prefs?.[auto.key];
              return (
                <div key={auto.key} className={`p-4 rounded-lg border cursor-pointer transition-all ${enabled ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]' : 'border-[hsl(var(--border))] bg-[hsl(var(--secondary))]'}`}
                  onClick={() => togglePref(auto.key)}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm">{auto.label}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{auto.desc}</p>
                    </div>
                    <div className={`w-10 h-5 rounded-full flex items-center px-0.5 transition-all ${enabled ? 'bg-[hsl(var(--primary))] justify-end' : 'bg-[hsl(var(--muted))] justify-start'}`}>
                      <div className="w-4 h-4 rounded-full bg-white" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-sm">Zamanlama</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-[hsl(var(--muted-foreground))]">Puan Hatirlatma (gun)</label>
              <p className="text-lg font-bold">{prefs?.points_reminder_days || 30}</p>
            </div>
            <div>
              <label className="text-xs text-[hsl(var(--muted-foreground))]">Inaktif Hatirlatma (gun)</label>
              <p className="text-lg font-bold">{prefs?.inactive_reminder_days || 60}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ============ MAIN PAGE ============
export default function LoyaltyEnginePage() {
  const tenant = useAuthStore((s) => s.tenant);
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Sadakat Programi Motoru</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Puan kurallari, seviye yonetimi, odul katalogu, kampanyalar, referral, analitik ve segmentasyon
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-1 p-1 bg-[hsl(var(--secondary))] rounded-lg">
        {TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-[hsl(var(--background))] text-[hsl(var(--foreground))] shadow-sm'
                  : 'text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && <OverviewTab slug={tenant?.slug} />}
      {activeTab === 'point-rules' && <PointRulesTab slug={tenant?.slug} />}
      {activeTab === 'tiers' && <TiersTab slug={tenant?.slug} />}
      {activeTab === 'rewards' && <RewardsTab slug={tenant?.slug} />}
      {activeTab === 'campaigns' && <CampaignsTab slug={tenant?.slug} />}
      {activeTab === 'referral' && <ReferralTab slug={tenant?.slug} />}
      {activeTab === 'digital-card' && <DigitalCardTab slug={tenant?.slug} />}
      {activeTab === 'segmentation' && <SegmentationTab slug={tenant?.slug} />}
      {activeTab === 'analytics' && <AnalyticsTab slug={tenant?.slug} />}
      {activeTab === 'communication' && <CommunicationTab slug={tenant?.slug} />}
    </div>
  );
}
