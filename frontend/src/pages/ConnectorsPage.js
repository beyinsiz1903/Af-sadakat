import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import {
  MessageCircle, Instagram, Star, Award, MessageSquare, ExternalLink, RefreshCw, Loader2,
  Clock, Share2, CheckCircle2, XCircle, Copy, Eye, EyeOff, Globe, Phone, Settings, Unplug, Mail, Smartphone
} from 'lucide-react';
import { toast } from 'sonner';
import { timeAgo } from '../lib/utils';
import { platformsAPI } from '../lib/api';

const connectorIcons = {
  WHATSAPP: MessageCircle,
  INSTAGRAM: Instagram,
  GOOGLE_REVIEWS: Star,
  TRIPADVISOR: Award,
  WEBCHAT: MessageSquare,
  META: Share2,
};
const connectorColors = {
  WHATSAPP: 'text-emerald-400',
  INSTAGRAM: 'text-pink-400',
  GOOGLE_REVIEWS: 'text-amber-400',
  TRIPADVISOR: 'text-emerald-400',
  WEBCHAT: 'text-blue-400',
  META: 'text-blue-500',
};

const assetIcons = {
  FB_PAGE: Globe,
  IG_ACCOUNT: Instagram,
  WA_PHONE_NUMBER: Phone,
};
const assetColors = {
  FB_PAGE: 'text-blue-400',
  IG_ACCOUNT: 'text-pink-400',
  WA_PHONE_NUMBER: 'text-emerald-400',
};

