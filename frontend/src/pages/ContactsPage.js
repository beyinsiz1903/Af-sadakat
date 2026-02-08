import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import {
  Users, Search, Phone, Mail, Tag, Clock, Gift, Star, MessageSquare,
  ClipboardList, UtensilsCrossed, Send, Download, Plus, Award
} from 'lucide-react';
import { timeAgo, formatDate } from '../lib/utils';
import { toast } from 'sonner';

const eventIcons = {
  MESSAGE_IN: MessageSquare, MESSAGE_OUT: MessageSquare,
  REQUEST_CREATED: ClipboardList, REQUEST_STATUS_CHANGED: ClipboardList,
  ORDER_CREATED: UtensilsCrossed, ORDER_STATUS_CHANGED: UtensilsCrossed,
  LOYALTY_ENROLLED: Gift, LOYALTY_EARNED: Gift, LOYALTY_ADJUSTED: Gift,
  LOYALTY_REDEEMED: Gift, LOYALTY_SPENT: Gift,
  NOTE_ADDED: Tag, CONTACT_LINKED: Users, CONTACT_MERGED: Users,
  REVIEW_RECEIVED: Star, REVIEW_REPLIED: Star,
};
const eventColors = {
  MESSAGE_IN: 'text-blue-400', MESSAGE_OUT: 'text-indigo-400',
  REQUEST_CREATED: 'text-amber-400', REQUEST_STATUS_CHANGED: 'text-amber-400',
  ORDER_CREATED: 'text-pink-400', ORDER_STATUS_CHANGED: 'text-pink-400',
  LOYALTY_ENROLLED: 'text-purple-400', LOYALTY_EARNED: 'text-emerald-400',
  LOYALTY_ADJUSTED: 'text-amber-400', LOYALTY_REDEEMED: 'text-rose-400',
  NOTE_ADDED: 'text-gray-400', CONTACT_LINKED: 'text-blue-400',
};

