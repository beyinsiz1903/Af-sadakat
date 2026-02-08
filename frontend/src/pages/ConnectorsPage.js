import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { MessageCircle, Instagram, Star, Award, MessageSquare, ExternalLink, RefreshCw, Loader2, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { timeAgo } from '../lib/utils';

const connectorIcons = {
  WHATSAPP: MessageCircle,
  INSTAGRAM: Instagram,
  GOOGLE_REVIEWS: Star,
  TRIPADVISOR: Award,
  WEBCHAT: MessageSquare,
};
const connectorColors = {
  WHATSAPP: 'text-emerald-400',
  INSTAGRAM: 'text-pink-400',
  GOOGLE_REVIEWS: 'text-amber-400',
  TRIPADVISOR: 'text-emerald-400',
  WEBCHAT: 'text-blue-400',
};

export default function ConnectorsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();

  const { data: connectors = [] } = useQuery({
    queryKey: ['connectors', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/connectors`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const pullMutation = useMutation({
    mutationFn: () => api.post(`/v2/inbox/tenants/${tenant?.slug}/connectors/pull-now`),
    onSuccess: (res) => {
      queryClient.invalidateQueries(['connectors']);
      toast.success(`Synced: ${res.data.messages_created} messages, ${res.data.reviews_created} reviews`);
    },
    onError: () => toast.error('Pull failed'),
  });

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Integrations</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Connect your communication channels</p>
        </div>
        <Button variant="outline" onClick={() => pullMutation.mutate()} disabled={pullMutation.isPending} data-testid="pull-all-btn">
          {pullMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
          Pull All Now
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {connectors.map(conn => {
          const Icon = connectorIcons[conn.type] || MessageSquare;
          const color = connectorColors[conn.type] || 'text-gray-400';
          const isActive = conn.type === 'WEBCHAT' || conn.enabled;
          const isReal = conn.type === 'WEBCHAT';

          return (
            <Card key={conn.type} className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] ${isActive ? 'border-[hsl(var(--primary)/0.2)]' : ''}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-xl bg-[hsl(var(--secondary))] flex items-center justify-center">
                      <Icon className={`w-5 h-5 ${color}`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">{conn.label}</h3>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{conn.type}</p>
                    </div>
                  </div>
                  {isReal ? (
                    <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/25 border text-xs">Active</Badge>
                  ) : conn.enabled ? (
                    <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/25 border text-xs">Stub</Badge>
                  ) : (
                    <Badge variant="secondary" className="text-xs">Disabled</Badge>
                  )}
                </div>

                {/* Status info */}
                <div className="space-y-2 mb-3">
                  {isReal ? (
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Embedded chat widget. Messages arrive in real-time.</p>
                  ) : (
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Stub connector returning demo data. Replace with real API credentials later.</p>
                  )}
                  
                  {conn.configured && conn.credential_id && (
                    <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                      <Clock className="w-3 h-3" />
                      {conn.last_sync_at ? `Last sync: ${timeAgo(conn.last_sync_at)}` : 'Never synced'}
                    </div>
                  )}
                  
                  {conn.status && conn.status !== 'active' && (
                    <Badge variant="secondary" className="text-[10px]">Status: {conn.status}</Badge>
                  )}
                </div>

                {!isReal && (
                  <div className="flex items-center justify-between pt-3 border-t border-[hsl(var(--border))]">
                    <div className="flex items-center gap-2">
                      <Switch checked={conn.enabled} disabled />
                      <span className="text-xs">{conn.enabled ? 'Enabled' : 'Disabled'}</span>
                    </div>
                    <Button variant="outline" size="sm" className="text-xs h-7" disabled>
                      <ExternalLink className="w-3 h-3 mr-1" /> Configure
                    </Button>
                  </div>
                )}

                {isReal && (
                  <div className="pt-3 border-t border-[hsl(var(--border))]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs">Enabled</span>
                      <Switch checked={true} disabled />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
        <CardContent className="p-5">
          <h3 className="font-semibold text-sm mb-2">Embed WebChat Widget</h3>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mb-3">
            Add this script to your website to show a floating chat button:
          </p>
          <code className="block bg-[hsl(var(--secondary))] p-3 rounded-lg text-xs font-mono break-all">
            {`<script src="${process.env.REACT_APP_BACKEND_URL}/api/v2/inbox/webchat/widget.js?tenantSlug=${tenant?.slug}"></script>`}
          </code>
        </CardContent>
      </Card>
    </div>
  );
}
