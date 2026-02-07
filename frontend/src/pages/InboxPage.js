import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { conversationsAPI, aiAPI } from '../lib/api';
import api from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Separator } from '../components/ui/separator';
import { MessageSquare, Send, Sparkles, AlertTriangle, User, Bot, Loader2 } from 'lucide-react';
import { timeAgo } from '../lib/utils';
import { toast } from 'sonner';

export default function InboxPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [selectedConv, setSelectedConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const { data: conversations = [], refetch: refetchConvs } = useQuery({
    queryKey: ['conversations', tenant?.slug],
    queryFn: () => conversationsAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
    refetchInterval: 8000,
  });

  // Load messages when conversation selected
  useEffect(() => {
    if (!selectedConv || !tenant?.slug) return;
    const loadMessages = async () => {
      try {
        const { data } = await api.get(`/g/${tenant.slug}/chat/${selectedConv.id}/messages`);
        setMessages(data);
      } catch (e) {
        console.error(e);
      }
    };
    loadMessages();
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, [selectedConv, tenant?.slug]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Get AI suggestion when conversation selected
  useEffect(() => {
    if (!selectedConv || !tenant?.slug) return;
    const lastGuestMsg = [...messages].reverse().find(m => m.sender_type === 'guest');
    if (lastGuestMsg) {
      fetchAiSuggestion(lastGuestMsg.content);
    }
  }, [selectedConv?.id, messages.length]);

  const fetchAiSuggestion = async (message) => {
    setAiLoading(true);
    try {
      const { data } = await aiAPI.suggestReply(tenant?.slug, { message, sector: tenant?.business_type });
      setAiSuggestion(data);
    } catch (e) {
      console.error(e);
    } finally {
      setAiLoading(false);
    }
  };

  const sendMessage = async (content) => {
    if (!content.trim() || !selectedConv) return;
    try {
      await api.post(`/g/${tenant.slug}/chat/${selectedConv.id}/messages`, {
        sender_type: 'agent',
        sender_name: 'Agent',
        content: content.trim(),
      });
      setNewMessage('');
      // Reload messages
      const { data } = await api.get(`/g/${tenant.slug}/chat/${selectedConv.id}/messages`);
      setMessages(data);
      refetchConvs();
    } catch (e) {
      toast.error('Failed to send message');
    }
  };

  const useAiSuggestion = () => {
    if (aiSuggestion?.suggestion) {
      setNewMessage(aiSuggestion.suggestion);
    }
  };

  // WS listener
  useEffect(() => {
    if (!window.__ws) return;
    const unsub = window.__ws.on('message', (data) => {
      if (data.payload?.conversation_id === selectedConv?.id) {
        setMessages(prev => [...prev, data.payload]);
      }
      refetchConvs();
    });
    const unsub2 = window.__ws.on('conversation', () => refetchConvs());
    return () => { unsub(); unsub2(); };
  }, [selectedConv?.id, refetchConvs]);

  return (
    <div className="animate-fade-in h-[calc(100vh-140px)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Inbox</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{conversations.length} conversations</p>
        </div>
      </div>

      <div className="flex gap-4 h-[calc(100%-60px)]">
        {/* Conversation list */}
        <div className="w-80 flex-shrink-0 border-r border-[hsl(var(--border))] pr-4" data-testid="inbox-conversation-list">
          <ScrollArea className="h-full">
            <div className="space-y-2">
              {conversations.map(conv => (
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
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-[hsl(var(--secondary))] flex items-center justify-center">
                          <User className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{conv.guest_name || 'Guest'}</p>
                          <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">{conv.last_message || 'New conversation'}</p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{timeAgo(conv.updated_at)}</span>
                        {conv.needs_attention && <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {conversations.length === 0 && (
                <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No conversations yet</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          {selectedConv ? (
            <>
              {/* Chat header */}
              <div className="pb-3 border-b border-[hsl(var(--border))] flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{selectedConv.guest_name || 'Guest'}</h3>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">WebChat - {selectedConv.status}</p>
                </div>
                {selectedConv.needs_attention && (
                  <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/25 border">
                    <AlertTriangle className="w-3 h-3 mr-1" /> Needs Attention
                  </Badge>
                )}
              </div>

              {/* Messages */}
              <ScrollArea className="flex-1 py-4">
                <div className="space-y-4 pr-4">
                  {messages.map(msg => (
                    <div key={msg.id} className={`flex gap-3 ${msg.sender_type === 'agent' ? 'flex-row-reverse' : ''}`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        msg.sender_type === 'agent' ? 'bg-[hsl(var(--primary)/0.2)]' : 'bg-[hsl(var(--secondary))]'
                      }`}>
                        {msg.sender_type === 'agent' ? <Bot className="w-4 h-4 text-[hsl(var(--primary))]" /> : <User className="w-4 h-4" />}
                      </div>
                      <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 ${
                        msg.sender_type === 'agent'
                          ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                          : 'bg-[hsl(var(--secondary))]'
                      }`}>
                        <p className="text-sm">{msg.content}</p>
                        <p className={`text-[10px] mt-1 ${
                          msg.sender_type === 'agent' ? 'text-white/60' : 'text-[hsl(var(--muted-foreground))]'
                        }`}>{timeAgo(msg.created_at)}</p>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {/* AI Suggestion */}
              {(aiSuggestion || aiLoading) && (
                <div className="py-2 px-3 bg-[hsl(var(--primary)/0.05)] border border-[hsl(var(--primary)/0.2)] rounded-lg mb-2">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
                    <span className="text-xs font-medium text-[hsl(var(--primary))]">AI Suggestion</span>
                    {aiSuggestion && <Badge variant="secondary" className="text-[10px] h-4">{aiSuggestion.intent}</Badge>}
                  </div>
                  {aiLoading ? (
                    <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                      <Loader2 className="w-3 h-3 animate-spin" /> Generating...
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <p className="text-sm flex-1">{aiSuggestion?.suggestion}</p>
                      <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={useAiSuggestion} data-testid="use-ai-suggestion-btn">
                        Use
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Compose */}
              <div className="flex gap-2 pt-2">
                <Input
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type a message..."
                  className="bg-[hsl(var(--secondary))] border-[hsl(var(--border))]"
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage(newMessage)}
                  data-testid="chat-compose-input"
                />
                <Button onClick={() => sendMessage(newMessage)} disabled={!newMessage.trim()} data-testid="chat-compose-send-button">
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-[hsl(var(--muted-foreground))]">
              <div className="text-center">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Select a conversation to start chatting</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
