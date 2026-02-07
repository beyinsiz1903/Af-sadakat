import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { MessageCircle, Instagram, Star, Award, MessageSquare, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

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

  const { data: connectors = [] } = useQuery({
    queryKey: ['connectors', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/connectors`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Connect your communication channels</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {connectors.map(conn => {
          const Icon = connectorIcons[conn.type] || MessageSquare;
          const color = connectorColors[conn.type] || 'text-gray-400';
          const isActive = conn.type === 'WEBCHAT';

          return (
            <Card key={conn.type} className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] ${isActive ? 'border-[hsl(var(--primary)/0.3)]' : ''}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-11 h-11 rounded-xl bg-[hsl(var(--secondary))] flex items-center justify-center`}>
                      <Icon className={`w-5 h-5 ${color}`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">{conn.label}</h3>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{conn.type}</p>
                    </div>
                  </div>
                  {isActive ? (
                    <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/25 border text-xs">Active</Badge>
                  ) : (
                    <Badge variant="secondary" className="text-xs">Coming Soon</Badge>
                  )}
                </div>

                {isActive ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Enabled</span>
                      <Switch checked={true} disabled />
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Embedded chat widget for your website. Guest QR links include chat access.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Integration ready. Connect your {conn.label} account to receive messages directly in your inbox.</p>
                    <Button variant="outline" size="sm" className="w-full" disabled>
                      <ExternalLink className="w-3 h-3 mr-1" /> Connect (Coming Soon)
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
