import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { gamificationAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  Trophy, Medal, Target, Flame, Gift, Crown, Star, Plus, Trash2, Users,
  Award, Zap, TrendingUp, ShieldCheck, Sparkles, Clock, ArrowUpCircle
} from 'lucide-react';

const TABS = [
  { id: 'badges', label: 'Rozetler', icon: Medal },
  { id: 'challenges', label: 'Meydan Okumalar', icon: Target },
  { id: 'leaderboard', label: 'Liderlik Tablosu', icon: Trophy },
  { id: 'rewards', label: 'Odul Katalogu', icon: Gift },
  { id: 'redemptions', label: 'Odul Talepleri', icon: ShieldCheck },
];

const BADGE_ICONS = {
  'calendar-check': '📅', 'message-square': '💬', 'heart': '❤️',
  'sparkles': '✨', 'sunrise': '🌅', 'crown': '👑', 'star': '⭐',
};

export default function GamificationPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('badges');
  const [badgeDialog, setBadgeDialog] = useState(false);
  const [challengeDialog, setChallengeDialog] = useState(false);
  const [rewardDialog, setRewardDialog] = useState(false);
  const [newBadge, setNewBadge] = useState({ name: '', description: '', icon: 'star', color: '#FFD700', category: 'general', points_reward: 50 });
  const [newChallenge, setNewChallenge] = useState({ name: '', description: '', target_event: '', target_value: 1, points_reward: 50 });
  const [newReward, setNewReward] = useState({ name: '', description: '', points_cost: 100, category: 'general', stock: -1 });

  const { data: stats } = useQuery({
    queryKey: ['gamification-stats', tenant?.slug],
    queryFn: () => gamificationAPI.getStats(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: badgesData } = useQuery({
    queryKey: ['gamification-badges', tenant?.slug],
    queryFn: () => gamificationAPI.listBadges(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: challengesData } = useQuery({
    queryKey: ['gamification-challenges', tenant?.slug],
    queryFn: () => gamificationAPI.listChallenges(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: leaderboardData } = useQuery({
    queryKey: ['gamification-leaderboard', tenant?.slug],
    queryFn: () => gamificationAPI.getLeaderboard(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: rewardsData } = useQuery({
    queryKey: ['gamification-rewards', tenant?.slug],
    queryFn: () => gamificationAPI.listRewards(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: redemptionsData } = useQuery({
    queryKey: ['gamification-redemptions', tenant?.slug],
    queryFn: () => gamificationAPI.listRedemptions(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const createBadge = useMutation({
    mutationFn: (data) => gamificationAPI.createBadge(tenant?.slug, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gamification-badges'] }); setBadgeDialog(false); toast.success('Rozet olusturuldu'); setNewBadge({ name: '', description: '', icon: 'star', color: '#FFD700', category: 'general', points_reward: 50 }); },
  });

  const deleteBadge = useMutation({
    mutationFn: (id) => gamificationAPI.deleteBadge(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gamification-badges'] }); toast.success('Rozet silindi'); },
  });

  const createChallenge = useMutation({
    mutationFn: (data) => gamificationAPI.createChallenge(tenant?.slug, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gamification-challenges'] }); setChallengeDialog(false); toast.success('Meydan okuma olusturuldu'); },
  });

  const deleteChallenge = useMutation({
    mutationFn: (id) => gamificationAPI.deleteChallenge(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gamification-challenges'] }); toast.success('Meydan okuma silindi'); },
  });

  const createReward = useMutation({
    mutationFn: (data) => gamificationAPI.createReward(tenant?.slug, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gamification-rewards'] }); setRewardDialog(false); toast.success('Odul olusturuldu'); },
  });

  const deleteReward = useMutation({
    mutationFn: (id) => gamificationAPI.deleteReward(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gamification-rewards'] }); toast.success('Odul silindi'); },
  });

  const updateRedemption = useMutation({
    mutationFn: ({ id, data }) => gamificationAPI.updateRedemption(tenant?.slug, id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gamification-redemptions'] }); toast.success('Durum guncellendi'); },
  });

  const badges = badgesData?.data || [];
  const challenges = challengesData?.data || [];
  const leaderboard = leaderboardData?.data || [];
  const rewards = rewardsData?.data || [];
  const redemptions = redemptionsData?.data || [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Gamification</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Rozetler, meydan okumalar, liderlik tablosu ve odul yonetimi</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Toplam Rozet</p>
                <p className="text-2xl font-bold">{stats?.total_badges || 0}</p>
              </div>
              <Medal className="w-8 h-8 text-amber-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Aktif Challenge</p>
                <p className="text-2xl font-bold">{stats?.active_challenges || 0}</p>
              </div>
              <Target className="w-8 h-8 text-blue-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Odul Cesidi</p>
                <p className="text-2xl font-bold">{stats?.total_rewards || 0}</p>
              </div>
              <Gift className="w-8 h-8 text-emerald-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Kazanilan Rozet</p>
                <p className="text-2xl font-bold">{stats?.total_earned_badges || 0}</p>
              </div>
              <Award className="w-8 h-8 text-purple-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        {TABS.map(t => (
          <Button key={t.id} variant={tab === t.id ? 'default' : 'outline'} size="sm" onClick={() => setTab(t.id)}>
            <t.icon className="w-4 h-4 mr-1" /> {t.label}
          </Button>
        ))}
      </div>

      {/* Badges Tab */}
      {tab === 'badges' && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Rozet Tanimlari</CardTitle>
            <Dialog open={badgeDialog} onOpenChange={setBadgeDialog}>
              <DialogTrigger asChild>
                <Button size="sm"><Plus className="w-4 h-4 mr-1" /> Yeni Rozet</Button>
              </DialogTrigger>
              <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <DialogHeader><DialogTitle>Yeni Rozet Olustur</DialogTitle></DialogHeader>
                <div className="space-y-3">
                  <Input placeholder="Rozet Adi" value={newBadge.name} onChange={e => setNewBadge({...newBadge, name: e.target.value})} />
                  <Input placeholder="Aciklama" value={newBadge.description} onChange={e => setNewBadge({...newBadge, description: e.target.value})} />
                  <div className="flex gap-2">
                    <Input placeholder="Icon" value={newBadge.icon} onChange={e => setNewBadge({...newBadge, icon: e.target.value})} />
                    <Input type="color" value={newBadge.color} onChange={e => setNewBadge({...newBadge, color: e.target.value})} className="w-20" />
                  </div>
                  <div className="flex gap-2">
                    <select className="flex-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm" value={newBadge.category} onChange={e => setNewBadge({...newBadge, category: e.target.value})}>
                      <option value="general">Genel</option>
                      <option value="milestone">Kilometre Tasi</option>
                      <option value="engagement">Katilim</option>
                      <option value="loyalty">Sadakat</option>
                      <option value="experience">Deneyim</option>
                      <option value="behavior">Davranis</option>
                    </select>
                    <Input type="number" placeholder="Puan Odulu" value={newBadge.points_reward} onChange={e => setNewBadge({...newBadge, points_reward: parseInt(e.target.value) || 0})} />
                  </div>
                  <Button onClick={() => createBadge.mutate(newBadge)} disabled={!newBadge.name}>Olustur</Button>
                </div>
              </DialogContent>
            </Dialog>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {badges.map(badge => (
                <div key={badge.id} className="p-4 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary)/0.3)] hover:bg-[hsl(var(--secondary)/0.5)] transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl" style={{ backgroundColor: badge.color + '20' }}>
                        {BADGE_ICONS[badge.icon] || '⭐'}
                      </div>
                      <div>
                        <h3 className="font-semibold">{badge.name}</h3>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">{badge.description}</p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => deleteBadge.mutate(badge.id)}>
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <Badge variant="outline" className="text-[10px]">{badge.category}</Badge>
                    <Badge variant="outline" className="text-[10px]">+{badge.points_reward} puan</Badge>
                  </div>
                </div>
              ))}
            </div>
            {badges.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">Henuz rozet tanimlanmamis</p>}
          </CardContent>
        </Card>
      )}

      {/* Challenges Tab */}
      {tab === 'challenges' && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Meydan Okumalar</CardTitle>
            <Dialog open={challengeDialog} onOpenChange={setChallengeDialog}>
              <DialogTrigger asChild>
                <Button size="sm"><Plus className="w-4 h-4 mr-1" /> Yeni Challenge</Button>
              </DialogTrigger>
              <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <DialogHeader><DialogTitle>Yeni Meydan Okuma Olustur</DialogTitle></DialogHeader>
                <div className="space-y-3">
                  <Input placeholder="Challenge Adi" value={newChallenge.name} onChange={e => setNewChallenge({...newChallenge, name: e.target.value})} />
                  <Input placeholder="Aciklama" value={newChallenge.description} onChange={e => setNewChallenge({...newChallenge, description: e.target.value})} />
                  <div className="flex gap-2">
                    <Input placeholder="Hedef Olay" value={newChallenge.target_event} onChange={e => setNewChallenge({...newChallenge, target_event: e.target.value})} />
                    <Input type="number" placeholder="Hedef Deger" value={newChallenge.target_value} onChange={e => setNewChallenge({...newChallenge, target_value: parseInt(e.target.value) || 1})} className="w-28" />
                  </div>
                  <Input type="number" placeholder="Puan Odulu" value={newChallenge.points_reward} onChange={e => setNewChallenge({...newChallenge, points_reward: parseInt(e.target.value) || 0})} />
                  <Button onClick={() => createChallenge.mutate(newChallenge)} disabled={!newChallenge.name}>Olustur</Button>
                </div>
              </DialogContent>
            </Dialog>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {challenges.map(ch => (
                <div key={ch.id} className="p-4 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary)/0.3)]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                        <Target className="w-5 h-5 text-blue-400" />
                      </div>
                      <div>
                        <h3 className="font-semibold">{ch.name}</h3>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">{ch.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={ch.status === 'active' ? 'default' : 'secondary'}>{ch.status}</Badge>
                      <Button variant="ghost" size="sm" onClick={() => deleteChallenge.mutate(ch.id)}>
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </Button>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center gap-4 text-xs text-[hsl(var(--muted-foreground))]">
                    <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {ch.participants_count} katilimci</span>
                    <span className="flex items-center gap-1"><Trophy className="w-3 h-3" /> {ch.completions_count} tamamlayan</span>
                    <span className="flex items-center gap-1"><Zap className="w-3 h-3" /> +{ch.points_reward} puan</span>
                    <span>Hedef: {ch.target_value}</span>
                  </div>
                  {ch.participants_count > 0 && (
                    <div className="mt-2 w-full bg-[hsl(var(--secondary))] rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full transition-all" style={{ width: `${Math.min(100, (ch.completions_count / ch.participants_count) * 100)}%` }} />
                    </div>
                  )}
                </div>
              ))}
              {challenges.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">Henuz challenge tanimlanmamis</p>}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Leaderboard Tab */}
      {tab === 'leaderboard' && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2"><Trophy className="w-5 h-5 text-amber-400" /> Liderlik Tablosu</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {leaderboard.map((entry, i) => (
                <div key={entry.contact_id} className={`p-4 rounded-lg border flex items-center justify-between ${
                  i === 0 ? 'border-amber-500/50 bg-amber-500/5' :
                  i === 1 ? 'border-gray-400/50 bg-gray-400/5' :
                  i === 2 ? 'border-orange-600/50 bg-orange-600/5' :
                  'border-[hsl(var(--border))] bg-[hsl(var(--secondary)/0.3)]'
                }`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                      i === 0 ? 'bg-amber-500/20 text-amber-400' :
                      i === 1 ? 'bg-gray-400/20 text-gray-300' :
                      i === 2 ? 'bg-orange-600/20 text-orange-400' :
                      'bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))]'
                    }`}>
                      {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${entry.rank}`}
                    </div>
                    <div>
                      <p className="font-semibold">{entry.contact_name}</p>
                      <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                        <Badge variant="outline" className="text-[10px]">{entry.tier}</Badge>
                        <span>{entry.badge_count} rozet</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-bold text-[hsl(var(--primary))]">{entry.points}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">puan</p>
                  </div>
                </div>
              ))}
              {leaderboard.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">Liderlik tablosunda henuz veri yok</p>}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rewards Tab */}
      {tab === 'rewards' && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Odul Katalogu</CardTitle>
            <Dialog open={rewardDialog} onOpenChange={setRewardDialog}>
              <DialogTrigger asChild>
                <Button size="sm"><Plus className="w-4 h-4 mr-1" /> Yeni Odul</Button>
              </DialogTrigger>
              <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <DialogHeader><DialogTitle>Yeni Odul Olustur</DialogTitle></DialogHeader>
                <div className="space-y-3">
                  <Input placeholder="Odul Adi" value={newReward.name} onChange={e => setNewReward({...newReward, name: e.target.value})} />
                  <Input placeholder="Aciklama" value={newReward.description} onChange={e => setNewReward({...newReward, description: e.target.value})} />
                  <div className="flex gap-2">
                    <Input type="number" placeholder="Puan Maliyeti" value={newReward.points_cost} onChange={e => setNewReward({...newReward, points_cost: parseInt(e.target.value) || 0})} />
                    <Input type="number" placeholder="Stok (-1=sinirsiz)" value={newReward.stock} onChange={e => setNewReward({...newReward, stock: parseInt(e.target.value)})} />
                  </div>
                  <select className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm" value={newReward.category} onChange={e => setNewReward({...newReward, category: e.target.value})}>
                    <option value="general">Genel</option>
                    <option value="spa">Spa</option>
                    <option value="room">Oda</option>
                    <option value="service">Hizmet</option>
                    <option value="dining">Yemek</option>
                    <option value="transport">Ulasim</option>
                  </select>
                  <Button onClick={() => createReward.mutate(newReward)} disabled={!newReward.name}>Olustur</Button>
                </div>
              </DialogContent>
            </Dialog>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {rewards.map(reward => (
                <div key={reward.id} className="p-4 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary)/0.3)] hover:bg-[hsl(var(--secondary)/0.5)] transition-colors">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold">{reward.name}</h3>
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{reward.description}</p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => deleteReward.mutate(reward.id)}>
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <Badge className="bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">{reward.points_cost} puan</Badge>
                    <Badge variant="outline" className="text-[10px]">{reward.category}</Badge>
                    <Badge variant="outline" className="text-[10px]">
                      {reward.stock === -1 ? 'Sinirsiz' : `Stok: ${reward.stock}`}
                    </Badge>
                  </div>
                  <p className="text-xs text-[hsl(var(--muted-foreground))] mt-2">{reward.redeemed_count} kez kullanildi</p>
                </div>
              ))}
            </div>
            {rewards.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">Henuz odul tanimlanmamis</p>}
          </CardContent>
        </Card>
      )}

      {/* Redemptions Tab */}
      {tab === 'redemptions' && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader>
            <CardTitle className="text-lg">Odul Talepleri</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {redemptions.map(r => (
                <div key={r.id} className="p-3 rounded-lg border border-[hsl(var(--border))] flex items-center justify-between">
                  <div>
                    <p className="font-medium">{r.reward_name}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{r.contact_id?.substring(0, 8)}... | {r.points_spent} puan | {new Date(r.redeemed_at).toLocaleDateString('tr-TR')}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={r.status === 'fulfilled' ? 'default' : r.status === 'cancelled' ? 'destructive' : 'secondary'}>
                      {r.status === 'pending' ? 'Bekliyor' : r.status === 'fulfilled' ? 'Tamamlandi' : 'Iptal'}
                    </Badge>
                    {r.status === 'pending' && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => updateRedemption.mutate({ id: r.id, data: { status: 'fulfilled' } })}>Onayla</Button>
                        <Button size="sm" variant="ghost" onClick={() => updateRedemption.mutate({ id: r.id, data: { status: 'cancelled' } })}>
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {redemptions.length === 0 && <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">Henuz odul talebi yok</p>}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
