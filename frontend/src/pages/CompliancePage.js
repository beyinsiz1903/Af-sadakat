import React from 'react';
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
import { Shield, FileDown, Trash2, ScrollText, Clock } from 'lucide-react';
import { formatDate } from '../lib/utils';
import { toast } from 'sonner';
import { useState } from 'react';

export default function CompliancePage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();

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
    queryFn: () => api.get(`/tenants/${tenant?.slug}/contacts`, { params: { limit: 100 }}).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const exportMutation = useMutation({
    mutationFn: (contactId) => api.post(`/tenants/${tenant?.slug}/compliance/export/${contactId}`),
    onSuccess: (res) => {
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'guest_data_export.json'; a.click();
      toast.success('Data exported');
    },
  });

  const forgetMutation = useMutation({
    mutationFn: (contactId) => api.post(`/tenants/${tenant?.slug}/compliance/forget/${contactId}`),
    onSuccess: () => {
      queryClient.invalidateQueries(['contacts-compliance']);
      toast.success('Guest data anonymized');
    },
  });

  const retentionMutation = useMutation({
    mutationFn: (data) => api.patch(`/tenants/${tenant?.slug}/compliance/retention`, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['retention']);
      toast.success('Retention policy updated');
    },
  });

  const [retentionMonths, setRetentionMonths] = useState(retention?.retention_months || 24);

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Data Compliance</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">GDPR / KVKK data management</p>
      </div>

      <Tabs defaultValue="guests">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="guests"><Shield className="w-4 h-4 mr-2" /> Guest Data</TabsTrigger>
          <TabsTrigger value="retention"><Clock className="w-4 h-4 mr-2" /> Retention</TabsTrigger>
          <TabsTrigger value="logs"><ScrollText className="w-4 h-4 mr-2" /> Consent Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="guests" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-lg">Guest Data Management</CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="border-[hsl(var(--border))]">
                    <TableHead>Guest</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Consent</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(contacts?.data || []).map(c => (
                    <TableRow key={c.id} className="border-[hsl(var(--border))]">
                      <TableCell className="font-medium">{c.name || 'Unknown'}</TableCell>
                      <TableCell className="text-sm">{c.phone || '-'}</TableCell>
                      <TableCell className="text-sm">{c.email || '-'}</TableCell>
                      <TableCell>
                        {c.consent_data ? <Badge className="bg-emerald-500/10 text-emerald-400 text-xs">Data</Badge> : <Badge variant="secondary" className="text-xs">No</Badge>}
                        {c.consent_marketing && <Badge className="bg-blue-500/10 text-blue-400 text-xs ml-1">Marketing</Badge>}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => exportMutation.mutate(c.id)} data-testid={`export-${c.id}`}>
                            <FileDown className="w-3 h-3 mr-1" /> Export
                          </Button>
                          {!c.anonymized && (
                            <Button variant="ghost" size="sm" className="h-7 text-xs text-[hsl(var(--destructive))]" onClick={() => { if(window.confirm('Anonymize this guest data? This cannot be undone.')) forgetMutation.mutate(c.id); }}>
                              <Trash2 className="w-3 h-3 mr-1" /> Forget
                            </Button>
                          )}
                          {c.anonymized && <Badge variant="secondary" className="text-xs">Anonymized</Badge>}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="retention" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-lg">Data Retention Policy</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div><p className="font-medium">Auto-purge old data</p><p className="text-xs text-[hsl(var(--muted-foreground))]">Automatically delete data older than retention period</p></div>
                <Switch checked={retention?.auto_purge || false} onCheckedChange={(v) => retentionMutation.mutate({ auto_purge: v })} />
              </div>
              <div>
                <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Retention Period (months)</label>
                <div className="flex gap-2">
                  <Input type="number" value={retentionMonths} onChange={(e) => setRetentionMonths(parseInt(e.target.value))} className="bg-[hsl(var(--secondary))] w-32" />
                  <Button onClick={() => retentionMutation.mutate({ retention_months: retentionMonths })} data-testid="save-retention-btn">Save</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-lg">Consent & Compliance Logs</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(consentLogs?.data || []).map(log => (
                  <div key={log.id} className="flex items-center justify-between py-2 px-3 rounded-lg bg-[hsl(var(--secondary))]">
                    <div><p className="text-sm font-medium capitalize">{log.action?.replace(/_/g, ' ')}</p><p className="text-xs text-[hsl(var(--muted-foreground))]">{formatDate(log.created_at)}</p></div>
                    <Badge variant="secondary" className="text-xs">{log.contact_id?.substring(0, 8)}...</Badge>
                  </div>
                ))}
                {(!consentLogs?.data || consentLogs.data.length === 0) && <p className="text-center py-4 text-[hsl(var(--muted-foreground))]">No compliance events yet</p>}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
