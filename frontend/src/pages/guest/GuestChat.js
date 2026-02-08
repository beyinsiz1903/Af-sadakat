import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../../lib/api';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { MessageSquare, Send, User, Bot, Loader2, Hotel, CreditCard, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { timeAgo } from '../../lib/utils';

const API_BASE = process.env.REACT_APP_BACKEND_URL;

export default function GuestChat() {
  const { tenantSlug } = useParams();
  const [conversationId, setConversationId] = useState(null);
  const [tenantId, setTenantId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [guestName, setGuestName] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [started, setStarted] = useState(false);
  const [aiTyping, setAiTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Poll for new messages
  useEffect(() => {
    if (!conversationId || !tenantId) return;
    const poll = async () => {
      try {
        const res = await api.get(`/v2/inbox/webchat/${conversationId}/messages`);
        if (res.data) {
          setMessages(res.data);
        }
      } catch (e) {
        // Ignore polling errors
      }
    };
    pollRef.current = setInterval(poll, 4000);
    return () => clearInterval(pollRef.current);
  }, [conversationId, tenantId]);

  const startChat = async () => {
    setLoading(true);
    try {
      const res = await api.post('/v2/inbox/webchat/start', {
        tenantSlug,
        visitorName: guestName || 'Guest',
      });
      setConversationId(res.data.conversationId);
      setTenantId(res.data.tenantId);
      setStarted(true);
    } catch (e) {
      toast.error('Failed to start chat');
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !conversationId || sending) return;
    const content = newMessage.trim();
    setNewMessage('');
    setSending(true);
    setAiTyping(true);

    // Optimistic: add user message immediately
    const tempMsg = {
      id: 'temp-' + Date.now(),
      direction: 'IN',
      body: content,
      meta: { sender_type: 'guest', sender_name: guestName || 'Guest' },
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempMsg]);

    try {
      const res = await api.post(`/v2/inbox/webchat/${conversationId}/messages`, {
        text: content,
        senderName: guestName || 'Guest',
      });

      // Replace temp message with real one
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== tempMsg.id);
        filtered.push({
          id: res.data.id,
          direction: 'IN',
          body: content,
          meta: { sender_type: 'guest' },
          created_at: res.data.created_at,
        });
        return filtered;
      });

      // If AI auto-replied, add the AI message
      if (res.data.ai_reply?.message) {
        const aiMsg = res.data.ai_reply.message;
        setMessages(prev => [...prev, {
          id: aiMsg.id,
          direction: 'OUT',
          body: aiMsg.body,
          meta: aiMsg.meta || { sender_type: 'ai', ai: true },
          created_at: aiMsg.created_at,
        }]);
      }
    } catch (e) {
      toast.error('Failed to send message');
      // Remove temp message on error
      setMessages(prev => prev.filter(m => m.id !== tempMsg.id));
    } finally {
      setSending(false);
      setAiTyping(false);
    }
  };

  // Render message body with payment link detection
  const renderMessageBody = (body) => {
    if (!body) return null;

    // Detect payment links in markdown format [text](url) or plain URLs
    const paymentLinkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+\/pay\/[^\s)]+)\)/g;
    const plainPaymentRegex = /(https?:\/\/[^\s]+\/pay\/[a-f0-9-]+)/g;

    // Check for markdown links first
    const mdMatches = [...body.matchAll(paymentLinkRegex)];
    if (mdMatches.length > 0) {
      const parts = [];
      let lastIndex = 0;
      for (const match of mdMatches) {
        if (match.index > lastIndex) {
          parts.push(<span key={`text-${lastIndex}`}>{body.slice(lastIndex, match.index)}</span>);
        }
        const linkText = match[1];
        const linkUrl = match[2];
        // Extract payment link ID from URL
        const plIdMatch = linkUrl.match(/\/pay\/([a-f0-9-]+)/);
        const payPath = plIdMatch ? `/pay/${plIdMatch[1]}` : linkUrl;
        parts.push(
          <Link key={`link-${match.index}`} to={payPath}
            className="inline-flex items-center gap-1.5 mt-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors no-underline">
            <CreditCard className="w-4 h-4" />
            {linkText}
          </Link>
        );
        lastIndex = match.index + match[0].length;
      }
      if (lastIndex < body.length) {
        parts.push(<span key={`text-end`}>{body.slice(lastIndex)}</span>);
      }
      return <>{parts}</>;
    }

    // Check for plain payment URLs
    const plainMatches = [...body.matchAll(plainPaymentRegex)];
    if (plainMatches.length > 0) {
      const parts = [];
      let lastIndex = 0;
      for (const match of plainMatches) {
        if (match.index > lastIndex) {
          parts.push(<span key={`text-${lastIndex}`}>{body.slice(lastIndex, match.index)}</span>);
        }
        const linkUrl = match[1];
        const plIdMatch = linkUrl.match(/\/pay\/([a-f0-9-]+)/);
        const payPath = plIdMatch ? `/pay/${plIdMatch[1]}` : linkUrl;
        parts.push(
          <Link key={`link-${match.index}`} to={payPath}
            className="inline-flex items-center gap-1.5 mt-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors no-underline">
            <CreditCard className="w-4 h-4" />
            Pay Securely
          </Link>
        );
        lastIndex = match.index + match[0].length;
      }
      if (lastIndex < body.length) {
        parts.push(<span key={`text-end`}>{body.slice(lastIndex)}</span>);
      }
      return <>{parts}</>;
    }

    return body;
  };

  if (!started) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4">
        <div className="max-w-sm w-full">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[hsl(var(--primary))] mb-4">
              <MessageSquare className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold">Chat with us</h1>
            <p className="text-[hsl(var(--muted-foreground))] text-sm mt-2">We're here to help with your booking</p>
          </div>
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Your Name (optional)</label>
                <Input
                  value={guestName}
                  onChange={(e) => setGuestName(e.target.value)}
                  placeholder="Enter your name"
                  className="bg-[hsl(var(--secondary))]"
                  data-testid="guest-chat-name"
                />
              </div>
              <Button className="w-full" onClick={startChat} disabled={loading} data-testid="start-chat-btn">
                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <MessageSquare className="w-4 h-4 mr-2" />}
                Start Chat
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex flex-col">
      {/* Chat header */}
      <div className="bg-[hsl(var(--card))] border-b border-[hsl(var(--border))] px-4 py-3">
        <div className="max-w-md mx-auto flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[hsl(var(--primary))] flex items-center justify-center">
            <Hotel className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-sm">Booking Assistant</h2>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-xs text-[hsl(var(--muted-foreground))]">Online</span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-md mx-auto px-4 py-4 space-y-4">
          {/* Welcome message */}
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-[hsl(var(--secondary))] flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-[hsl(var(--secondary))] rounded-2xl rounded-tl-md px-4 py-2.5 max-w-[85%]">
              <p className="text-sm">Welcome! How can I help you with your booking today? 🏨</p>
            </div>
          </div>

          {messages.map(msg => {
            const isGuest = msg.direction === 'IN' || msg.meta?.sender_type === 'guest';
            const isAI = msg.meta?.ai || msg.meta?.sender_type === 'ai';
            const msgBody = msg.body || msg.content || '';

            return (
              <div key={msg.id} className={`flex gap-3 ${isGuest ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isGuest ? 'bg-[hsl(var(--primary)/0.2)]' : 'bg-[hsl(var(--secondary))]'
                }`}>
                  {isGuest ? (
                    <User className="w-4 h-4 text-[hsl(var(--primary))]" />
                  ) : isAI ? (
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                  ) : (
                    <Bot className="w-4 h-4" />
                  )}
                </div>
                <div className={`rounded-2xl px-4 py-2.5 max-w-[85%] ${
                  isGuest
                    ? 'bg-[hsl(var(--primary))] text-white rounded-tr-md'
                    : 'bg-[hsl(var(--secondary))] rounded-tl-md'
                }`}>
                  {isAI && (
                    <div className="flex items-center gap-1 mb-1">
                      <Badge className="text-[10px] px-1.5 py-0 bg-indigo-600/20 text-indigo-300 border-0">
                        AI Assistant
                      </Badge>
                    </div>
                  )}
                  <div className="text-sm whitespace-pre-wrap">{renderMessageBody(msgBody)}</div>
                  <p className={`text-[10px] mt-1 ${isGuest ? 'text-white/60' : 'text-[hsl(var(--muted-foreground))]'}`}>
                    {timeAgo(msg.created_at)}
                  </p>
                </div>
              </div>
            );
          })}

          {/* AI typing indicator */}
          {aiTyping && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-[hsl(var(--secondary))] flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="bg-[hsl(var(--secondary))] rounded-2xl rounded-tl-md px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Compose */}
      <div className="bg-[hsl(var(--card))] border-t border-[hsl(var(--border))] p-4">
        <div className="max-w-md mx-auto flex gap-2">
          <Input
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type a message..."
            className="bg-[hsl(var(--secondary))]"
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            disabled={sending}
            data-testid="guest-chat-input"
          />
          <Button onClick={sendMessage} disabled={!newMessage.trim() || sending} data-testid="guest-chat-send-btn">
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
