import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../lib/store';
import { authAPI, tenantAPI } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Hotel, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [seedLoading, setSeedLoading] = useState(false);

  // Login form
  const [loginEmail, setLoginEmail] = useState('admin@grandhotel.com');
  const [loginPassword, setLoginPassword] = useState('admin123');

  // Register form
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regTenantName, setRegTenantName] = useState('');
  const [regTenantSlug, setRegTenantSlug] = useState('');
  const [regBusinessType, setRegBusinessType] = useState('hotel');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authAPI.login({ email: loginEmail, password: loginPassword });
      login(data.token, data.user, data.tenant);
      toast.success('Welcome back!');
      navigate('/');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authAPI.register({
        email: regEmail,
        password: regPassword,
        name: regName,
        tenant_name: regTenantName,
        tenant_slug: regTenantSlug,
        business_type: regBusinessType,
      });
      login(data.token, data.user, data.tenant);
      toast.success('Account created!');
      navigate('/');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSeed = async () => {
    setSeedLoading(true);
    try {
      const { data } = await tenantAPI.seed();
      toast.success('Demo data created! Login: admin@grandhotel.com / admin123');
      setLoginEmail('admin@grandhotel.com');
      setLoginPassword('admin123');
    } catch (err) {
      if (err.response?.data?.detail?.includes('Already')) {
        toast.info('Demo data already exists');
      } else {
        toast.error('Seed failed');
      }
    } finally {
      setSeedLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[hsl(var(--background))] guest-header-gradient bg-noise">
      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[hsl(var(--primary))] mb-4">
            <Hotel className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold">OmniHub</h1>
          <p className="text-[hsl(var(--muted-foreground))] mt-2">Tourism SaaS Platform</p>
        </div>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <Tabs defaultValue="login">
            <CardHeader className="pb-4">
              <TabsList className="grid w-full grid-cols-2 bg-[hsl(var(--secondary))]">
                <TabsTrigger value="login" data-testid="login-tab">Login</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab">Register</TabsTrigger>
              </TabsList>
            </CardHeader>
            <CardContent>
              <TabsContent value="login" className="mt-0">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Email</label>
                    <Input
                      type="email"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="admin@grandhotel.com"
                      className="bg-[hsl(var(--secondary))] border-[hsl(var(--border))]"
                      data-testid="login-email-input"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Password</label>
                    <Input
                      type="password"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="Enter password"
                      className="bg-[hsl(var(--secondary))] border-[hsl(var(--border))]"
                      data-testid="login-password-input"
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit-btn">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    Sign In
                  </Button>
                </form>
                <div className="mt-4">
                  <Button
                    variant="outline"
                    className="w-full border-dashed"
                    onClick={handleSeed}
                    disabled={seedLoading}
                    data-testid="seed-demo-btn"
                  >
                    {seedLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    Load Demo Data
                  </Button>
                  <p className="text-xs text-center text-[hsl(var(--muted-foreground))] mt-2">
                    Creates sample hotel with rooms, menu, and requests
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="register" className="mt-0">
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Business Name</label>
                      <Input value={regTenantName} onChange={(e) => setRegTenantName(e.target.value)} placeholder="My Hotel" className="bg-[hsl(var(--secondary))]" data-testid="reg-tenant-name" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">URL Slug</label>
                      <Input value={regTenantSlug} onChange={(e) => setRegTenantSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))} placeholder="my-hotel" className="bg-[hsl(var(--secondary))]" data-testid="reg-tenant-slug" />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Business Type</label>
                    <div className="flex gap-2">
                      {['hotel', 'restaurant'].map(t => (
                        <Button key={t} type="button" variant={regBusinessType === t ? 'default' : 'outline'} size="sm" onClick={() => setRegBusinessType(t)} className="flex-1 capitalize">
                          {t}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Your Name</label>
                    <Input value={regName} onChange={(e) => setRegName(e.target.value)} placeholder="John Doe" className="bg-[hsl(var(--secondary))]" data-testid="reg-name" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Email</label>
                    <Input type="email" value={regEmail} onChange={(e) => setRegEmail(e.target.value)} placeholder="you@hotel.com" className="bg-[hsl(var(--secondary))]" data-testid="reg-email" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5 block">Password</label>
                    <Input type="password" value={regPassword} onChange={(e) => setRegPassword(e.target.value)} placeholder="Min 6 characters" className="bg-[hsl(var(--secondary))]" data-testid="reg-password" />
                  </div>
                  <Button type="submit" className="w-full" disabled={loading} data-testid="register-submit-btn">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    Create Account
                  </Button>
                </form>
              </TabsContent>
            </CardContent>
          </Tabs>
        </Card>
      </div>
    </div>
  );
}
