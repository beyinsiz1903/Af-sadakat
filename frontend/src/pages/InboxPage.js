import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api, { inboxOffersAPI, offersAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import {
  MessageSquare, Send, Sparkles, AlertTriangle, User, Bot, Loader2, X,
  Phone, Instagram, Globe, Gift, Link2, Copy, ExternalLink, CheckCircle2,
  Image as ImageIcon, Mic, Video, Paperclip, FileText, Plus, Trash2
} from 'lucide-react';
import { timeAgo, formatCurrency } from '../lib/utils';
import { toast } from 'sonner';

const channelIcons = {
  WEBCHAT: Globe,
  WHATSAPP: Phone,
  INSTAGRAM: Instagram,
  FACEBOOK: Globe,
};
const channelColors = {
  WEBCHAT: 'text-blue-400',
  WHATSAPP: 'text-emerald-400',
  INSTAGRAM: 'text-pink-400',
  FACEBOOK: 'text-blue-500',
};

export default function InboxPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const user = useAuthStore((s) => s.user);
  const activePropertyId = useAuthStore((s) => s.activePropertyId);
  const queryClient = useQueryClient();
  const [selectedConv, setSelectedConv] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [channelFilter, setChannelFilter] = useState('all');
  const messagesEndRef = useRef(null);

  // Offer creation state
  const [offerModalOpen, setOfferModalOpen] = useState(false);
  const [createdOffer, setCreatedOffer] = useState(null);
  const [offerForm, setOfferForm] = useState({
    room_type: 'standard', check_in: '', check_out: '',
    price: '', currency: 'TRY', guests_count: '2', notes: ''
  });

  // WhatsApp template picker state
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [templateMgrOpen, setTemplateMgrOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateParams, setTemplateParams] = useState([]);
  const [newTpl, setNewTpl] = useState({ name: '', language: 'en', category: 'UTILITY', body_preview: '', param_count: 0 });

  // Templates list
  const { data: templatesData, refetch: refetchTemplates } = useQuery({
    queryKey: ['wa-templates', tenant?.slug],
    queryFn: () => api.get(`/v2/whatsapp/tenants/${tenant?.slug}/templates`).then(r => r.data),
    enabled: !!tenant?.slug,
  });
  const templates = templatesData || [];

  const createTemplateMutation = useMutation({
    mutationFn: (payload) => api.post(`/v2/whatsapp/tenants/${tenant?.slug}/templates`, payload),
    onSuccess: () => {
      toast.success('Şablon eklendi');
      setNewTpl({ name: '', language: 'en', category: 'UTILITY', body_preview: '', param_count: 0 });
      refetchTemplates();
    },
    onError: () => toast.error('Şablon eklenemedi'),
  });
  const deleteTemplateMutation = useMutation({
    mutationFn: (id) => api.delete(`/v2/whatsapp/tenants/${tenant?.slug}/templates/${id}`),
    onSuccess: () => { toast.success('Silindi'); refetchTemplates(); },
  });
  const sendTemplateMutation = useMutation({
    mutationFn: () => api.post(
      `/v2/whatsapp/tenants/${tenant?.slug}/conversations/${selectedConv?.id}/send-template`,
      {
        template_name: selectedTemplate?.name,
        language: selectedTemplate?.language || 'en',
        parameters: templateParams,
      }
    ),
    onSuccess: () => {
      toast.success('Şablon gönderildi');
      setTemplateModalOpen(false);
      setSelectedTemplate(null);
      setTemplateParams([]);
      refetchDetail();
      refetchConvs();
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Şablon gönderilemedi'),
  });

  // V2 API: list conversations
  const { data: convsData, refetch: refetchConvs } = useQuery({
    queryKey: ['v2-conversations', tenant?.slug, channelFilter],
    queryFn: () => api.get(`/v2/inbox/tenants/${tenant?.slug}/conversations`, {
      params: { channel: channelFilter === 'all' ? undefined : channelFilter, limit: 50 }
    }).then(r => r.data),
    enabled: !!tenant?.slug,
    refetchInterval: 8000,
  });
  const conversations = convsData?.data || [];

  // V2 API: conversation detail
  const { data: convDetail, refetch: refetchDetail } = useQuery({
    queryKey: ['v2-conversation-detail', tenant?.slug, selectedConv?.id],
    queryFn: () => api.get(`/v2/inbox/tenants/${tenant?.slug}/conversations/${selectedConv?.id}`).then(r => r.data),
    enabled: !!selectedConv?.id && !!tenant?.slug,
    refetchInterval: 5000,
  });
  const messages = convDetail?.messages || [];

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages.length]);

  // AI Suggest
  const suggestMutation = useMutation({
    mutationFn: () => api.post(`/v2/inbox/tenants/${tenant?.slug}/conversations/${selectedConv?.id}/ai-suggest`),
    onSuccess: (res) => { setAiSuggestion(res.data); },
    onError: (err) => {
      const detail = err.response?.data?.detail;
      if (detail?.code === 'AI_LIMIT_EXCEEDED') {
        toast.error(detail.message);
      } else {
        toast.error('AI suggestion failed');
      }
    },
  });

  // Send message
  const sendMutation = useMutation({
    mutationFn: (text) => api.post(`/v2/inbox/tenants/${tenant?.slug}/conversations/${selectedConv?.id}/messages`, { text }),
    onSuccess: () => {
      setNewMessage('');
      setAiSuggestion(null);
      refetchDetail();
      refetchConvs();
    },
    onError: (err) => {
      const detail = err.response?.data?.detail;
      if (detail?.code === 'TEMPLATE_REQUIRED') {
        toast.warning('24 saatlik pencere doldu. Şablon mesajı gönderin.');
        setTemplateModalOpen(true);
      } else {
        toast.error('Mesaj gönderilemedi');
      }
    },
  });

  // Close/Reopen
  const closeMutation = useMutation({
    mutationFn: () => api.post(`/v2/inbox/tenants/${tenant?.slug}/conversations/${selectedConv?.id}/close`),
    onSuccess: () => { refetchConvs(); refetchDetail(); toast.success('Conversation closed'); },
  });
  const reopenMutation = useMutation({
    mutationFn: () => api.post(`/v2/inbox/tenants/${tenant?.slug}/conversations/${selectedConv?.id}/reopen`),
    onSuccess: () => { refetchConvs(); refetchDetail(); toast.success('Conversation reopened'); },
  });

  // Create offer from conversation
  const createOfferMutation = useMutation({
    mutationFn: (data) => inboxOffersAPI.createFromConversation(tenant?.slug, selectedConv?.id, data),
    onSuccess: (res) => {
      const offer = res.data?.offer;
      setCreatedOffer(offer);
      toast.success('Offer created from conversation!');
      queryClient.invalidateQueries(['offers-v2']);
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to create offer'),
  });

  // Send offer
  const sendOfferMutation = useMutation({
    mutationFn: (offerId) => offersAPI.send(tenant?.slug, offerId),
    onSuccess: () => {
      toast.success('Offer sent');
      if (createdOffer) setCreatedOffer({ ...createdOffer, status: 'SENT' });
    },
  });

  // Create payment link
  const createPaymentLinkMutation = useMutation({
    mutationFn: (offerId) => offersAPI.createPaymentLink(tenant?.slug, offerId),
    onSuccess: (res) => {
      const url = res.data?.url;
      if (url) {
        navigator.clipboard.writeText(url).then(() => toast.success('Payment link created & copied!')).catch(() => toast.success('Payment link created'));
        if (createdOffer) setCreatedOffer({ ...createdOffer, payment_link: res.data, payment_link_id: res.data?.id, status: 'SENT' });
      }
    },
  });

  // WS listener
  useEffect(() => {
    if (!window.__ws) return;
    const unsub = window.__ws.on('message', (data) => {
      if (data.payload?.conversation_id === selectedConv?.id) refetchDetail();
      refetchConvs();
    });
    const unsub2 = window.__ws.on('conversation', () => refetchConvs());
    return () => { unsub(); unsub2(); };
  }, [selectedConv?.id, refetchConvs, refetchDetail]);

  const handleSend = () => {
    if (newMessage.trim()) sendMutation.mutate(newMessage.trim());
  };

  const handleCreateOffer = () => {
    const guestName = convDetail?.conversation?.guest_name || selectedConv?.guest_name || 'Guest';
    createOfferMutation.mutate({
      property_id: activePropertyId || '',
      room_type: offerForm.room_type,
      check_in: offerForm.check_in,
      check_out: offerForm.check_out,
      price_total: parseFloat(offerForm.price) || 0,
      currency: offerForm.currency,
      guests_count: parseInt(offerForm.guests_count) || 2,
      notes: offerForm.notes,
      guest_name: guestName,
    });
  };

  const resetOfferModal = () => {
    setOfferModalOpen(false);
    setCreatedOffer(null);
    setOfferForm({ room_type: 'standard', check_in: '', check_out: '', price: '', currency: 'TRY', guests_count: '2', notes: '' });
  };

  return (
    <div className="animate-fade-in h-[calc(100vh-140px)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Inbox</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{convsData?.total || 0} conversations</p>
        </div>
        <Select value={channelFilter} onValueChange={setChannelFilter}>
          <SelectTrigger className="w-[160px] bg-[hsl(var(--card))]" data-testid="channel-filter">
            <SelectValue placeholder="All Channels" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Channels</SelectItem>
            <SelectItem value="WEBCHAT">WebChat</SelectItem>
            <SelectItem value="WHATSAPP">WhatsApp</SelectItem>
            <SelectItem value="INSTAGRAM">Instagram</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Create Offer Modal */}
      <Dialog open={offerModalOpen} onOpenChange={(open) => { if (!open) resetOfferModal(); else setOfferModalOpen(true); }}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-lg">
          <DialogHeader>
            <DialogTitle>{createdOffer ? 'Offer Created' : 'Create Offer from Conversation'}</DialogTitle>
          </DialogHeader>

          {!createdOffer ? (
            <div className="space-y-3">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Creating offer for: <span className="font-medium text-[hsl(var(--foreground))]">{convDetail?.conversation?.guest_name || selectedConv?.guest_name || 'Guest'}</span>
              </p>
              <div className="grid grid-cols-3 gap-3">
                <Select value={offerForm.room_type} onValueChange={(v) => setOfferForm({...offerForm, room_type: v})}>
                  <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">Standard</SelectItem>
                    <SelectItem value="deluxe">Deluxe</SelectItem>
                    <SelectItem value="suite">Suite</SelectItem>
                  </SelectContent>
                </Select>
                <Input type="number" value={offerForm.guests_count} onChange={(e) => setOfferForm({...offerForm, guests_count: e.target.value})} placeholder="Guests" className="bg-[hsl(var(--secondary))]" />
                <Select value={offerForm.currency} onValueChange={(v) => setOfferForm({...offerForm, currency: v})}>
                  <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="TRY">TRY</SelectItem>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Check-in</label>
                  <Input type="date" value={offerForm.check_in} onChange={(e) => setOfferForm({...offerForm, check_in: e.target.value})} className="bg-[hsl(var(--secondary))]" />
                </div>
                <div>
                  <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Check-out</label>
                  <Input type="date" value={offerForm.check_out} onChange={(e) => setOfferForm({...offerForm, check_out: e.target.value})} className="bg-[hsl(var(--secondary))]" />
                </div>
              </div>
              <Input type="number" value={offerForm.price} onChange={(e) => setOfferForm({...offerForm, price: e.target.value})} placeholder="Total Price" className="bg-[hsl(var(--secondary))]" />
              <Input value={offerForm.notes} onChange={(e) => setOfferForm({...offerForm, notes: e.target.value})} placeholder="Notes / Inclusions" className="bg-[hsl(var(--secondary))]" />
              <Button onClick={handleCreateOffer} disabled={!offerForm.price || createOfferMutation.isPending} className="w-full" data-testid="inbox-submit-offer-btn">
                {createOfferMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Gift className="w-4 h-4 mr-2" />}
                Create Offer
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-emerald-500/10 border border-emerald-500/25 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span className="font-medium text-emerald-400">Offer Created Successfully</span>
                </div>
                <div className="text-sm space-y-1 text-[hsl(var(--muted-foreground))]">
                  <p>Room: <span className="text-[hsl(var(--foreground))] capitalize">{createdOffer.room_type}</span></p>
                  <p>Dates: {createdOffer.check_in} to {createdOffer.check_out}</p>
                  <p>Price: <span className="font-bold text-[hsl(var(--foreground))]">{formatCurrency(createdOffer.price_total)} {createdOffer.currency}</span></p>
                  <p>Status: <Badge className="bg-gray-500/10 text-gray-400 border-gray-500/25 border text-xs">{createdOffer.status}</Badge></p>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                {createdOffer.status === 'DRAFT' && (
                  <Button onClick={() => sendOfferMutation.mutate(createdOffer.id)} disabled={sendOfferMutation.isPending} variant="outline">
                    <Send className="w-4 h-4 mr-2" /> Send Offer
                  </Button>
                )}
                <Button onClick={() => createPaymentLinkMutation.mutate(createdOffer.id)} disabled={createPaymentLinkMutation.isPending}>
                  <Link2 className="w-4 h-4 mr-2" /> Create Payment Link
                </Button>
                {createdOffer.payment_link?.url && (
                  <div className="flex gap-2">
                    <Button variant="outline" className="flex-1" onClick={() => {
                      navigator.clipboard.writeText(createdOffer.payment_link.url);
                      toast.success('Payment URL copied!');
                    }}>
                      <Copy className="w-4 h-4 mr-2" /> Copy Payment URL
                    </Button>
                    <Button variant="outline" onClick={() => window.open(createdOffer.payment_link.url, '_blank')}>
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                  </div>
                )}
                <Button variant="ghost" onClick={() => { resetOfferModal(); window.location.href = '/offers'; }}>
                  View in Offers Page
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <div className="flex gap-4 h-[calc(100%-60px)]">
        {/* Conversation List */}
        <div className="w-80 flex-shrink-0 border-r border-[hsl(var(--border))] pr-4" data-testid="inbox-conversation-list">
          <ScrollArea className="h-full">
            <div className="space-y-2">
              {conversations.map(conv => {
                const ChannelIcon = channelIcons[conv.channel_type] || Globe;
                const channelColor = channelColors[conv.channel_type] || 'text-gray-400';
                return (
                  <Card
                    key={conv.id}
                    className={`cursor-pointer transition-all hover:border-[hsl(var(--primary)/0.3)] ${
                      selectedConv?.id === conv.id
                        ? 'bg-[hsl(var(--primary)/0.08)] border-[hsl(var(--primary))]'
                        : 'bg-[hsl(var(--card))] border-[hsl(var(--border))]'
                    }`}
                    onClick={() => { setSelectedConv(conv); setAiSuggestion(null); setCreatedOffer(null); }}
                    data-testid={`conversation-${conv.id}`}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-8 h-8 rounded-full bg-[hsl(var(--secondary))] flex items-center justify-center flex-shrink-0">
                            <ChannelIcon className={`w-4 h-4 ${channelColor}`} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium truncate">{conv.guest_name || 'Guest'}</p>
                            <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">{conv.last_message_preview || 'New conversation'}</p>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                          <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{timeAgo(conv.last_message_at)}</span>
                          {conv.needs_attention && <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
                          {conv.message_count > 0 && (
                            <Badge variant="secondary" className="text-[10px] h-4 px-1">{conv.message_count}</Badge>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
              {conversations.length === 0 && (
                <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
                  <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-20" />
                  <p className="text-sm">No conversations yet</p>
                  <p className="text-xs mt-1">Messages from guests and channels will appear here</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {selectedConv ? (
            <>
              {/* Header */}
              <div className="pb-3 border-b border-[hsl(var(--border))] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-[hsl(var(--secondary))] flex items-center justify-center">
                    {React.createElement(channelIcons[convDetail?.conversation?.channel_type || selectedConv.channel_type] || Globe,
                      { className: `w-4 h-4 ${channelColors[convDetail?.conversation?.channel_type || selectedConv.channel_type] || ''}` })}
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm">{convDetail?.conversation?.guest_name || selectedConv.guest_name || 'Guest'}</h3>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-[10px] h-4">{convDetail?.conversation?.channel_type || selectedConv.channel_type}</Badge>
                      <Badge className={`text-[10px] h-4 ${(convDetail?.conversation?.status || selectedConv.status) === 'OPEN' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-gray-500/10 text-gray-400'}`}>
                        {convDetail?.conversation?.status || selectedConv.status}
                      </Badge>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setOfferModalOpen(true)} data-testid="inbox-create-offer-btn">
                    <Gift className="w-3.5 h-3.5 mr-1" /> Create Offer
                  </Button>
                  {(convDetail?.conversation?.status || selectedConv.status) === 'OPEN' ? (
                    <Button size="sm" variant="outline" onClick={() => closeMutation.mutate()} data-testid="close-conv-btn">Close</Button>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => reopenMutation.mutate()}>Reopen</Button>
                  )}
                  {convDetail?.conversation?.needs_attention && (
                    <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/25 border text-xs">
                      <AlertTriangle className="w-3 h-3 mr-1" /> Attention
                    </Badge>
                  )}
                </div>
              </div>

              {/* Messages */}
              <ScrollArea className="flex-1 py-4">
                <div className="space-y-4 pr-4">
                  {messages.map(msg => (
                    <div key={msg.id} className={`flex gap-3 ${msg.direction === 'OUT' ? 'flex-row-reverse' : ''}`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        msg.direction === 'OUT' ? 'bg-[hsl(var(--primary)/0.2)]' : 'bg-[hsl(var(--secondary))]'
                      }`}>
                        {msg.direction === 'OUT' ? <Bot className="w-4 h-4 text-[hsl(var(--primary))]" /> : <User className="w-4 h-4" />}
                      </div>
                      <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 ${
                        msg.direction === 'OUT'
                          ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                          : 'bg-[hsl(var(--secondary))]'
                      }`}>
                        {/* Media attachments (inbound) */}
                        {Array.isArray(msg.meta?.media) && msg.meta.media.length > 0 && (
                          <div className="space-y-2 mb-2">
                            {msg.meta.media.map((m, idx) => {
                              const t = (m.type || '').toLowerCase();
                              const rawUrl = typeof m.url === 'string' ? m.url : '';
                              const safeUrl = (rawUrl.startsWith('http://') || rawUrl.startsWith('https://') || rawUrl.startsWith('/api/')) ? rawUrl : '';
                              if (t === 'image' && safeUrl) {
                                return <img key={idx} src={safeUrl} alt="" className="rounded-lg max-w-full max-h-60 object-cover" />;
                              }
                              if (t === 'video' && safeUrl) {
                                return <video key={idx} src={safeUrl} controls className="rounded-lg max-w-full max-h-60" />;
                              }
                              if (t === 'audio' && safeUrl) {
                                return <audio key={idx} src={safeUrl} controls className="w-full" />;
                              }
                              const Icon = t === 'image' ? ImageIcon : t === 'video' ? Video : t === 'audio' ? Mic : t === 'document' || t === 'file' ? FileText : Paperclip;
                              return (
                                <div key={idx} className="flex items-center gap-2 text-xs opacity-80">
                                  <Icon className="w-3.5 h-3.5" />
                                  {safeUrl ? (
                                    <a href={safeUrl} target="_blank" rel="noreferrer" className="underline">{m.filename || t || 'attachment'}</a>
                                  ) : (
                                    <span>{m.filename || `[${t}]`}{m.mime_type ? ` (${m.mime_type})` : ''}</span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                        {msg.body && <p className="text-sm whitespace-pre-wrap">{msg.body}</p>}
                        <div className={`flex items-center gap-2 mt-1 ${msg.direction === 'OUT' ? 'text-white/50' : 'text-[hsl(var(--muted-foreground))]'}`}>
                          <span className="text-[10px]">{timeAgo(msg.created_at)}</span>
                          {msg.meta?.kind === 'template' && <span className="text-[10px]">• template</span>}
                          {msg.last_updated_by && <span className="text-[10px]">by {msg.last_updated_by}</span>}
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {/* AI Suggestion */}
              {(aiSuggestion || suggestMutation.isPending) && (
                <div className="py-2 px-3 bg-[hsl(var(--primary)/0.05)] border border-[hsl(var(--primary)/0.2)] rounded-lg mb-2">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
                      <span className="text-xs font-medium text-[hsl(var(--primary))]">AI Suggestion</span>
                      {aiSuggestion && <Badge variant="secondary" className="text-[10px] h-4">{aiSuggestion.intent}</Badge>}
                    </div>
                    {aiSuggestion?.usage && (
                      <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{aiSuggestion.usage.used}/{aiSuggestion.usage.limit} used</span>
                    )}
                  </div>
                  {suggestMutation.isPending ? (
                    <div className="flex items-center gap-2 text-xs"><Loader2 className="w-3 h-3 animate-spin" /> Generating...</div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <p className="text-sm flex-1">{aiSuggestion?.suggestion}</p>
                      <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setNewMessage(aiSuggestion?.suggestion || '')} data-testid="use-ai-suggestion-btn">Use</Button>
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setAiSuggestion(null)}><X className="w-3 h-3" /></Button>
                    </div>
                  )}
                </div>
              )}

              {/* Compose */}
              <div className="flex gap-2 pt-2">
                <Button variant="outline" size="icon" className="h-10 w-10 flex-shrink-0" onClick={() => suggestMutation.mutate()} disabled={suggestMutation.isPending} data-testid="ai-suggest-btn" title="AI önerisi">
                  <Sparkles className="w-4 h-4" />
                </Button>
                {selectedConv?.channel_type === 'WHATSAPP' && (
                  <Button variant="outline" size="icon" className="h-10 w-10 flex-shrink-0" onClick={() => setTemplateModalOpen(true)} data-testid="wa-template-btn" title="WhatsApp şablonu gönder">
                    <FileText className="w-4 h-4" />
                  </Button>
                )}
                <Input
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Mesaj yazın..."
                  className="bg-[hsl(var(--secondary))]"
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  data-testid="chat-compose-input"
                />
                <Button onClick={handleSend} disabled={!newMessage.trim() || sendMutation.isPending} data-testid="chat-compose-send-button">
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-[hsl(var(--muted-foreground))]">
              <div className="text-center">
                <MessageSquare className="w-14 h-14 mx-auto mb-4 opacity-15" />
                <p className="font-medium">Select a conversation</p>
                <p className="text-sm mt-1">Choose from the list or wait for new messages</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* WhatsApp Template Picker Dialog */}
      <Dialog open={templateModalOpen} onOpenChange={setTemplateModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between gap-3">
              <span>WhatsApp Şablonu Gönder</span>
              <Button size="sm" variant="ghost" className="h-7" onClick={() => { setTemplateModalOpen(false); setTemplateMgrOpen(true); }}>
                <Plus className="w-3.5 h-3.5 mr-1" /> Yönet
              </Button>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              24 saatlik konuşma penceresi dışındaki misafirler için Meta tarafından önceden onaylanmış bir şablon seçin.
            </p>
            {templates.length === 0 ? (
              <div className="text-center py-6 text-sm text-[hsl(var(--muted-foreground))]">
                Henüz şablon eklenmemiş. "Yönet" butonu ile ekleyebilirsiniz.
              </div>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {templates.map(t => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => {
                      setSelectedTemplate(t);
                      setTemplateParams(Array(t.param_count || 0).fill(''));
                    }}
                    className={`w-full text-left rounded-lg border px-3 py-2 ${selectedTemplate?.id === t.id ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)]' : 'border-[hsl(var(--border))]'}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-sm">{t.name}</span>
                      <Badge variant="secondary" className="text-[10px]">{t.language} • {t.category}</Badge>
                    </div>
                    {t.body_preview && <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{t.body_preview}</p>}
                  </button>
                ))}
              </div>
            )}
            {selectedTemplate && (selectedTemplate.param_count || 0) > 0 && (
              <div className="space-y-2 pt-2 border-t">
                <p className="text-xs font-medium">Parametreler ({selectedTemplate.param_count})</p>
                {templateParams.map((v, i) => (
                  <Input
                    key={i}
                    value={v}
                    onChange={(e) => {
                      const next = [...templateParams]; next[i] = e.target.value; setTemplateParams(next);
                    }}
                    placeholder={`{{${i + 1}}}`}
                  />
                ))}
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setTemplateModalOpen(false)}>İptal</Button>
              <Button
                onClick={() => sendTemplateMutation.mutate()}
                disabled={!selectedTemplate || sendTemplateMutation.isPending || templateParams.some(p => !p?.trim())}
              >
                {sendTemplateMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                Gönder
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Template Manager Dialog */}
      <Dialog open={templateMgrOpen} onOpenChange={setTemplateMgrOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader><DialogTitle>WhatsApp Şablonları</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="rounded-lg border p-3 space-y-2">
              <p className="text-xs font-medium">Yeni Şablon Ekle</p>
              <p className="text-[11px] text-[hsl(var(--muted-foreground))]">
                Şablonu önce Meta Business Manager'da oluşturup onaylatın, sonra burada ad/dil bilgileriyle kayıt ekleyin.
              </p>
              <div className="grid grid-cols-2 gap-2">
                <Input placeholder="Şablon adı (örn. welcome_v1)" value={newTpl.name} onChange={(e) => setNewTpl({ ...newTpl, name: e.target.value })} />
                <Input placeholder="Dil (en, tr, ar, ...)" value={newTpl.language} onChange={(e) => setNewTpl({ ...newTpl, language: e.target.value })} />
                <Select value={newTpl.category} onValueChange={(v) => setNewTpl({ ...newTpl, category: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="UTILITY">UTILITY</SelectItem>
                    <SelectItem value="MARKETING">MARKETING</SelectItem>
                    <SelectItem value="AUTHENTICATION">AUTHENTICATION</SelectItem>
                  </SelectContent>
                </Select>
                <Input type="number" min="0" max="10" placeholder="Parametre sayısı" value={newTpl.param_count} onChange={(e) => setNewTpl({ ...newTpl, param_count: parseInt(e.target.value || '0') })} />
              </div>
              <Input placeholder="Önizleme (gövde metni)" value={newTpl.body_preview} onChange={(e) => setNewTpl({ ...newTpl, body_preview: e.target.value })} />
              <Button size="sm" onClick={() => createTemplateMutation.mutate(newTpl)} disabled={!newTpl.name.trim() || createTemplateMutation.isPending}>
                <Plus className="w-3.5 h-3.5 mr-1" /> Ekle
              </Button>
            </div>
            <div className="space-y-1 max-h-72 overflow-y-auto">
              {templates.map(t => (
                <div key={t.id} className="flex items-center justify-between border rounded px-3 py-2">
                  <div>
                    <p className="text-sm font-medium">{t.name} <span className="text-xs text-[hsl(var(--muted-foreground))]">({t.language} · {t.category} · {t.param_count} param)</span></p>
                    {t.body_preview && <p className="text-xs text-[hsl(var(--muted-foreground))]">{t.body_preview}</p>}
                  </div>
                  <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => deleteTemplateMutation.mutate(t.id)}>
                    <Trash2 className="w-3.5 h-3.5 text-red-500" />
                  </Button>
                </div>
              ))}
              {templates.length === 0 && (
                <p className="text-center text-xs text-[hsl(var(--muted-foreground))] py-3">Henüz şablon yok.</p>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
