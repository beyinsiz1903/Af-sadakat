import React, { useState, useEffect } from 'react';
import { useGuest } from '../GuestContext';
import { guestAPI } from '../../../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Input } from '../../../components/ui/input';
import { Crown, Star, Gift, Award, Trophy, Flame, QrCode, ChevronRight, Loader2, Check, Lock, ArrowUp, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const tierColors = {
  bronze: { bg: 'bg-amber-900/20', border: 'border-amber-700', text: 'text-amber-500', gradient: 'from-amber-900 to-amber-700' },
  silver: { bg: 'bg-gray-400/20', border: 'border-gray-400', text: 'text-gray-300', gradient: 'from-gray-600 to-gray-400' },
  gold: { bg: 'bg-yellow-500/20', border: 'border-yellow-500', text: 'text-yellow-400', gradient: 'from-yellow-700 to-yellow-500' },
  platinum: { bg: 'bg-purple-400/20', border: 'border-purple-400', text: 'text-purple-300', gradient: 'from-purple-700 to-purple-400' },
};

export default function LoyaltyTab() {
  const { tenantSlug, roomCode, lang, guestName: ctxName, guestPhone: ctxPhone, t } = useGuest();
  const [profile, setProfile] = useState(null);
  const [rewards, setRewards] = useState([]);
  const [badges, setBadges] = useState([]);
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [joined, setJoined] = useState(false);
  const [contactId, setContactId] = useState(null);
  const [showJoinDialog, setShowJoinDialog] = useState(false);
  const [showCardDialog, setShowCardDialog] = useState(false);
  const [showRedeemDialog, setShowRedeemDialog] = useState(null);
  const [joinForm, setJoinForm] = useState({ name: ctxName || '', phone: ctxPhone || '', email: '' });
  const [otpCode, setOtpCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpStub, setOtpStub] = useState('');
  const [joining, setJoining] = useState(false);
  const [redeeming, setRedeeming] = useState(false);
  const [subTab, setSubTab] = useState('overview');
  const [digitalCard, setDigitalCard] = useState(null);

  useEffect(() => {
    (async () => {
      const stored = localStorage.getItem(`loyalty_${tenantSlug}_${roomCode}`);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          setContactId(parsed.contact_id);
          setJoined(true);
          setLoading(false);
          return;
        } catch (e) {}
      }
      // Auto-recognize returning guest by device_token (cross-room)
      const devToken = localStorage.getItem(`omnihub_device_${tenantSlug}`);
      if (devToken) {
        try {
          const res = await guestAPI.resolveDevice(tenantSlug, { device_token: devToken });
          if (res.data?.contact_id) {
            setContactId(res.data.contact_id);
            setJoined(true);
            localStorage.setItem(`loyalty_${tenantSlug}_${roomCode}`,
              JSON.stringify({ contact_id: res.data.contact_id }));
          }
        } catch (e) {
          if (e.response?.status === 410) localStorage.removeItem(`omnihub_device_${tenantSlug}`);
        }
      }
      setLoading(false);
    })();
  }, [tenantSlug, roomCode]);

  useEffect(() => {
    if (joined && contactId) loadProfile();
  }, [joined, contactId]);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const [profRes, rewRes, badgeRes, challRes] = await Promise.all([
        guestAPI.getLoyaltyProfile(tenantSlug, contactId).catch(() => ({ data: null })),
        guestAPI.getLoyaltyRewards(tenantSlug, contactId).catch(() => ({ data: [] })),
        guestAPI.getMyBadges(tenantSlug, contactId).catch(() => ({ data: [] })),
        guestAPI.getMyChallenges(tenantSlug, contactId).catch(() => ({ data: [] })),
      ]);
      setProfile(profRes.data);
      setRewards(Array.isArray(rewRes.data) ? rewRes.data : rewRes.data?.rewards || []);
      setBadges(Array.isArray(badgeRes.data) ? badgeRes.data : badgeRes.data?.badges || []);
      setChallenges(Array.isArray(challRes.data) ? challRes.data : challRes.data?.challenges || []);
    } catch (e) { console.error('Loyalty load error:', e); }
    finally { setLoading(false); }
  };

  const handleSendOtp = async () => {
    if (!joinForm.phone.trim()) return;
    setJoining(true);
    try {
      const res = await guestAPI.sendOtp(tenantSlug, { phone: joinForm.phone });
      setOtpSent(true);
      if (res.data?.otp_stub) setOtpStub(res.data.otp_stub);
      toast.success(t('Verification code sent!', 'Dogrulama kodu gonderildi!'));
    } catch (e) { toast.error(t('Failed to send code', 'Kod gonderilemedi')); }
    finally { setJoining(false); }
  };

  const handleVerifyAndJoin = async () => {
    if (!otpCode.trim() || !joinForm.name.trim()) return;
    setJoining(true);
    try {
      const verifyRes = await guestAPI.verifyOtp(tenantSlug, { phone: joinForm.phone, code: otpCode });
      if (verifyRes.data?.device_token) {
        localStorage.setItem(`omnihub_device_${tenantSlug}`, verifyRes.data.device_token);
      }
      const res = await guestAPI.joinLoyalty(tenantSlug, {
        guest_name: joinForm.name, phone: joinForm.phone, email: joinForm.email, room_code: roomCode
      });
      const cid = res.data?.contact_id;
      if (cid) {
        setContactId(cid);
        setJoined(true);
        localStorage.setItem(`loyalty_${tenantSlug}_${roomCode}`, JSON.stringify({ contact_id: cid }));
        toast.success(t('Welcome to loyalty program!', 'Sadakat programina hosgeldiniz!'));
        setShowJoinDialog(false);
        setOtpSent(false); setOtpCode(''); setOtpStub('');
      }
    } catch (e) {
      const msg = e.response?.data?.detail || t('Verification failed', 'Dogrulama basarisiz');
      toast.error(msg);
    }
    finally { setJoining(false); }
  };

  const handleRedeem = async (reward) => {
    setRedeeming(true);
    try {
      await guestAPI.redeemReward(tenantSlug, { contact_id: contactId, reward_id: reward._id || reward.id });
      toast.success(t('Reward redeemed!', 'Odul kullanildi!'));
      setShowRedeemDialog(null);
      loadProfile();
    } catch (e) { toast.error(t('Failed to redeem', 'Odul kullanilamadi')); }
    finally { setRedeeming(false); }
  };

  const handleShowCard = async () => {
    setShowCardDialog(true);
    try {
      const res = await guestAPI.getDigitalCard(tenantSlug, contactId);
      setDigitalCard(res.data);
    } catch (e) { console.error('Card error:', e); }
  };

  const handleDailyCheckIn = async () => {
    try {
      await guestAPI.dailyCheckIn(tenantSlug, contactId);
      toast.success(t('Daily check-in complete! +10 points', 'Gunluk giris tamamlandi! +10 puan'));
      loadProfile();
    } catch (e) { toast.error(t('Already checked in today', 'Bugun zaten giris yapildi')); }
  };

  if (loading) return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--primary))]" />
    </div>
  );

  if (!joined) return (
    <div className="space-y-4 py-4">
      <Card className="bg-gradient-to-br from-purple-900/40 to-indigo-900/40 border-purple-500/30 overflow-hidden">
        <CardContent className="p-6 text-center relative">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full -mr-10 -mt-10" />
          <Crown className="w-12 h-12 mx-auto mb-3 text-yellow-400" />
          <h2 className="text-xl font-bold mb-2">{t('Loyalty Program', 'Sadakat Programi')}</h2>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
            {t('Earn points with every stay, unlock exclusive rewards and tier benefits.',
               'Her konaklamada puan kazanin, ozel oduller ve katman avantajlarinin kilidini acin.')}
          </p>
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="bg-[hsl(var(--secondary))] rounded-lg p-3">
              <Star className="w-5 h-5 mx-auto mb-1 text-yellow-400" />
              <p className="text-xs font-medium">{t('Earn Points', 'Puan Kazan')}</p>
            </div>
            <div className="bg-[hsl(var(--secondary))] rounded-lg p-3">
              <Gift className="w-5 h-5 mx-auto mb-1 text-emerald-400" />
              <p className="text-xs font-medium">{t('Get Rewards', 'Odul Al')}</p>
            </div>
            <div className="bg-[hsl(var(--secondary))] rounded-lg p-3">
              <Crown className="w-5 h-5 mx-auto mb-1 text-purple-400" />
              <p className="text-xs font-medium">{t('VIP Benefits', 'VIP Avantajlar')}</p>
            </div>
          </div>
          <Button className="w-full" onClick={() => setShowJoinDialog(true)}>
            {t('Join Now - Free', 'Hemen Katil - Ucretsiz')}
          </Button>
        </CardContent>
      </Card>

      <Dialog open={showJoinDialog} onOpenChange={(o) => { setShowJoinDialog(o); if(!o) { setOtpSent(false); setOtpCode(''); setOtpStub(''); } }}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-sm">
          <DialogHeader>
            <DialogTitle>{t('Join Loyalty Program', 'Sadakat Programina Katil')}</DialogTitle>
          </DialogHeader>
          {!otpSent ? (
            <div className="space-y-3">
              <Input placeholder={t('Your Name', 'Adiniz')} value={joinForm.name} onChange={e => setJoinForm({...joinForm, name: e.target.value})} />
              <Input placeholder={t('Phone Number', 'Telefon Numarasi')} type="tel" value={joinForm.phone} onChange={e => setJoinForm({...joinForm, phone: e.target.value})} />
              <Input placeholder={t('Email (optional)', 'E-posta (opsiyonel)')} value={joinForm.email} onChange={e => setJoinForm({...joinForm, email: e.target.value})} />
              <Button className="w-full" disabled={joining || !joinForm.name.trim() || !joinForm.phone.trim()} onClick={handleSendOtp}>
                {joining ? <Loader2 className="w-4 h-4 animate-spin" /> : t('Send Verification Code', 'Dogrulama Kodu Gonder')}
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                {t('Enter the 6-digit code sent to', '6 haneli kodu girin, gonderilen numara:')} <strong>{joinForm.phone}</strong>
              </p>
              {otpStub && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-2 text-xs text-yellow-400 text-center">
                  {t('Demo mode - Code:', 'Demo modu - Kod:')} <strong>{otpStub}</strong>
                </div>
              )}
              <Input placeholder={t('Verification Code', 'Dogrulama Kodu')} value={otpCode} onChange={e => setOtpCode(e.target.value)} maxLength={6} className="text-center text-lg tracking-widest" />
              <Button className="w-full" disabled={joining || otpCode.length < 6} onClick={handleVerifyAndJoin}>
                {joining ? <Loader2 className="w-4 h-4 animate-spin" /> : t('Verify & Join', 'Dogrula ve Katil')}
              </Button>
              <button className="w-full text-xs text-[hsl(var(--muted-foreground))] hover:underline" onClick={() => { setOtpSent(false); setOtpCode(''); setOtpStub(''); }}>
                {t('Change phone number', 'Telefon numarasini degistir')}
              </button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );

  const tier = profile?.tier || { name: 'Bronze', slug: 'bronze' };
  const tc = tierColors[tier.slug] || tierColors.bronze;
  const points = profile?.points_balance || 0;
  const nextTier = profile?.next_tier;
  const progressPct = nextTier ? Math.min(100, ((profile?.total_points || 0) / (nextTier.min_points || 1)) * 100) : 100;
  const activity = profile?.recent_activity || [];

  const subTabs = [
    { id: 'overview', label: t('Overview', 'Genel'), icon: Crown },
    { id: 'rewards', label: t('Rewards', 'Oduller'), icon: Gift },
    { id: 'badges', label: t('Badges', 'Rozetler'), icon: Award },
    { id: 'activity', label: t('Activity', 'Hareketler'), icon: Sparkles },
  ];

  return (
    <div className="space-y-3 py-3">
      <div className={`rounded-xl p-4 bg-gradient-to-r ${tc.gradient} relative overflow-hidden`}>
        <div className="absolute top-0 right-0 w-24 h-24 bg-white/5 rounded-full -mr-6 -mt-6" />
        <div className="absolute bottom-0 left-0 w-16 h-16 bg-white/5 rounded-full -ml-4 -mb-4" />
        <div className="relative z-10 flex items-center justify-between">
          <div>
            <p className="text-xs text-white/70">{t('Your Tier', 'Katmaniniz')}</p>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Crown className="w-5 h-5" /> {tier.name}
            </h3>
          </div>
          <div className="text-right">
            <p className="text-xs text-white/70">{t('Points', 'Puan')}</p>
            <p className="text-2xl font-bold text-white">{points.toLocaleString()}</p>
          </div>
        </div>
        {nextTier && (
          <div className="relative z-10 mt-3">
            <div className="flex items-center justify-between text-xs text-white/70 mb-1">
              <span>{tier.name}</span>
              <span className="flex items-center gap-1"><ArrowUp className="w-3 h-3" /> {nextTier.name} ({nextTier.min_points} pts)</span>
            </div>
            <div className="w-full h-2 bg-white/20 rounded-full">
              <div className="h-2 bg-white rounded-full transition-all duration-500" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        )}
        <div className="relative z-10 flex gap-2 mt-3">
          <Button size="sm" variant="secondary" className="text-xs h-7 bg-white/20 hover:bg-white/30 text-white border-0" onClick={handleShowCard}>
            <QrCode className="w-3 h-3 mr-1" /> {t('Digital Card', 'Dijital Kart')}
          </Button>
          <Button size="sm" variant="secondary" className="text-xs h-7 bg-white/20 hover:bg-white/30 text-white border-0" onClick={handleDailyCheckIn}>
            <Flame className="w-3 h-3 mr-1" /> {t('Daily Check-in', 'Gunluk Giris')}
          </Button>
        </div>
      </div>

      <div className="flex gap-1 bg-[hsl(var(--secondary))] rounded-lg p-1">
        {subTabs.map(st => {
          const Icon = st.icon;
          return (
            <button key={st.id} onClick={() => setSubTab(st.id)}
              className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-md text-xs font-medium transition-colors ${subTab === st.id ? 'bg-[hsl(var(--card))] text-[hsl(var(--foreground))] shadow-sm' : 'text-[hsl(var(--muted-foreground))]'}`}>
              <Icon className="w-3.5 h-3.5" /> {st.label}
            </button>
          );
        })}
      </div>

      {subTab === 'overview' && (
        <div className="space-y-3">
          {tier.benefits && tier.benefits.length > 0 && (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardHeader className="p-3 pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Crown className={`w-4 h-4 ${tc.text}`} /> {t('Your Benefits', 'Avantajlariniz')}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 pt-0">
                <div className="space-y-2">
                  {tier.benefits.map((b, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                      <span>{b}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {challenges.length > 0 && (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardHeader className="p-3 pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Trophy className="w-4 h-4 text-orange-400" /> {t('Active Challenges', 'Aktif Gorevler')}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 pt-0 space-y-2">
                {challenges.slice(0, 3).map((ch, i) => (
                  <div key={i} className="bg-[hsl(var(--secondary))] rounded-lg p-2.5">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium">{ch.title || ch.name}</span>
                      <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{ch.current_progress || 0}/{ch.target || ch.goal || 0}</span>
                    </div>
                    <div className="w-full h-1.5 bg-[hsl(var(--border))] rounded-full">
                      <div className="h-1.5 bg-[hsl(var(--primary))] rounded-full transition-all" style={{ width: `${Math.min(100, ((ch.current_progress || 0) / (ch.target || ch.goal || 1)) * 100)}%` }} />
                    </div>
                    {ch.reward_points && <p className="text-[10px] text-emerald-400 mt-1">+{ch.reward_points} {t('pts', 'puan')}</p>}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {subTab === 'rewards' && (
        <div className="space-y-2">
          {rewards.length === 0 ? (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-6 text-center">
                <Gift className="w-8 h-8 mx-auto mb-2 text-[hsl(var(--muted-foreground))]" />
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{t('No rewards available yet', 'Henuz odul yok')}</p>
              </CardContent>
            </Card>
          ) : rewards.map((rw, i) => {
            const canRedeem = points >= (rw.points_cost || rw.points_required || 0);
            return (
              <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-3 flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${canRedeem ? 'bg-emerald-500/20' : 'bg-[hsl(var(--secondary))]'}`}>
                    <Gift className={`w-5 h-5 ${canRedeem ? 'text-emerald-400' : 'text-[hsl(var(--muted-foreground))]'}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{rw.name || rw.title}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">{rw.description}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs font-bold text-[hsl(var(--primary))]">{(rw.points_cost || rw.points_required || 0).toLocaleString()} pts</p>
                    <Button size="sm" className="text-[10px] h-6 mt-1 px-2" disabled={!canRedeem} onClick={() => setShowRedeemDialog(rw)}>
                      {canRedeem ? <>{t('Redeem', 'Kullan')} <ChevronRight className="w-3 h-3 ml-0.5" /></> : <><Lock className="w-3 h-3 mr-0.5" /> {t('Locked', 'Kilitli')}</>}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {subTab === 'badges' && (
        <div className="grid grid-cols-3 gap-2">
          {badges.length === 0 ? (
            <div className="col-span-3 text-center py-8">
              <Award className="w-8 h-8 mx-auto mb-2 text-[hsl(var(--muted-foreground))]" />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">{t('No badges earned yet', 'Henuz rozet kazanilmadi')}</p>
            </div>
          ) : badges.map((b, i) => (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-3 text-center">
                <div className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center mx-auto mb-1.5">
                  <Award className="w-5 h-5 text-yellow-400" />
                </div>
                <p className="text-[11px] font-medium leading-tight">{b.name || b.title}</p>
                {b.earned_at && <p className="text-[10px] text-emerald-400 mt-0.5">{t('Earned', 'Kazanildi')}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {subTab === 'activity' && (
        <div className="space-y-2">
          {activity.length === 0 ? (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-6 text-center">
                <Sparkles className="w-8 h-8 mx-auto mb-2 text-[hsl(var(--muted-foreground))]" />
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{t('No activity yet', 'Henuz hareket yok')}</p>
              </CardContent>
            </Card>
          ) : activity.map((a, i) => (
            <div key={i} className="flex items-center gap-3 bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${(a.points || 0) >= 0 ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
                <Star className={`w-4 h-4 ${(a.points || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium">{a.description || a.reason || a.type}</p>
                <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{a.created_at ? new Date(a.created_at).toLocaleDateString() : ''}</p>
              </div>
              <span className={`text-sm font-bold ${(a.points || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {(a.points || 0) >= 0 ? '+' : ''}{a.points || 0}
              </span>
            </div>
          ))}
        </div>
      )}

      <Dialog open={!!showRedeemDialog} onOpenChange={() => setShowRedeemDialog(null)}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-sm">
          <DialogHeader>
            <DialogTitle>{t('Redeem Reward', 'Odul Kullan')}</DialogTitle>
          </DialogHeader>
          {showRedeemDialog && (
            <div className="space-y-4">
              <div className="text-center">
                <Gift className="w-10 h-10 mx-auto mb-2 text-emerald-400" />
                <h3 className="font-medium">{showRedeemDialog.name || showRedeemDialog.title}</h3>
                <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{showRedeemDialog.description}</p>
                <p className="text-lg font-bold text-[hsl(var(--primary))] mt-2">{(showRedeemDialog.points_cost || showRedeemDialog.points_required || 0).toLocaleString()} {t('points', 'puan')}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => setShowRedeemDialog(null)}>{t('Cancel', 'Iptal')}</Button>
                <Button className="flex-1" disabled={redeeming} onClick={() => handleRedeem(showRedeemDialog)}>
                  {redeeming ? <Loader2 className="w-4 h-4 animate-spin" /> : t('Confirm', 'Onayla')}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={showCardDialog} onOpenChange={setShowCardDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-sm">
          <DialogHeader>
            <DialogTitle>{t('Digital Loyalty Card', 'Dijital Sadakat Karti')}</DialogTitle>
          </DialogHeader>
          <div className={`rounded-xl p-5 bg-gradient-to-br ${tc.gradient} text-white`}>
            <div className="flex items-center justify-between mb-4">
              <Crown className="w-6 h-6" />
              <span className="text-sm font-bold">{tier.name}</span>
            </div>
            <p className="text-lg font-bold mb-1">{profile?.member_name || ctxName}</p>
            <p className="text-xs text-white/70 mb-4">{t('Member since', 'Uyelik tarihi')}: {profile?.enrollment_date ? new Date(profile.enrollment_date).toLocaleDateString() : '-'}</p>
            {digitalCard?.qr_data && (
              <div className="bg-white rounded-lg p-3 w-32 h-32 mx-auto mb-3 flex items-center justify-center">
                <QrCode className="w-24 h-24 text-gray-800" />
              </div>
            )}
            <div className="text-center">
              <p className="text-2xl font-bold">{points.toLocaleString()} {t('pts', 'puan')}</p>
              {profile?.referral_code && <p className="text-xs text-white/70 mt-1">{t('Referral', 'Referans')}: {profile.referral_code}</p>}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
