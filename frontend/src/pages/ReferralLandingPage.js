import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Gift, MessageSquare, Users, BarChart3, CalendarCheck, Sparkles, ArrowRight, Loader2 } from 'lucide-react';

const featureIcons = {
  0: MessageSquare,
  1: CalendarCheck,
  2: MessageSquare,
  3: Gift,
  4: BarChart3,
};

export default function ReferralLandingPage() {
  const { referralCode } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadReferral();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [referralCode]);

  const loadReferral = async () => {
    try {
      const res = await api.get(`/r/${referralCode}`);
      setData(res.data);
    } catch (e) {
      setError('Referans kodu bulunamadi');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md w-full mx-4">
          <CardContent className="p-8 text-center">
            <p className="text-lg font-semibold text-red-400">{error || 'Bir hata olustu'}</p>
            <Button className="mt-4" variant="outline" onClick={() => window.location.href = '/'}>Ana Sayfaya Don</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4">
      <div className="max-w-lg w-full space-y-6">
        {/* Hero */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[hsl(var(--primary)/0.1)] mb-4">
            <Gift className="w-8 h-8 text-[hsl(var(--primary))]" />
          </div>
          <h1 className="text-3xl font-bold mb-2">Kritik'e Hosgeldiniz!</h1>
          <p className="text-[hsl(var(--muted-foreground))]">{data.message}</p>
        </div>

        {/* Referrer Card */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[hsl(var(--primary)/0.2)] flex items-center justify-center text-lg font-bold text-[hsl(var(--primary))]">
                {(data.referrer_name || 'K')[0]}
              </div>
              <div>
                <p className="font-semibold">{data.referrer_name}</p>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">sizi davet ediyor</p>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-emerald-400" />
                <span className="font-semibold text-emerald-400">{data.reward_amount} Ucretsiz AI Kredi</span>
              </div>
              <p className="text-sm text-emerald-300/80 mt-1">Kaydoldugunuzda hesabiniza tanimlanan</p>
            </div>
          </CardContent>
        </Card>

        {/* Features */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6">
            <h3 className="font-semibold mb-4">Kritik Neler Sunar?</h3>
            <div className="space-y-3">
              {(data.features || []).map((feature, idx) => {
                const Icon = featureIcons[idx] || Sparkles;
                return (
                  <div key={idx} className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[hsl(var(--secondary))] flex items-center justify-center shrink-0">
                      <Icon className="w-4 h-4 text-[hsl(var(--primary))]" />
                    </div>
                    <span className="text-sm">{feature}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* CTA */}
        <Button
          className="w-full h-12 text-base bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.9)]"
          onClick={() => window.location.href = data.cta_url || `/register?ref=${referralCode}`}
        >
          {data.cta_text || 'Ucretsiz Baslayin'} <ArrowRight className="w-5 h-5 ml-2" />
        </Button>

        <p className="text-center text-xs text-[hsl(var(--muted-foreground))]">
          Referans kodu: <Badge variant="outline" className="font-mono text-xs">{referralCode}</Badge>
        </p>
      </div>
    </div>
  );
}
