import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { guestAPI } from '../../lib/api';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { ScrollArea } from '../../components/ui/scroll-area';
import { MessageSquare, Send, User, Bot, Loader2, Hotel } from 'lucide-react';
import { toast } from 'sonner';
import { timeAgo } from '../../lib/utils';
import { WebSocketManager } from '../../lib/websocket';

export default function GuestChat() {
  const { tenantSlug } = useParams();
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [guestName, setGuestName] = useState('');
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.disconnect();
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startChat = async () => {
    setLoading(true);
    try {
      const { data } = await guestAPI.startChat(tenantSlug);
      setConversation(data);
      setStarted(true);

      // Connect WebSocket
      wsRef.current = new WebSocketManager(data.tenant_id);
      wsRef.current.connect();
      wsRef.current.on('message', (event) => {
        if (event.payload?.conversation_id === data.id && event.payload?.sender_type !== 'guest') {
          setMessages(prev => [...prev, event.payload]);
        }
      });
    } catch (e) {
      toast.error('Failed to start chat');
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !conversation) return;
    const content = newMessage.trim();
    setNewMessage('');

    // Optimistic update
    const optimisticMsg = {
      id: Date.now().toString(),
      sender_type: 'guest',
      sender_name: guestName || 'Guest',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, optimisticMsg]);

    try {
      await guestAPI.sendMessage(tenantSlug, conversation.id, {
        sender_type: 'guest',
        sender_name: guestName || 'Guest',
        content,
      });
    } catch (e) {
      toast.error('Failed to send');
    }
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
            <p className="text-[hsl(var(--muted-foreground))] text-sm mt-2">We're here to help during your stay</p>
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
            <h2 className="font-semibold text-sm">Guest Support</h2>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-[hsl(var(--success))]" />
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
            <div className="bg-[hsl(var(--secondary))] rounded-2xl rounded-tl-md px-4 py-2.5 max-w-[80%]">
              <p className="text-sm">Welcome! How can we help you today?</p>
            </div>
          </div>

          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.sender_type === 'guest' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                msg.sender_type === 'guest' ? 'bg-[hsl(var(--primary)/0.2)]' : 'bg-[hsl(var(--secondary))]'
              }`}>
                {msg.sender_type === 'guest' ? <User className="w-4 h-4 text-[hsl(var(--primary))]" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`rounded-2xl px-4 py-2.5 max-w-[80%] ${
                msg.sender_type === 'guest'
                  ? 'bg-[hsl(var(--primary))] text-white rounded-tr-md'
                  : 'bg-[hsl(var(--secondary))] rounded-tl-md'
              }`}>
                <p className="text-sm">{msg.content}</p>
                <p className={`text-[10px] mt-1 ${msg.sender_type === 'guest' ? 'text-white/60' : 'text-[hsl(var(--muted-foreground))]'}`}>
                  {timeAgo(msg.created_at)}
                </p>
              </div>
            </div>
          ))}
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
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            data-testid="guest-chat-input"
          />
          <Button onClick={sendMessage} disabled={!newMessage.trim()} data-testid="guest-chat-send-btn">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
