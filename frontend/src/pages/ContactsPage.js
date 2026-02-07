import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { contactsAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Users, Search, Phone, Mail, Tag, Clock, ClipboardList, UtensilsCrossed, Gift } from 'lucide-react';
import { timeAgo, formatDate, formatCurrency, statusColors } from '../lib/utils';

export default function ContactsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const [search, setSearch] = useState('');
  const [selectedContact, setSelectedContact] = useState(null);

  const { data: contactsData } = useQuery({
    queryKey: ['contacts', tenant?.slug, search],
    queryFn: () => contactsAPI.list(tenant?.slug, { search: search || undefined, limit: 50 }).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: timeline } = useQuery({
    queryKey: ['contact-timeline', tenant?.slug, selectedContact?.id],
    queryFn: () => contactsAPI.timeline(tenant?.slug, selectedContact?.id).then(r => r.data),
    enabled: !!selectedContact?.id && !!tenant?.slug,
  });

  const contacts = contactsData?.data || [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Contacts</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{contactsData?.total || 0} total contacts</p>
      </div>

      <div className="flex gap-4 h-[calc(100vh-220px)]">
        {/* Contact list */}
        <div className="w-full lg:w-1/3 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search contacts..."
              className="pl-9 bg-[hsl(var(--card))] border-[hsl(var(--border))]"
              data-testid="contacts-search"
            />
          </div>
          <ScrollArea className="h-[calc(100vh-300px)]">
            <div className="space-y-2 pr-2">
              {contacts.map(contact => (
                <Card
                  key={contact.id}
                  className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] cursor-pointer transition-all hover:border-[hsl(var(--primary)/0.3)] ${
                    selectedContact?.id === contact.id ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]' : ''
                  }`}
                  onClick={() => setSelectedContact(contact)}
                  data-testid={`contact-card-${contact.id}`}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-[hsl(var(--primary)/0.15)] flex items-center justify-center flex-shrink-0">
                        <span className="text-sm font-semibold text-[hsl(var(--primary))]">
                          {contact.name?.charAt(0)?.toUpperCase() || '?'}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-sm truncate">{contact.name || 'Unknown'}</p>
                        <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">
                          {contact.phone || contact.email}
                        </p>
                      </div>
                    </div>
                    {contact.tags?.length > 0 && (
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {contact.tags.map(tag => (
                          <Badge key={tag} variant="secondary" className="text-[10px] h-5">{tag}</Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
              {contacts.length === 0 && (
                <div className="text-center py-8 text-sm text-[hsl(var(--muted-foreground))]">No contacts found</div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Contact detail */}
        <div className="hidden lg:block flex-1">
          {selectedContact ? (
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] h-full">
              <CardContent className="p-6">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 rounded-full bg-[hsl(var(--primary)/0.15)] flex items-center justify-center">
                    <span className="text-2xl font-bold text-[hsl(var(--primary))]">
                      {selectedContact.name?.charAt(0)?.toUpperCase() || '?'}
                    </span>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold">{selectedContact.name || 'Unknown'}</h2>
                    <div className="flex items-center gap-4 mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                      {selectedContact.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" /> {selectedContact.phone}</span>}
                      {selectedContact.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" /> {selectedContact.email}</span>}
                    </div>
                  </div>
                </div>

                <div className="flex gap-1 mb-4 flex-wrap">
                  {(selectedContact.tags || []).map(tag => (
                    <Badge key={tag} variant="secondary">{tag}</Badge>
                  ))}
                </div>

                {selectedContact.notes && (
                  <div className="mb-4 p-3 bg-[hsl(var(--secondary))] rounded-lg text-sm">
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">Notes</p>
                    {selectedContact.notes}
                  </div>
                )}

                <Tabs defaultValue="timeline">
                  <TabsList className="bg-[hsl(var(--secondary))]">
                    <TabsTrigger value="timeline">Timeline</TabsTrigger>
                    <TabsTrigger value="info">Info</TabsTrigger>
                  </TabsList>
                  <TabsContent value="timeline" className="mt-4">
                    <ScrollArea className="h-[400px]">
                      <div className="space-y-3">
                        {(timeline || []).map((entry, i) => (
                          <div key={i} className="flex gap-3 text-sm">
                            <div className="w-8 h-8 rounded-full bg-[hsl(var(--secondary))] flex items-center justify-center flex-shrink-0">
                              {entry.type === 'request' && <ClipboardList className="w-4 h-4" />}
                              {entry.type === 'order' && <UtensilsCrossed className="w-4 h-4" />}
                              {entry.type === 'loyalty' && <Gift className="w-4 h-4" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium capitalize">{entry.type}</p>
                              {entry.type === 'request' && <p className="text-xs text-[hsl(var(--muted-foreground))]">{entry.data?.description}</p>}
                              {entry.type === 'order' && <p className="text-xs text-[hsl(var(--muted-foreground))]">{entry.data?.items?.length} items - {formatCurrency(entry.data?.total || 0)}</p>}
                              {entry.type === 'loyalty' && <p className="text-xs text-[hsl(var(--muted-foreground))]">{entry.data?.points > 0 ? '+' : ''}{entry.data?.points} points</p>}
                              <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{formatDate(entry.timestamp)}</p>
                            </div>
                            {entry.data?.status && (
                              <Badge className={`${statusColors[entry.data.status]} border text-xs self-start`}>{entry.data.status}</Badge>
                            )}
                          </div>
                        ))}
                        {(!timeline || timeline.length === 0) && (
                          <p className="text-center text-[hsl(var(--muted-foreground))] py-8">No activity yet</p>
                        )}
                      </div>
                    </ScrollArea>
                  </TabsContent>
                  <TabsContent value="info" className="mt-4 space-y-3">
                    <div className="text-sm">
                      <p className="text-[hsl(var(--muted-foreground))] text-xs">Marketing Consent</p>
                      <p>{selectedContact.consent_marketing ? 'Yes' : 'No'}</p>
                    </div>
                    <div className="text-sm">
                      <p className="text-[hsl(var(--muted-foreground))] text-xs">Data Consent</p>
                      <p>{selectedContact.consent_data ? 'Yes' : 'No'}</p>
                    </div>
                    <div className="text-sm">
                      <p className="text-[hsl(var(--muted-foreground))] text-xs">Loyalty</p>
                      <p>{selectedContact.loyalty_account_id ? 'Enrolled' : 'Not enrolled'}</p>
                    </div>
                    <div className="text-sm">
                      <p className="text-[hsl(var(--muted-foreground))] text-xs">Created</p>
                      <p>{formatDate(selectedContact.created_at)}</p>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ) : (
            <div className="h-full flex items-center justify-center text-[hsl(var(--muted-foreground))]">
              <div className="text-center">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Select a contact to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
