import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { MessageSquare, Send, Sparkles, AlertTriangle, User, Bot, Loader2, X, Phone, Instagram, Globe, ChevronDown } from 'lucide-react';
import { timeAgo } from '../lib/utils';
import { toast } from 'sonner';

const channelIcons = {
  WEBCHAT: Globe,
  WHATSAPP: Phone,
  INSTAGRAM: Instagram,
};
const channelColors = {
  WEBCHAT: 'text-blue-400',
  WHATSAPP: 'text-emerald-400',
  INSTAGRAM: 'text-pink-400',
};

export default function InboxPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [selectedConv, setSelectedConv] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [channelFilter, setChannelFilter] = useState('all');
  const messagesEndRef = useRef(null);

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
    onError: () => toast.error('Failed to send'),
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
                    onClick={() => { setSelectedConv(conv); setAiSuggestion(null); }}
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
                        <p className="text-sm">{msg.body}</p>
                        <div className={`flex items-center gap-2 mt-1 ${msg.direction === 'OUT' ? 'text-white/50' : 'text-[hsl(var(--muted-foreground))]'}`}>
                          <span className="text-[10px]">{timeAgo(msg.created_at)}</span>
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
                <Button variant="outline" size="icon" className="h-10 w-10 flex-shrink-0" onClick={() => suggestMutation.mutate()} disabled={suggestMutation.isPending} data-testid="ai-suggest-btn">
                  <Sparkles className="w-4 h-4" />
                </Button>
                <Input
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type a message..."
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
    </div>
  );
}