export default function ConnectorsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [metaConfigOpen, setMetaConfigOpen] = useState(false);
  const [metaAssetsOpen, setMetaAssetsOpen] = useState(false);
  const [platformConfigOpen, setPlatformConfigOpen] = useState(null);
  const [platformApiKey, setPlatformApiKey] = useState('');
  const [platformPropertyId, setPlatformPropertyId] = useState('');
  const [emailSmsOpen, setEmailSmsOpen] = useState(false);

  const { data: platforms = [] } = useQuery({
    queryKey: ['platforms', tenant?.slug],
    queryFn: () => platformsAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: notifSettings } = useQuery({
    queryKey: ['notif-settings', tenant?.slug],
    queryFn: () => platformsAPI.getNotificationSettings(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const configurePlatform = useMutation({
    mutationFn: ({ platformId, data }) => platformsAPI.configure(tenant?.slug, platformId, data),
    onSuccess: () => { queryClient.invalidateQueries(['platforms']); setPlatformConfigOpen(null); toast.success('Platform configured!'); },
  });

  const disconnectPlatform = useMutation({
    mutationFn: (platformId) => platformsAPI.disconnect(tenant?.slug, platformId),
    onSuccess: () => { queryClient.invalidateQueries(['platforms']); toast.success('Disconnected'); },
  });

  const { data: connectors = [] } = useQuery({
    queryKey: ['connectors', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/connectors`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: metaStatus, refetch: refetchMeta } = useQuery({
    queryKey: ['meta-status', tenant?.slug],
    queryFn: () => api.get(`/v2/integrations/meta/tenants/${tenant?.slug}/status`).then(r => r.data),
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

  // Filter out old WHATSAPP/INSTAGRAM stubs since we have META now
  const filteredConnectors = connectors.filter(c =>
    !['WHATSAPP', 'INSTAGRAM'].includes(c.type) || c.type === 'META'
  );

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
        {/* Meta Integration Card (First) */}
        <MetaCard
          status={metaStatus}
          slug={tenant?.slug}
          onConfigure={() => setMetaConfigOpen(true)}
          onAssets={() => setMetaAssetsOpen(true)}
          onRefresh={refetchMeta}
        />

        {/* Other connectors */}
        {filteredConnectors.map(conn => {
          if (conn.type === 'META') return null;
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
                <div className="space-y-2 mb-3">
                  {isReal ? (
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Embedded chat widget. Messages arrive in real-time.</p>
                  ) : (
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Stub connector returning demo data.</p>
                  )}
                  {conn.configured && conn.credential_id && (
                    <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                      <Clock className="w-3 h-3" />
                      {conn.last_sync_at ? `Last sync: ${timeAgo(conn.last_sync_at)}` : 'Never synced'}
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-[hsl(var(--border))]">
                  <div className="flex items-center gap-2">
                    <Switch checked={isActive} disabled />
                    <span className="text-xs">{isActive ? 'Enabled' : 'Disabled'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* WebChat Widget Embed */}
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

      {/* Meta Config Dialog */}
      <MetaConfigDialog open={metaConfigOpen} onClose={() => { setMetaConfigOpen(false); refetchMeta(); }}
        slug={tenant?.slug} status={metaStatus} />

      {/* Meta Assets Dialog */}
      <MetaAssetsDialog open={metaAssetsOpen} onClose={() => { setMetaAssetsOpen(false); refetchMeta(); }}
        slug={tenant?.slug} status={metaStatus} />
    </div>
  );
}

function MetaCard({ status, slug, onConfigure, onAssets, onRefresh }) {
  const isConnected = status?.connected;
  const enabledAssets = (status?.assets || []).filter(a => a.is_enabled);

  const disconnectMutation = useMutation({
    mutationFn: () => api.post(`/v2/integrations/meta/tenants/${slug}/disconnect`),
    onSuccess: () => { toast.success('Meta disconnected'); onRefresh(); },
    onError: () => toast.error('Failed to disconnect'),
  });

  const oauthMutation = useMutation({
    mutationFn: () => api.post(`/v2/integrations/meta/tenants/${slug}/oauth/start`),
    onSuccess: (res) => {
      window.open(res.data.url, '_blank', 'width=600,height=700');
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to start OAuth'),
  });

  return (
    <Card className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] ${isConnected ? 'border-blue-500/30' : ''}`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
              <Share2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">Meta Platform</h3>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Facebook · Instagram · WhatsApp</p>
            </div>
          </div>
          {isConnected ? (
            <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/25 border text-xs">
              <CheckCircle2 className="w-3 h-3 mr-1" /> Connected
            </Badge>
          ) : status?.status === 'ERROR' ? (
            <Badge className="bg-red-500/10 text-red-400 border-red-500/25 border text-xs">
              <XCircle className="w-3 h-3 mr-1" /> Error
            </Badge>
          ) : (
            <Badge variant="secondary" className="text-xs">Not Connected</Badge>
          )}
        </div>

        <div className="space-y-2 mb-3">
          {isConnected ? (
            <>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {enabledAssets.length} asset(s) enabled. Messages arrive via webhooks.
              </p>
              {enabledAssets.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {enabledAssets.map(a => {
                    const AIcon = assetIcons[a.asset_type] || Globe;
                    return (
                      <Badge key={a.meta_id} className="text-[10px] bg-slate-700 border-0">
                        <AIcon className={`w-2.5 h-2.5 mr-1 ${assetColors[a.asset_type] || ''}`} />
                        {a.display_name?.slice(0, 20)}
                      </Badge>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Connect your Meta Business account to receive messages from Facebook, Instagram, and WhatsApp.
            </p>
          )}
          {status?.last_error && (
            <p className="text-xs text-red-400">Error: {status.last_error.slice(0, 100)}</p>
          )}
        </div>

        <div className="flex gap-2 pt-3 border-t border-[hsl(var(--border))]">
          <Button size="sm" variant="outline" className="text-xs h-8 flex-1" onClick={onConfigure}>
            <Settings className="w-3 h-3 mr-1" /> Configure
          </Button>
          {isConnected ? (
            <>
              <Button size="sm" variant="outline" className="text-xs h-8 flex-1" onClick={onAssets}>
                Assets ({(status?.assets || []).length})
              </Button>
              <Button size="sm" variant="ghost" className="text-xs h-8"
                onClick={() => disconnectMutation.mutate()} disabled={disconnectMutation.isPending}>
                <Unplug className="w-3 h-3 text-red-400" />
              </Button>
            </>
          ) : status?.meta_app_id ? (
            <Button size="sm" className="text-xs h-8 flex-1 bg-blue-600 hover:bg-blue-700"
              onClick={() => oauthMutation.mutate()} disabled={oauthMutation.isPending}>
              {oauthMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <ExternalLink className="w-3 h-3 mr-1" />}
              Connect Meta
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

function MetaConfigDialog({ open, onClose, slug, status }) {
  const [appId, setAppId] = useState(status?.meta_app_id || '');
  const [appSecret, setAppSecret] = useState('');
  const [verifyToken, setVerifyToken] = useState(status?.verify_token || '');
  const [showSecret, setShowSecret] = useState(false);
  const [saving, setSaving] = useState(false);

  React.useEffect(() => {
    if (open) {
      setAppId(status?.meta_app_id || '');
      setVerifyToken(status?.verify_token || '');
      setAppSecret('');
    }
  }, [open, status]);

  const save = async () => {
    setSaving(true);
    try {
      const data = { meta_app_id: appId };
      if (appSecret) data.meta_app_secret = appSecret;
      if (verifyToken) data.meta_verify_token = verifyToken;
      await api.post(`/v2/integrations/meta/tenants/${slug}/configure`, data);
      toast.success('Meta credentials saved');
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save');
    }
    setSaving(false);
  };

  const webhookUrl = status?.webhook_url || `${process.env.REACT_APP_BACKEND_URL}/api/v2/webhooks/meta/${slug}`;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="w-5 h-5 text-blue-400" /> Meta Configuration
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="p-3 bg-blue-900/20 border border-blue-800/30 rounded-lg text-xs text-blue-300">
            <p className="font-medium mb-1">Setup Steps:</p>
            <ol className="list-decimal list-inside space-y-0.5">
              <li>Create a Meta App at developers.facebook.com</li>
              <li>Add Facebook Login, Messenger, Instagram, and WhatsApp products</li>
              <li>Enter App ID and App Secret below</li>
              <li>Set the webhook callback URL and verify token in Meta Dashboard</li>
              <li>Click "Connect Meta" to complete OAuth</li>
            </ol>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Meta App ID</label>
            <Input value={appId} onChange={e => setAppId(e.target.value)}
              placeholder="123456789012345" className="bg-slate-800 border-slate-700" />
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">App Secret</label>
            <div className="relative">
              <Input type={showSecret ? 'text' : 'password'} value={appSecret}
                onChange={e => setAppSecret(e.target.value)}
                placeholder={status?.has_access_token ? '(stored - enter new to update)' : 'Enter app secret'}
                className="bg-slate-800 border-slate-700 pr-10" />
              <button onClick={() => setShowSecret(!showSecret)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white">
                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Webhook Verify Token</label>
            <div className="flex gap-2">
              <Input value={verifyToken} onChange={e => setVerifyToken(e.target.value)}
                className="bg-slate-800 border-slate-700 flex-1" />
              <Button size="sm" variant="ghost" onClick={() => {
                navigator.clipboard.writeText(verifyToken);
                toast.success('Copied!');
              }}>
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Webhook Callback URL</label>
            <div className="flex items-start gap-2">
              <code className="flex-1 block bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs text-emerald-400 font-mono break-all select-all">
                {webhookUrl}
              </code>
              <Button size="sm" variant="ghost" className="mt-0.5 shrink-0" onClick={() => {
                navigator.clipboard.writeText(webhookUrl);
                toast.success('Copied!');
              }}>
                <Copy className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-[10px] text-slate-500 mt-1">Paste this exact URL into Meta Developer Dashboard → Webhooks → Callback URL</p>
          </div>

          <Button onClick={save} disabled={saving || !appId}
            className="w-full bg-blue-600 hover:bg-blue-700">
            {saving ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function MetaAssetsDialog({ open, onClose, slug, status }) {
  const [assets, setAssets] = useState(status?.assets || []);
  const [saving, setSaving] = useState(false);
  const [discovering, setDiscovering] = useState(false);

  React.useEffect(() => {
    if (open) setAssets(status?.assets || []);
  }, [open, status]);

  const discover = async () => {
    setDiscovering(true);
    try {
      const res = await api.post(`/v2/integrations/meta/tenants/${slug}/discover-assets`);
      toast.success(`Discovered ${res.data.discovered} assets`);
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Discovery failed');
    }
    setDiscovering(false);
  };

  const toggleAsset = (idx) => {
    setAssets(prev => prev.map((a, i) => i === idx ? { ...a, is_enabled: !a.is_enabled } : a));
  };

  const saveAssets = async () => {
    setSaving(true);
    try {
      await api.put(`/v2/integrations/meta/tenants/${slug}/assets`, {
        assets: assets.map(a => ({
          asset_type: a.asset_type,
          meta_id: a.meta_id,
          is_enabled: a.is_enabled,
        })),
      });
      toast.success('Assets updated');
      onClose();
    } catch (e) {
      toast.error('Failed to update assets');
    }
    setSaving(false);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-lg">
        <DialogHeader>
          <DialogTitle>Meta Assets</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-slate-400">Enable assets to receive messages/comments</p>
            <Button size="sm" variant="outline" onClick={discover} disabled={discovering}>
              {discovering ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <RefreshCw className="w-3 h-3 mr-1" />}
              Discover
            </Button>
          </div>

          {assets.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <p className="text-sm">No assets found. Click "Discover" to scan your Meta account.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {assets.map((asset, idx) => {
                const AIcon = assetIcons[asset.asset_type] || Globe;
                const color = assetColors[asset.asset_type] || 'text-slate-400';
                return (
                  <div key={asset.meta_id} className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                    <div className="flex items-center gap-3">
                      <AIcon className={`w-5 h-5 ${color}`} />
                      <div>
                        <p className="text-sm font-medium">{asset.display_name}</p>
                        <p className="text-xs text-slate-500">{asset.asset_type} · {asset.meta_id?.slice(0, 12)}...</p>
                      </div>
                    </div>
                    <Switch checked={asset.is_enabled} onCheckedChange={() => toggleAsset(idx)} />
                  </div>
                );
              })}
            </div>
          )}

          {assets.length > 0 && (
            <Button onClick={saveAssets} disabled={saving} className="w-full bg-blue-600 hover:bg-blue-700">
              {saving ? 'Saving...' : 'Save Asset Settings'}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
