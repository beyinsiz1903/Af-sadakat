import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { CreditCard, Receipt, ArrowUpRight, Check, Zap, Crown, Building2, AlertTriangle, X, Shield } from 'lucide-react';
import { formatDate } from '../lib/utils';
import { toast } from 'sonner';

const planFeatures = {
  basic: ['Hotel QR', 'Restaurant QR', 'CRM', 'WebChat', '5 kullanici', '20 oda', '50 AI cevap/ay'],
  pro: ['Basic dahil', 'Sadakat Programi', 'AI Onerileri', 'Departmanlar', 'Canli Panolar', 'Yorumlar', '25 kullanici', '100 oda', '500 AI cevap/ay'],
  enterprise: ['Pro dahil', 'API Connectorleri', 'White Label', 'Ozel SLA', 'Sinirsiz', 'Oncelikli Destek', 'Gelismis Analitik', 'GDPR Araclari'],
};
const planIcons = { basic: Zap, pro: Crown, enterprise: Building2 };
const planColors = { basic: 'text-blue-400', pro: 'text-amber-400', enterprise: 'text-purple-400' };
const planPrices = { basic: 49, pro: 149, enterprise: 499 };

function UpgradeModal({ isOpen, onClose, targetPlan, currentPlan, onConfirm, loading }) {
  if (!isOpen) return null;
  const price = planPrices[targetPlan] || 0;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Plan Yukseltme</h2>
          <button onClick={onClose} className="text-[hsl(var(--muted-foreground))] hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="mb-4 p-4 rounded-xl bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)]">
          <div className="flex items-center gap-3 mb-2">
            <ArrowUpRight className="w-5 h-5 text-[hsl(var(--primary))]" />
            <span className="font-semibold capitalize">{currentPlan} → {targetPlan}</span>
          </div>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Aylik ${price}/ay faturalama baslar</p>
        </div>
        <div className="mb-4">
          <h3 className="text-sm font-medium mb-2">Yeni ozellikler:</h3>
          <ul className="space-y-1">
            {(planFeatures[targetPlan] || []).map((f, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />{f}
              </li>
            ))}
          </ul>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onClose} className="flex-1">Vazgec</Button>
          <Button onClick={() => onConfirm(targetPlan)} disabled={loading} className="flex-1 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.9)]">
            {loading ? 'Islem...' : `${targetPlan.charAt(0).toUpperCase() + targetPlan.slice(1)} Plana Gec`}
          </Button>
        </div>
      </div>
    </div>
  );
}

function LimitWarningBanner({ usage }) {
  if (!usage?.metrics) return null;
  const warnings = Object.entries(usage.metrics).filter(([, v]) => v.pct >= 80);
  if (warnings.length === 0) return null;
  return (
    <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
      <div>
        <p className="font-medium text-amber-300">Limit Uyarisi</p>
        <p className="text-sm text-amber-200/80 mt-1">
          {warnings.map(([key, v]) => `${key}: %${Math.round(v.pct)}`).join(' · ')} — Plan yukselterek limitlerinizi artirin.
        </p>
      </div>
    </div>
  );
}

