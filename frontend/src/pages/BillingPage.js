import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { CreditCard, Receipt, ArrowUpRight, Check, Zap, Crown, Building2 } from 'lucide-react';
import { formatDate } from '../lib/utils';
import { toast } from 'sonner';

const planFeatures = {
  basic: ['Hotel QR', 'Restaurant QR', 'CRM', 'WebChat', '5 users', '20 rooms'],
  pro: ['Everything in Basic', 'Loyalty Program', 'AI Suggestions', 'Departments', 'Real-time Boards', 'Reviews', '25 users', '100 rooms'],
  enterprise: ['Everything in Pro', 'API Connectors', 'White Label', 'Custom SLA', 'Unlimited', 'Priority Support'],
};

const planIcons = { basic: Zap, pro: Crown, enterprise: Building2 };
const planColors = { basic: 'text-blue-400', pro: 'text-amber-400', enterprise: 'text-purple-400' };

export default function BillingPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const { updateTenant } = useAuthStore();
  const queryClient = useQueryClient();

  const { data: billing } = useQuery({
    queryKey: ['billing', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/billing`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: usage } = useQuery({
    queryKey: ['usage', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/usage`).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const upgradeMutation = useMutation({
    mutationFn: (plan) => api.post(`/tenants/${tenant?.slug}/upgrade`, { plan }),
    onSuccess: (res) => {
      updateTenant(res.data);
      queryClient.invalidateQueries(['billing', 'usage']);
      toast.success('Plan upgraded successfully!');
    },
  });

  const currentPlan = tenant?.plan || 'basic';

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Billing & Plans</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Manage your subscription and usage</p>
      </div>

      <Tabs defaultValue="plans">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="plans">Plans</TabsTrigger>
          <TabsTrigger value="usage">Usage</TabsTrigger>
          <TabsTrigger value="invoices">Invoices</TabsTrigger>
        </TabsList>

        <TabsContent value="plans" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {['basic', 'pro', 'enterprise'].map(plan => {
              const Icon = planIcons[plan];
              const isCurrent = currentPlan === plan;
              const price = plan === 'basic' ? 49 : plan === 'pro' ? 149 : 499;
              return (
                <Card key={plan} className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] ${isCurrent ? 'border-[hsl(var(--primary))] ring-1 ring-[hsl(var(--primary)/0.3)]' : ''}`}>
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <div className={`w-10 h-10 rounded-xl bg-[hsl(var(--secondary))] flex items-center justify-center`}>
                        <Icon className={`w-5 h-5 ${planColors[plan]}`} />
                      </div>
                      <div>
                        <h3 className="font-bold capitalize">{plan}</h3>
                        {isCurrent && <Badge className="bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] text-xs">Current</Badge>}
                      </div>
                    </div>
                    <p className="text-3xl font-bold mb-4">${price}<span className="text-sm text-[hsl(var(--muted-foreground))] font-normal">/mo</span></p>
                    <ul className="space-y-2 mb-6">
                      {(planFeatures[plan] || []).map((f, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <Check className="w-3.5 h-3.5 text-emerald-400" /> {f}
                        </li>
                      ))}
                    </ul>
                    {!isCurrent && (
                      <Button className="w-full" variant={plan === 'enterprise' ? 'outline' : 'default'}
                        onClick={() => upgradeMutation.mutate(plan)}
                        data-testid={`upgrade-${plan}-btn`}
                      >
                        {plan === 'enterprise' ? 'Contact Sales' : 'Upgrade'}
                      </Button>
                    )}
                    {isCurrent && <Button className="w-full" variant="secondary" disabled>Current Plan</Button>}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="usage" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {usage && Object.entries(usage.metrics || {}).map(([key, val]) => (
              <Card key={key} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="text-sm">{val.current} / {val.limit}</span>
                  </div>
                  <Progress value={Math.min((val.current / val.limit) * 100, 100)} className="h-2" />
                  {val.current >= val.limit && (
                    <p className="text-xs text-[hsl(var(--destructive))] mt-1">Limit reached - upgrade to increase</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="invoices" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <Table>
              <TableHeader>
                <TableRow className="border-[hsl(var(--border))]">
                  <TableHead>Invoice</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(billing?.invoices || []).map(inv => (
                  <TableRow key={inv.id} className="border-[hsl(var(--border))]">
                    <TableCell className="font-mono text-xs">{inv.invoice_number}</TableCell>
                    <TableCell className="text-sm">{formatDate(inv.period_start)} - {formatDate(inv.period_end)}</TableCell>
                    <TableCell className="font-medium">${inv.amount}</TableCell>
                    <TableCell><Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/25 border text-xs">{inv.status}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
