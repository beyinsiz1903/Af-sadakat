import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { socialDashboardAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { MessageCircle, Star, TrendingUp, Users, ThumbsUp, ThumbsDown, Minus, Plug } from 'lucide-react';

export default function SocialDashboardPage() {
  const tenant = useAuthStore((s) => s.tenant);

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['social-dashboard', tenant?.slug],
    queryFn: () => socialDashboardAPI.getDashboard(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  if (isLoading || !dashboard) return <div className="p-8 text-center">Loading...</div>;

  const channels = dashboard.channel_stats || {};
  const sentiment = dashboard.sentiment || {};

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Social Media Dashboard</h1>

      {/* Overview KPIs */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Total Conversations', value: dashboard.total_conversations, icon: MessageCircle, color: 'text-blue-400' },
          { label: 'Open Conversations', value: dashboard.open_conversations, icon: Users, color: 'text-amber-400' },
          { label: 'Messages (24h)', value: dashboard.recent_messages_24h, icon: TrendingUp, color: 'text-emerald-400' },
          { label: 'Total Reviews', value: dashboard.total_reviews, icon: Star, color: 'text-yellow-400' },
          { label: 'Avg Rating', value: dashboard.avg_rating, icon: Star, color: 'text-purple-400' },
        ].map((kpi, i) => {
          const Icon = kpi.icon;
          return (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4 text-center">
                <Icon className={`w-5 h-5 mx-auto mb-1 ${kpi.color}`} />
                <p className="text-2xl font-bold">{kpi.value}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">{kpi.label}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Channel Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Object.entries(channels).map(([ch, data]) => (
          <Card key={ch} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold capitalize">{ch}</span>
                <Badge className={ch === 'whatsapp' ? 'bg-green-500/20 text-green-400' : ch === 'instagram' ? 'bg-pink-500/20 text-pink-400' : ch === 'facebook' ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'}>
                  {data.open} open
                </Badge>
              </div>
              <p className="text-xl font-bold">{data.total}</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">total conversations</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Sentiment */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-lg">Review Sentiment</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <ThumbsUp className="w-5 h-5 text-emerald-400" />
              <div>
                <p className="text-xl font-bold text-emerald-400">{sentiment.positive}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Positive</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Minus className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-xl font-bold text-gray-400">{sentiment.neutral}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Neutral</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <ThumbsDown className="w-5 h-5 text-red-400" />
              <div>
                <p className="text-xl font-bold text-red-400">{sentiment.negative}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Negative</p>
              </div>
            </div>
          </div>
          <div className="mt-3 h-3 rounded-full bg-[hsl(var(--secondary))] overflow-hidden flex">
            {(() => { const total = (sentiment.positive||0)+(sentiment.neutral||0)+(sentiment.negative||0); return total > 0 ? (<>
              <div style={{width:`${(sentiment.positive||0)/total*100}%`}} className="bg-emerald-500 h-full" />
              <div style={{width:`${(sentiment.neutral||0)/total*100}%`}} className="bg-gray-500 h-full" />
              <div style={{width:`${(sentiment.negative||0)/total*100}%`}} className="bg-red-500 h-full" />
            </>) : null; })()}
          </div>
        </CardContent>
      </Card>

      {/* Meta Status */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <Plug className="w-5 h-5 text-[hsl(var(--primary))]" />
            <span className="font-medium">Meta Integration</span>
            <Badge className={dashboard.meta_status === 'CONNECTED' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-500/20 text-gray-400'}>
              {dashboard.meta_status}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Review Platform Stats */}
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardHeader><CardTitle className="text-lg">Reviews by Platform</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-4">
            {Object.entries(dashboard.review_stats || {}).map(([platform, count]) => (
              <div key={platform} className="text-center">
                <p className="text-xl font-bold">{count}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] capitalize">{platform}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