export default function BillingPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const { updateTenant } = useAuthStore();
  const queryClient = useQueryClient();
  const [upgradeModal, setUpgradeModal] = useState({ open: false, plan: '' });

  const { data: billing } = useQuery({
    queryKey: ['billing', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/billing`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: usage } = useQuery({
    queryKey: ['usage-detailed', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/usage/detailed`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const upgradeMutation = useMutation({
    mutationFn: (plan) => api.post(`/tenants/${tenant?.slug}/upgrade`, { plan }),
    onSuccess: (res) => {
      updateTenant(res.data);
      queryClient.invalidateQueries(['billing', 'usage', 'usage-detailed']);
      toast.success('Plan basariyla yukseltildi!');
      setUpgradeModal({ open: false, plan: '' });
    },
    onError: () => toast.error('Plan yukseltme basarisiz'),
  });

  const currentPlan = tenant?.plan || 'basic';

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Faturalandirma & Planlar</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Abonelik ve kullanim yonetiminiz</p>
      </div>

      <LimitWarningBanner usage={usage} />

      <Tabs defaultValue="plans">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="plans">Planlar</TabsTrigger>
          <TabsTrigger value="usage">Kullanim</TabsTrigger>
          <TabsTrigger value="invoices">Faturalar</TabsTrigger>
          <TabsTrigger value="payment">Odeme Yontemi</TabsTrigger>
        </TabsList>

        <TabsContent value="plans" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {['basic', 'pro', 'enterprise'].map(plan => {
              const Icon = planIcons[plan];
              const isCurrent = currentPlan === plan;
              const price = planPrices[plan];
              const isUpgrade = ['basic', 'pro', 'enterprise'].indexOf(plan) > ['basic', 'pro', 'enterprise'].indexOf(currentPlan);
              return (
                <Card key={plan} className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] ${isCurrent ? 'border-[hsl(var(--primary))] ring-1 ring-[hsl(var(--primary)/0.3)]' : ''}`}>
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-xl bg-[hsl(var(--secondary))] flex items-center justify-center">
                        <Icon className={`w-5 h-5 ${planColors[plan]}`} />
                      </div>
                      <div>
                        <h3 className="font-bold capitalize">{plan}</h3>
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">${price}/ay</p>
                      </div>
                      {isCurrent && <Badge className="ml-auto bg-[hsl(var(--primary)/0.2)] text-[hsl(var(--primary))]">Mevcut</Badge>}
                    </div>
                    <ul className="space-y-2 mb-4">
                      {(planFeatures[plan] || []).map((f, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                          <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />{f}
                        </li>
                      ))}
                    </ul>
                    {isUpgrade && (
                      <Button onClick={() => setUpgradeModal({ open: true, plan })} className="w-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.9)]" size="sm">
                        <ArrowUpRight className="w-4 h-4 mr-1" /> Yukselt
                      </Button>
                    )}
                    {isCurrent && (
                      <Button disabled className="w-full" variant="outline" size="sm">Mevcut Planiniz</Button>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="usage" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {usage?.metrics && Object.entries(usage.metrics).map(([key, v]) => (
              <Card key={key} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium capitalize">{key.replace('_', ' ')}</span>
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">{v.current} / {v.limit}</span>
                  </div>
                  <Progress value={v.pct} className="h-2" />
                  {v.pct >= 90 && (
                    <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> Limite yaklasiyorsunuz!
                    </p>
                  )}
                  {v.pct >= 80 && v.pct < 90 && (
                    <p className="text-xs text-amber-400 mt-1">%{Math.round(v.pct)} kullanildi</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
          {usage?.features && (
            <Card className="mt-4 bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardHeader><CardTitle className="text-sm">Aktif Ozellikler</CardTitle></CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {usage.features.map(f => (
                  <Badge key={f} variant="outline" className="text-xs">{f}</Badge>
                ))}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="invoices" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-[hsl(var(--border))]">
                    <TableHead>Fatura No</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>Tutar</TableHead>
                    <TableHead>Durum</TableHead>
                    <TableHead>Tarih</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(billing?.invoices || []).map(inv => (
                    <TableRow key={inv.id} className="border-[hsl(var(--border))]">
                      <TableCell className="font-mono text-sm">{inv.invoice_number}</TableCell>
                      <TableCell className="capitalize">{inv.plan}</TableCell>
                      <TableCell>${inv.amount}</TableCell>
                      <TableCell>
                        <Badge className={inv.status === 'paid' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}>
                          {inv.status === 'paid' ? 'Odendi' : 'Bekliyor'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-[hsl(var(--muted-foreground))]">{formatDate(inv.created_at)}</TableCell>
                    </TableRow>
                  ))}
                  {(!billing?.invoices || billing.invoices.length === 0) && (
                    <TableRow><TableCell colSpan={5} className="text-center text-[hsl(var(--muted-foreground))] py-8">Henuz fatura bulunmuyor</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="payment" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <Shield className="w-6 h-6 text-[hsl(var(--primary))]" />
                <div>
                  <h3 className="font-semibold">Odeme Yontemi</h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Stripe ile guvenli odeme</p>
                </div>
              </div>
              {billing?.billing_account?.payment_method ? (
                <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--secondary)/0.5)] flex items-center gap-3">
                  <CreditCard className="w-8 h-8 text-blue-400" />
                  <div>
                    <p className="font-mono">**** **** **** 4242</p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Visa · 12/2027</p>
                  </div>
                  <Badge className="ml-auto bg-emerald-500/20 text-emerald-400">Varsayilan</Badge>
                </div>
              ) : (
                <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                  <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-40" />
                  <p>Henuz odeme yontemi eklenmedi</p>
                  <p className="text-sm mt-1">Stripe entegrasyonu yapilandirildiginda burada gorunur</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <UpgradeModal
        isOpen={upgradeModal.open}
        onClose={() => setUpgradeModal({ open: false, plan: '' })}
        targetPlan={upgradeModal.plan}
        currentPlan={currentPlan}
        onConfirm={(plan) => upgradeMutation.mutate(plan)}
        loading={upgradeMutation.isPending}
      />
    </div>
  );
}
