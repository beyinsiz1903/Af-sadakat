import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Share2, MousePointerClick, UserPlus, Gift, Copy, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

export default function GrowthPage() {
  const tenant = useAuthStore((s) => s.tenant);

  const { data: growth } = useQuery({
    queryKey: ['growth', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/growth/stats`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const referralCode = growth?.referral?.code || '';
  const referralUrl = `${window.location.origin}/r/${referralCode}`;

  const copyLink = () => {
    navigator.clipboard.writeText(referralUrl);
    toast.success('Referral link copied!');
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">Growth & Referrals</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Grow your network and earn rewards</p>
      </div>

      {/* Referral Link */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardContent className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-[hsl(var(--primary)/0.1)] flex items-center justify-center">
              <Share2 className="w-6 h-6 text-[hsl(var(--primary))]" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Your Referral Link</h2>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Share with other businesses and earn 50 AI credits per signup</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Input value={referralUrl} readOnly className="bg-[hsl(var(--secondary))] font-mono text-sm" />
            <Button onClick={copyLink} data-testid="copy-referral-link">
              <Copy className="w-4 h-4 mr-2" /> Copy
            </Button>
          </div>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-2">Code: <code className="bg-[hsl(var(--secondary))] px-2 py-0.5 rounded">{referralCode}</code></p>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">Referral Clicks</p>
                <p className="text-3xl font-bold mt-1">{growth?.total_clicks || 0}</p>
              </div>
              <MousePointerClick className="w-8 h-8 text-blue-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">Converted Signups</p>
                <p className="text-3xl font-bold mt-1">{growth?.total_signups || 0}</p>
              </div>
              <UserPlus className="w-8 h-8 text-emerald-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">Earned Rewards</p>
                <p className="text-3xl font-bold mt-1">{growth?.total_rewards || 0}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">AI credits</p>
              </div>
              <Gift className="w-8 h-8 text-amber-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Events */}
      {(growth?.events || []).length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader><CardTitle className="text-lg">Referral Events</CardTitle></CardHeader>
          <CardContent>
            {growth.events.map(e => (
              <div key={e.id} className="flex items-center justify-between py-2">
                <span className="text-sm">New signup via {e.code}</span>
                <Badge className="bg-emerald-500/10 text-emerald-400 text-xs">+{e.reward} credits</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