export default function ContactsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [selectedContact, setSelectedContact] = useState(null);
  const [noteText, setNoteText] = useState('');

  // V2 CRM API
  const { data: contactsData } = useQuery({
    queryKey: ['v2-contacts', tenant?.slug, search],
    queryFn: () => api.get(`/v2/crm/tenants/${tenant?.slug}/contacts`, {
      params: { q: search || undefined, limit: 50 }
    }).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: contactDetail, refetch: refetchDetail } = useQuery({
    queryKey: ['v2-contact-detail', tenant?.slug, selectedContact?.id],
    queryFn: () => api.get(`/v2/crm/tenants/${tenant?.slug}/contacts/${selectedContact?.id}`).then(r => r.data),
    enabled: !!selectedContact?.id && !!tenant?.slug,
  });

  const { data: timeline } = useQuery({
    queryKey: ['v2-contact-timeline', tenant?.slug, selectedContact?.id],
    queryFn: () => api.get(`/v2/crm/tenants/${tenant?.slug}/contacts/${selectedContact?.id}/timeline`).then(r => r.data),
    enabled: !!selectedContact?.id && !!tenant?.slug,
  });

  const noteMutation = useMutation({
    mutationFn: (note) => api.post(`/v2/crm/tenants/${tenant?.slug}/contacts/${selectedContact?.id}/note`, { note }),
    onSuccess: () => { refetchDetail(); setNoteText(''); toast.success('Note added'); queryClient.invalidateQueries(['v2-contact-timeline']); },
  });

  const enrollMutation = useMutation({
    mutationFn: (contactId) => api.post(`/v2/loyalty/tenants/${tenant?.slug}/enroll`, { contact_id: contactId }),
    onSuccess: () => { refetchDetail(); toast.success('Enrolled in loyalty'); },
  });

  const contacts = contactsData?.data || [];
  const events = timeline?.data || [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Contacts</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{contactsData?.total || 0} contacts</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => {
            window.open(`${process.env.REACT_APP_BACKEND_URL}/api/v2/crm/tenants/${tenant?.slug}/export/contacts.csv`, '_blank');
          }} data-testid="export-contacts-btn">
            <Download className="w-4 h-4 mr-1" /> Export CSV
          </Button>
        </div>
      </div>

      <div className="flex gap-4 h-[calc(100vh-220px)]">
        {/* Contact List */}
        <div className="w-full lg:w-1/3 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search contacts..."
              className="pl-9 bg-[hsl(var(--card))]" data-testid="contacts-search" />
          </div>
          <ScrollArea className="h-[calc(100vh-300px)]">
            <div className="space-y-2 pr-2">
              {contacts.map(c => (
                <Card key={c.id} className={`cursor-pointer transition-all hover:border-[hsl(var(--primary)/0.3)] ${
                  selectedContact?.id === c.id ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]' : 'bg-[hsl(var(--card))] border-[hsl(var(--border))]'
                }`} onClick={() => setSelectedContact(c)} data-testid={`contact-card-${c.id}`}>
                  <CardContent className="p-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-[hsl(var(--primary)/0.15)] flex items-center justify-center flex-shrink-0">
                        <span className="text-sm font-semibold text-[hsl(var(--primary))]">{c.name?.charAt(0)?.toUpperCase() || '?'}</span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-sm truncate">{c.name || 'Unknown'}</p>
                          {c.loyalty && (
                            <Badge className="text-[10px] h-4 bg-amber-500/10 text-amber-400">{c.loyalty.tier} {c.loyalty.points}pts</Badge>
                          )}
                        </div>
                        <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">{c.phone || c.email}</p>
                      </div>
                    </div>
                    {c.tags?.length > 0 && (
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {c.tags.map(tag => <Badge key={tag} variant="secondary" className="text-[10px] h-4">{tag}</Badge>)}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* Contact Detail */}
        <div className="hidden lg:block flex-1">
          {contactDetail ? (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] h-full overflow-auto">
              <CardContent className="p-6">
                {/* Header */}
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 rounded-full bg-[hsl(var(--primary)/0.15)] flex items-center justify-center">
                    <span className="text-2xl font-bold text-[hsl(var(--primary))]">{contactDetail.name?.charAt(0)?.toUpperCase()}</span>
                  </div>
                  <div className="flex-1">
                    <h2 className="text-xl font-bold">{contactDetail.name}</h2>
                    <div className="flex items-center gap-4 mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                      {contactDetail.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" /> {contactDetail.phone}</span>}
                      {contactDetail.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" /> {contactDetail.email}</span>}
                    </div>
                  </div>
                  {!contactDetail.loyalty && (
                    <Button size="sm" variant="outline" onClick={() => enrollMutation.mutate(contactDetail.id)} data-testid="enroll-loyalty-btn">
                      <Gift className="w-4 h-4 mr-1" /> Enroll Loyalty
                    </Button>
                  )}
                </div>

                {/* Quick Stats */}
                <div className="grid grid-cols-4 gap-3 mb-6">
                  {[
                    { label: 'Messages', value: contactDetail.summary?.total_messages || 0, icon: MessageSquare },
                    { label: 'Requests', value: contactDetail.summary?.total_requests || 0, icon: ClipboardList },
                    { label: 'Orders', value: contactDetail.summary?.total_orders || 0, icon: UtensilsCrossed },
                    { label: 'Convos', value: contactDetail.summary?.total_conversations || 0, icon: MessageSquare },
                  ].map(s => (
                    <div key={s.label} className="bg-[hsl(var(--secondary))] rounded-lg p-3 text-center">
                      <p className="text-xl font-bold">{s.value}</p>
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{s.label}</p>
                    </div>
                  ))}
                </div>

                {/* Loyalty Card */}
                {contactDetail.loyalty && (
                  <div className="mb-6 p-4 rounded-lg border border-amber-500/20 bg-amber-500/5">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Award className="w-5 h-5 text-amber-400" />
                        <span className="font-semibold">{contactDetail.loyalty.tier_name}</span>
                      </div>
                      <span className="text-lg font-bold">{contactDetail.loyalty.points_balance} pts</span>
                    </div>
                    <div className="w-full bg-[hsl(var(--secondary))] rounded-full h-2">
                      <div className="bg-amber-400 h-2 rounded-full transition-all" style={{width: `${Math.min(contactDetail.loyalty.points_balance / 15, 100)}%`}} />
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Since {formatDate(contactDetail.loyalty.enrolled_at)}</p>
                  </div>
                )}

                <Tabs defaultValue="timeline">
                  <TabsList className="bg-[hsl(var(--secondary))]">
                    <TabsTrigger value="timeline">Timeline</TabsTrigger>
                    <TabsTrigger value="notes">Notes</TabsTrigger>
                  </TabsList>

                  <TabsContent value="timeline" className="mt-4">
                    <ScrollArea className="h-[350px]">
                      <div className="space-y-3">
                        {events.map(e => {
                          const Icon = eventIcons[e.type] || Clock;
                          const color = eventColors[e.type] || 'text-gray-400';
                          return (
                            <div key={e.id} className="flex gap-3 text-sm">
                              <div className="w-8 h-8 rounded-full bg-[hsl(var(--secondary))] flex items-center justify-center flex-shrink-0">
                                <Icon className={`w-4 h-4 ${color}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm">{e.title}</p>
                                {e.body && <p className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-2">{e.body}</p>}
                                <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">{timeAgo(e.created_at)}</p>
                              </div>
                              <Badge variant="secondary" className="text-[10px] h-4 self-start">{e.type.split('_')[0]}</Badge>
                            </div>
                          );
                        })}
                        {events.length === 0 && <p className="text-center py-8 text-[hsl(var(--muted-foreground))]">No activity yet</p>}
                      </div>
                    </ScrollArea>
                  </TabsContent>

                  <TabsContent value="notes" className="mt-4 space-y-3">
                    {contactDetail.notes && (
                      <div className="p-3 bg-[hsl(var(--secondary))] rounded-lg text-sm whitespace-pre-wrap">{contactDetail.notes}</div>
                    )}
                    <div className="flex gap-2">
                      <Input value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="Add a note..." className="bg-[hsl(var(--secondary))]"
                        onKeyDown={(e) => e.key === 'Enter' && noteText.trim() && noteMutation.mutate(noteText)} data-testid="add-note-input" />
                      <Button size="sm" onClick={() => noteText.trim() && noteMutation.mutate(noteText)} disabled={!noteText.trim()} data-testid="add-note-btn">
                        <Send className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ) : (
            <div className="h-full flex items-center justify-center text-[hsl(var(--muted-foreground))]">
              <div className="text-center">
                <Users className="w-14 h-14 mx-auto mb-4 opacity-15" />
                <p className="font-medium">Select a contact</p>
                <p className="text-sm mt-1">View guest memory, timeline, and loyalty</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
