import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Shield, FileDown, Trash2, ScrollText, Clock, AlertTriangle, CheckCircle2, Search } from 'lucide-react';
import { formatDate } from '../lib/utils';
import { toast } from 'sonner';

export default function CompliancePage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [exportContactId, setExportContactId] = useState('');

  const { data: retention } = useQuery({
    queryKey: ['retention', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/compliance/retention`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: consentLogs } = useQuery({
    queryKey: ['consent-logs', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/compliance/consent-logs`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: contacts } = useQuery({
    queryKey: ['contacts-compliance', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/contacts`, { params: { limit: 100 } }).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const exportMutation = useMutation({
    mutationFn: (contactId) => api.post(`/tenants/${tenant?.slug}/compliance/export/${contactId}`),
    onSuccess: (res) => {
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `guest_data_export_${Date.now()}.json`;
      a.click();
      toast.success('Veri paketi indirildi');
      queryClient.invalidateQueries(['consent-logs']);
    },
    onError: () => toast.error('Veri disari aktarim basarisiz'),
  });

  const forgetMutation = useMutation({
    mutationFn: (contactId) => api.post(`/tenants/${tenant?.slug}/compliance/forget/${contactId}`),
    onSuccess: () => {
      toast.success('Misafir verisi anonimlestirildi');
      queryClient.invalidateQueries(['contacts-compliance', 'consent-logs']);
    },
    onError: () => toast.error('Anonimizasyon basarisiz'),
  });

  const retentionMutation = useMutation({
    mutationFn: (data) => api.patch(`/tenants/${tenant?.slug}/compliance/retention`, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['retention']);
      toast.success('Saklama politikasi guncellendi');
    },
  });

  const filteredContacts = (contacts?.data || contacts || []).filter(c =>
    !searchTerm || (c.name || '').toLowerCase().includes(searchTerm.toLowerCase()) || (c.email || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6 text-[hsl(var(--primary))]" /> GDPR / KVKK Uyumluluk
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Veri koruma, riza yonetimi ve saklama politikalari</p>
      </div>

      <Tabs defaultValue="data-rights">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="data-rights">Veri Haklari</TabsTrigger>
          <TabsTrigger value="consent">Riza Kayitlari</TabsTrigger>
          <TabsTrigger value="retention">Saklama Politikasi</TabsTrigger>
        </TabsList>

        <TabsContent value="data-rights" className="mt-4 space-y-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-4">
                <Search className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                <Input
                  placeholder="Misafir ara (isim veya email)..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="bg-[hsl(var(--secondary))] border-[hsl(var(--border))]"
                />
              </div>
              <Table>
                <TableHeader>
                  <TableRow className="border-[hsl(var(--border))]">
                    <TableHead>Misafir</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Telefon</TableHead>
                    <TableHead>Durum</TableHead>
                    <TableHead>Islemler</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredContacts.slice(0, 20).map(c => (
                    <TableRow key={c.id} className="border-[hsl(var(--border))]">
                      <TableCell className="font-medium">{c.name || '-'}</TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">{c.email || '-'}</TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">{c.phone || '-'}</TableCell>
                      <TableCell>
                        {c.anonymized ? (
                          <Badge className="bg-gray-500/20 text-gray-400">Anonimlestirildi</Badge>
                        ) : (
                          <Badge className="bg-emerald-500/20 text-emerald-400">Aktif</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            onClick={() => exportMutation.mutate(c.id)}
                            disabled={exportMutation.isPending || c.anonymized}
                          >
                            <FileDown className="w-3 h-3 mr-1" /> Disari Aktar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs text-red-400 hover:text-red-300"
                            onClick={() => {
                              if (window.confirm(`"${c.name}" icin unutulma hakki uygulansin mi? Bu islem geri alinamaz.`)) {
                                forgetMutation.mutate(c.id);
                              }
                            }}
                            disabled={forgetMutation.isPending || c.anonymized}
                          >
                            <Trash2 className="w-3 h-3 mr-1" /> Unutulma Hakki
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredContacts.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-[hsl(var(--muted-foreground))] py-8">
                        Misafir bulunamadi
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="consent" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <ScrollText className="w-4 h-4" /> Riza Kayitlari ({consentLogs?.total || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-[hsl(var(--border))]">
                    <TableHead>Islem</TableHead>
                    <TableHead>Iletisim ID</TableHead>
                    <TableHead>Kaynak</TableHead>
                    <TableHead>Verildigi</TableHead>
                    <TableHead>Tarih</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(consentLogs?.data || []).map(log => (
                    <TableRow key={log.id} className="border-[hsl(var(--border))]">
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {log.action === 'data_export' ? 'Veri Disari Aktarim' :
                           log.action === 'right_to_forget' ? 'Unutulma Hakki' :
                           log.action === 'retention_auto_cleanup' ? 'Otomatik Temizlik' :
                           log.action?.replace('consent_', 'Riza: ') || log.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{(log.contact_id || '').substring(0, 8)}...</TableCell>
                      <TableCell className="text-sm">{log.source || '-'}</TableCell>
                      <TableCell>
                        {log.granted !== undefined ? (
                          log.granted ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-red-400" />
                        ) : '-'}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">{formatDate(log.created_at)}</TableCell>
                    </TableRow>
                  ))}
                  {(!consentLogs?.data || consentLogs.data.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-[hsl(var(--muted-foreground))] py-8">
                        Riza kaydi bulunmuyor
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="retention" className="mt-4 space-y-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <Clock className="w-6 h-6 text-[hsl(var(--primary))]" />
                <div>
                  <h3 className="font-bold">Veri Saklama Politikasi</h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">KVKK uyumlu otomatik veri temizleme ayarlari</p>
                </div>
              </div>

              <div className="space-y-6">
                <div className="flex items-center justify-between p-4 rounded-xl bg-[hsl(var(--secondary)/0.5)] border border-[hsl(var(--border))]">
                  <div>
                    <p className="font-medium">Saklama Suresi</p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Inaktif misafir verisi ne kadar sure tutulacak</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      value={retention?.retention_months || 24}
                      onChange={(e) => retentionMutation.mutate({ retention_months: parseInt(e.target.value) || 24 })}
                      className="w-20 bg-[hsl(var(--secondary))] border-[hsl(var(--border))] text-center"
                      min={1}
                      max={120}
                    />
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">ay</span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl bg-[hsl(var(--secondary)/0.5)] border border-[hsl(var(--border))]">
                  <div>
                    <p className="font-medium">Otomatik Temizlik</p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Saklama suresi dolan veriler otomatik olarak anonimlestirilsin mi?</p>
                  </div>
                  <Switch
                    checked={retention?.auto_purge || false}
                    onCheckedChange={(checked) => retentionMutation.mutate({ auto_purge: checked })}
                  />
                </div>

                {retention?.auto_purge && (
                  <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-amber-300">Otomatik Temizlik Aktif</p>
                        <p className="text-xs text-amber-200/80 mt-1">
                          {retention?.retention_months || 24} aydan eski inaktif misafir verileri her gun otomatik olarak anonimlestirilecek.
                          Bu islem geri alinamaz.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
