import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { tenantAPI, usersAPI, departmentsAPI, guestServicesAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Settings as SettingsIcon, Shield, Users, Building2, Gift, Plus, ClipboardList } from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
  const { tenant, updateTenant } = useAuthStore();
  const queryClient = useQueryClient();

  // Feature flags
  const [features, setFeatures] = useState({
    hotel_enabled: tenant?.hotel_enabled ?? true,
    restaurant_enabled: tenant?.restaurant_enabled ?? true,
    agency_enabled: tenant?.agency_enabled ?? false,
    clinic_enabled: tenant?.clinic_enabled ?? false,
  });

  // Loyalty rules
  const [loyalty, setLoyalty] = useState(tenant?.loyalty_rules || {});

  // New user
  const [newUser, setNewUser] = useState({ email: '', password: '', name: '', role: 'agent' });
  const [userDialogOpen, setUserDialogOpen] = useState(false);

  // New department
  const [newDept, setNewDept] = useState({ name: '', code: '', description: '' });
  const [deptDialogOpen, setDeptDialogOpen] = useState(false);

  const { data: users = [] } = useQuery({
    queryKey: ['users', tenant?.slug],
    queryFn: () => usersAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: departments = [] } = useQuery({
    queryKey: ['departments', tenant?.slug],
    queryFn: () => departmentsAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: servicesConfig = [] } = useQuery({
    queryKey: ['services-config', tenant?.slug],
    queryFn: () => guestServicesAPI.getServicesConfig(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const updateServicesMutation = useMutation({
    mutationFn: (data) => guestServicesAPI.updateServicesConfig(tenant?.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['services-config']);
      toast.success('Guest services updated');
    },
  });

  const updateFeaturesMutation = useMutation({
    mutationFn: (data) => tenantAPI.update(tenant?.slug, data),
    onSuccess: (res) => {
      updateTenant(res.data);
      toast.success('Features updated');
    },
  });

  const updateLoyaltyMutation = useMutation({
    mutationFn: (data) => tenantAPI.updateLoyaltyRules(tenant?.slug, data),
    onSuccess: (res) => {
      updateTenant(res.data);
      toast.success('Loyalty rules updated');
    },
  });

  const createUserMutation = useMutation({
    mutationFn: (data) => usersAPI.create(tenant?.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['users']);
      toast.success('User created');
      setNewUser({ email: '', password: '', name: '', role: 'agent' });
      setUserDialogOpen(false);
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const createDeptMutation = useMutation({
    mutationFn: (data) => departmentsAPI.create(tenant?.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['departments']);
      toast.success('Department created');
      setNewDept({ name: '', code: '', description: '' });
      setDeptDialogOpen(false);
    },
  });

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Manage your business configuration</p>
      </div>

      <Tabs defaultValue="features">
        <TabsList className="bg-[hsl(var(--secondary))]">
          <TabsTrigger value="features"><Shield className="w-4 h-4 mr-2" /> Features</TabsTrigger>
          <TabsTrigger value="users"><Users className="w-4 h-4 mr-2" /> Users</TabsTrigger>
          <TabsTrigger value="departments"><Building2 className="w-4 h-4 mr-2" /> Departments</TabsTrigger>
          <TabsTrigger value="loyalty"><Gift className="w-4 h-4 mr-2" /> Loyalty</TabsTrigger>
        </TabsList>

        <TabsContent value="features" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-lg">Feature Flags</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {Object.entries(features).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between py-2">
                  <div>
                    <p className="font-medium capitalize">{key.replace('_enabled', '').replace('_', ' ')}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">Enable {key.replace('_enabled', '')} module</p>
                  </div>
                  <Switch checked={value} onCheckedChange={(v) => setFeatures({...features, [key]: v})} data-testid={`feature-${key}`} />
                </div>
              ))}
              <Separator />
              <Button onClick={() => updateFeaturesMutation.mutate(features)} data-testid="save-features-btn">Save Changes</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="users" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Team Members</CardTitle>
              <Dialog open={userDialogOpen} onOpenChange={setUserDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" data-testid="add-user-btn"><Plus className="w-4 h-4 mr-1" /> Add User</Button>
                </DialogTrigger>
                <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <DialogHeader><DialogTitle>Add Team Member</DialogTitle></DialogHeader>
                  <div className="space-y-4">
                    <Input value={newUser.name} onChange={(e) => setNewUser({...newUser, name: e.target.value})} placeholder="Name" className="bg-[hsl(var(--secondary))]" data-testid="user-name-input" />
                    <Input value={newUser.email} onChange={(e) => setNewUser({...newUser, email: e.target.value})} placeholder="Email" className="bg-[hsl(var(--secondary))]" data-testid="user-email-input" />
                    <Input type="password" value={newUser.password} onChange={(e) => setNewUser({...newUser, password: e.target.value})} placeholder="Password" className="bg-[hsl(var(--secondary))]" />
                    <Select value={newUser.role} onValueChange={(v) => setNewUser({...newUser, role: v})}>
                      <SelectTrigger className="bg-[hsl(var(--secondary))]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="manager">Manager</SelectItem>
                        <SelectItem value="agent">Agent</SelectItem>
                        <SelectItem value="department_staff">Department Staff</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button onClick={() => createUserMutation.mutate(newUser)} className="w-full" data-testid="create-user-btn">Create User</Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {users.map(u => (
                  <div key={u.id} className="flex items-center justify-between py-2 px-3 rounded-lg bg-[hsl(var(--secondary))]">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-[hsl(var(--primary)/0.15)] flex items-center justify-center">
                        <span className="text-sm font-semibold text-[hsl(var(--primary))]">{u.name?.charAt(0)?.toUpperCase()}</span>
                      </div>
                      <div>
                        <p className="font-medium text-sm">{u.name}</p>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">{u.email}</p>
                      </div>
                    </div>
                    <Badge variant="secondary" className="capitalize">{u.role}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="departments" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Departments</CardTitle>
              <Dialog open={deptDialogOpen} onOpenChange={setDeptDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" data-testid="add-dept-btn"><Plus className="w-4 h-4 mr-1" /> Add Department</Button>
                </DialogTrigger>
                <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <DialogHeader><DialogTitle>Add Department</DialogTitle></DialogHeader>
                  <div className="space-y-4">
                    <Input value={newDept.name} onChange={(e) => setNewDept({...newDept, name: e.target.value})} placeholder="Housekeeping" className="bg-[hsl(var(--secondary))]" data-testid="dept-name-input" />
                    <Input value={newDept.code} onChange={(e) => setNewDept({...newDept, code: e.target.value.toUpperCase()})} placeholder="HK" className="bg-[hsl(var(--secondary))]" data-testid="dept-code-input" />
                    <Input value={newDept.description} onChange={(e) => setNewDept({...newDept, description: e.target.value})} placeholder="Description" className="bg-[hsl(var(--secondary))]" />
                    <Button onClick={() => createDeptMutation.mutate(newDept)} className="w-full" data-testid="create-dept-btn">Create Department</Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {departments.map(d => (
                  <div key={d.id} className="flex items-center justify-between py-2 px-3 rounded-lg bg-[hsl(var(--secondary))]">
                    <div>
                      <p className="font-medium text-sm">{d.name}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{d.description}</p>
                    </div>
                    <code className="text-xs bg-[hsl(var(--card))] px-2 py-1 rounded">{d.code}</code>
                  </div>
                ))}
                {departments.length === 0 && <p className="text-center text-[hsl(var(--muted-foreground))] py-4">No departments</p>}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="loyalty" className="mt-4">
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardHeader><CardTitle className="text-lg">Loyalty Program</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Enable Loyalty</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Allow guests to join and earn points</p>
                </div>
                <Switch checked={loyalty.enabled} onCheckedChange={(v) => setLoyalty({...loyalty, enabled: v})} data-testid="loyalty-enabled-switch" />
              </div>
              <Separator />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Points per Request</label>
                  <Input type="number" value={loyalty.points_per_request || 10} onChange={(e) => setLoyalty({...loyalty, points_per_request: parseInt(e.target.value)})} className="bg-[hsl(var(--secondary))]" />
                </div>
                <div>
                  <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Points per Order</label>
                  <Input type="number" value={loyalty.points_per_order || 5} onChange={(e) => setLoyalty({...loyalty, points_per_order: parseInt(e.target.value)})} className="bg-[hsl(var(--secondary))]" />
                </div>
                <div>
                  <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Points per 100 TRY</label>
                  <Input type="number" value={loyalty.points_per_currency_unit || 1} onChange={(e) => setLoyalty({...loyalty, points_per_currency_unit: parseInt(e.target.value)})} className="bg-[hsl(var(--secondary))]" />
                </div>
              </div>
              <Button onClick={() => updateLoyaltyMutation.mutate(loyalty)} data-testid="save-loyalty-btn">Save Loyalty Rules</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
