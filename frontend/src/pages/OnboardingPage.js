import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Progress } from '../components/ui/progress';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Building2, BedDouble, TableProperties, BookOpen, Gift, QrCode, Users, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const STEPS = [
  { num: 1, label: 'Business Info', icon: Building2, key: '1' },
  { num: 2, label: 'Departments', icon: Building2, key: '2' },
  { num: 3, label: 'Rooms / Tables', icon: BedDouble, key: '3' },
  { num: 4, label: 'Menu', icon: BookOpen, key: '4' },
  { num: 5, label: 'Loyalty', icon: Gift, key: '5' },
  { num: 6, label: 'QR Codes', icon: QrCode, key: '6' },
  { num: 7, label: 'Invite Team', icon: Users, key: '7' },
];

export default function OnboardingPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const navigate = useNavigate();
  const [onboarding, setOnboarding] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(true);

  // Step forms
  const [deptName, setDeptName] = useState('');
  const [deptCode, setDeptCode] = useState('');
  const [roomNumber, setRoomNumber] = useState('');
  const [tableNumber, setTableNumber] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');

  useEffect(() => {
    loadOnboarding();
  }, [tenant?.slug]);

  const loadOnboarding = async () => {
    if (!tenant?.slug) return;
    try {
      const { data } = await api.get(`/tenants/${tenant.slug}/onboarding`);
      setOnboarding(data);
      if (data.completed) { navigate('/dashboard'); return; }
      // Find first incomplete step
      const steps = data.steps || {};
      for (let i = 1; i <= 7; i++) {
        if (!steps[String(i)]?.completed) { setCurrentStep(i); break; }
      }
    } catch (e) { console.error('onboarding load failed', e); } finally { setLoading(false); }
  };

  const addDepartment = async () => {
    if (!deptName || !deptCode) return;
    try {
      await api.post(`/tenants/${tenant.slug}/departments`, { name: deptName, code: deptCode });
      toast.success('Department added');
      setDeptName(''); setDeptCode('');
      loadOnboarding();
    } catch (e) { toast.error('Failed'); }
  };

  const addRoom = async () => {
    if (!roomNumber) return;
    try {
      await api.post(`/tenants/${tenant.slug}/rooms`, { room_number: roomNumber });
      toast.success('Room added');
      setRoomNumber('');
      loadOnboarding();
    } catch (e) { toast.error('Failed'); }
  };

  const addTable = async () => {
    if (!tableNumber) return;
    try {
      await api.post(`/tenants/${tenant.slug}/tables`, { table_number: tableNumber });
      toast.success('Table added');
      setTableNumber('');
      loadOnboarding();
    } catch (e) { toast.error('Failed'); }
  };

  const inviteMember = async () => {
    if (!inviteEmail || !inviteName) return;
    try {
      await api.post(`/tenants/${tenant.slug}/users`, { email: inviteEmail, password: 'welcome123', name: inviteName, role: 'agent' });
      toast.success('Team member invited');
      setInviteEmail(''); setInviteName('');
      loadOnboarding();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const completeOnboarding = async () => {
    try {
      await api.post(`/tenants/${tenant.slug}/onboarding/complete`);
      toast.success('Onboarding complete! Welcome to OmniHub.');
      navigate('/dashboard');
    } catch (e) { toast.error('Failed'); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin" /></div>;

  const steps = onboarding?.steps || {};
  const progress = onboarding?.progress || 0;

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] p-4 lg:p-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold">Welcome to OmniHub</h1>
          <p className="text-[hsl(var(--muted-foreground))] mt-2">Let's set up your business in minutes</p>
          <div className="mt-4"><Progress value={progress} className="h-2" /></div>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-2">{progress}% complete</p>
        </div>

        {/* Steps */}
        <div className="flex gap-2 overflow-x-auto pb-4 mb-6 scrollbar-thin">
          {STEPS.map(step => {
            const isComplete = steps[step.key]?.completed;
            const isCurrent = currentStep === step.num;
            return (
              <button key={step.num} onClick={() => setCurrentStep(step.num)} className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all whitespace-nowrap ${
                isCurrent ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]' :
                isComplete ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400' :
                'border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]'
              }`} data-testid={`onboarding-step-${step.num}`}>
                {isComplete ? <CheckCircle2 className="w-4 h-4" /> : <step.icon className="w-4 h-4" />}
                {step.label}
              </button>
            );
          })}
        </div>

        {/* Step Content */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-6">
            {currentStep === 1 && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Business Info</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">Your business is set up as: <Badge variant="secondary" className="ml-1 capitalize">{tenant?.business_type}</Badge></p>
                <p className="text-sm text-emerald-400">Business info is already configured from registration.</p>
                <Button onClick={() => setCurrentStep(2)}><ArrowRight className="w-4 h-4 mr-2" /> Next Step</Button>
              </div>
            )}

            {currentStep === 2 && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Create Departments</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">Departments route guest requests to the right team.</p>
                <div className="flex gap-2">
                  <Input value={deptName} onChange={(e) => setDeptName(e.target.value)} placeholder="Department name" className="bg-[hsl(var(--secondary))]" />
                  <Input value={deptCode} onChange={(e) => setDeptCode(e.target.value.toUpperCase())} placeholder="Code (HK)" className="bg-[hsl(var(--secondary))] w-32" />
                  <Button onClick={addDepartment} disabled={!deptName || !deptCode} data-testid="onboarding-add-dept">Add</Button>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {['Housekeeping/HK', 'Technical/TECH', 'F&B/FB', 'Front Desk/FRONTDESK'].map(d => {
                    const [name, code] = d.split('/');
                    return <Button key={d} variant="outline" size="sm" onClick={() => { setDeptName(name); setDeptCode(code); }}>{name}</Button>;
                  })}
                </div>
                {steps['2']?.completed && <Badge className="bg-emerald-500/10 text-emerald-400">Departments created</Badge>}
                <Button onClick={() => setCurrentStep(3)}><ArrowRight className="w-4 h-4 mr-2" /> Next</Button>
              </div>
            )}

            {currentStep === 3 && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Add Rooms & Tables</h2>
                {tenant?.hotel_enabled && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Rooms</p>
                    <div className="flex gap-2">
                      <Input value={roomNumber} onChange={(e) => setRoomNumber(e.target.value)} placeholder="Room number (101)" className="bg-[hsl(var(--secondary))]" />
                      <Button onClick={addRoom} disabled={!roomNumber} data-testid="onboarding-add-room">Add Room</Button>
                    </div>
                  </div>
                )}
                {tenant?.restaurant_enabled && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Tables</p>
                    <div className="flex gap-2">
                      <Input value={tableNumber} onChange={(e) => setTableNumber(e.target.value)} placeholder="Table number (1)" className="bg-[hsl(var(--secondary))]" />
                      <Button onClick={addTable} disabled={!tableNumber} data-testid="onboarding-add-table">Add Table</Button>
                    </div>
                  </div>
                )}
                {steps['3']?.completed && <Badge className="bg-emerald-500/10 text-emerald-400">Rooms/Tables added</Badge>}
                <Button onClick={() => setCurrentStep(4)}><ArrowRight className="w-4 h-4 mr-2" /> Next</Button>
              </div>
            )}

            {currentStep === 4 && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Configure Menu</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">You can add menu items in detail from the Menu page later.</p>
                <Button variant="outline" onClick={() => navigate('/menu')}>Go to Menu Management</Button>
                <Button onClick={() => setCurrentStep(5)}><ArrowRight className="w-4 h-4 mr-2" /> Skip / Next</Button>
              </div>
            )}

            {currentStep === 5 && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Loyalty Program</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">Configure loyalty rules from Settings when ready.</p>
                <Button onClick={() => setCurrentStep(6)}><ArrowRight className="w-4 h-4 mr-2" /> Next</Button>
              </div>
            )}

            {currentStep === 6 && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">QR Codes Ready</h2>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">QR codes are automatically generated for each room and table. Share the links with your guests.</p>
                {steps['6']?.completed && <Badge className="bg-emerald-500/10 text-emerald-400">QR codes ready</Badge>}
                <Button onClick={() => setCurrentStep(7)}><ArrowRight className="w-4 h-4 mr-2" /> Next</Button>
              </div>
            )}

            {currentStep === 7 && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Invite Team Members</h2>
                <div className="flex gap-2">
                  <Input value={inviteName} onChange={(e) => setInviteName(e.target.value)} placeholder="Name" className="bg-[hsl(var(--secondary))]" />
                  <Input value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="Email" className="bg-[hsl(var(--secondary))]" />
                  <Button onClick={inviteMember} disabled={!inviteName || !inviteEmail} data-testid="onboarding-invite">Invite</Button>
                </div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Default password: welcome123 (they can change it later)</p>
                <div className="pt-4">
                  <Button className="w-full" size="lg" onClick={completeOnboarding} data-testid="complete-onboarding-btn">
                    <CheckCircle2 className="w-5 h-5 mr-2" /> Complete Setup & Go to Dashboard
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
