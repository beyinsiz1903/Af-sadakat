import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { aiSalesAPI, propertiesAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Bot, Sparkles, DollarSign, Shield, Settings, Plus, Pencil, Trash2,
  TrendingUp, MessageSquare, CreditCard, AlertTriangle, Check, X,
  Bed, Percent, FileText, BarChart3
} from 'lucide-react';
import { toast } from 'sonner';

export default function AISalesPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const activePropertyId = useAuthStore((s) => s.activePropertyId);
  const queryClient = useQueryClient();
  const [selectedPropertyId, setSelectedPropertyId] = useState(activePropertyId || '');

  // Properties list
  const { data: properties } = useQuery({
    queryKey: ['v2-properties', tenant?.slug],
    queryFn: () => propertiesAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  useEffect(() => {
    if (properties?.length && !selectedPropertyId) {
      setSelectedPropertyId(properties[0].id);
    }
  }, [properties, selectedPropertyId]);

  useEffect(() => {
    if (activePropertyId) setSelectedPropertyId(activePropertyId);
  }, [activePropertyId]);

  // AI Stats
  const { data: stats } = useQuery({
    queryKey: ['ai-stats', tenant?.slug],
    queryFn: () => aiSalesAPI.getStats(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  // AI Settings
  const { data: allSettings, refetch: refetchSettings } = useQuery({
    queryKey: ['ai-settings', tenant?.slug],
    queryFn: () => aiSalesAPI.getSettings(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const currentSettings = allSettings?.find(s => s.property_id === selectedPropertyId) || {};

  // Room Rates
  const { data: roomRates, refetch: refetchRates } = useQuery({
    queryKey: ['room-rates', tenant?.slug, selectedPropertyId],
    queryFn: () => aiSalesAPI.listRoomRates(tenant?.slug, selectedPropertyId).then(r => r.data),
    enabled: !!tenant?.slug && !!selectedPropertyId,
  });

  // Discount Rules
  const { data: discountRules, refetch: refetchDiscounts } = useQuery({
    queryKey: ['discount-rules', tenant?.slug, selectedPropertyId],
    queryFn: () => aiSalesAPI.getDiscountRules(tenant?.slug, selectedPropertyId).then(r => r.data),
    enabled: !!tenant?.slug && !!selectedPropertyId,
  });

  // Policies
  const { data: policies, refetch: refetchPolicies } = useQuery({
    queryKey: ['policies', tenant?.slug, selectedPropertyId],
    queryFn: () => aiSalesAPI.getPolicies(tenant?.slug, selectedPropertyId).then(r => r.data),
    enabled: !!tenant?.slug && !!selectedPropertyId,
  });

  const selectedPropName = properties?.find(p => p.id === selectedPropertyId)?.name || '';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bot className="w-7 h-7 text-indigo-400" />
            AI Sales Engine
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure automated AI booking agent for each property
          </p>
        </div>
        {properties?.length > 1 && (
          <Select value={selectedPropertyId} onValueChange={setSelectedPropertyId}>
            <SelectTrigger className="w-64 bg-slate-800 border-slate-700 text-white">
              <SelectValue placeholder="Select property" />
            </SelectTrigger>
            <SelectContent>
              {properties?.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatsCard icon={MessageSquare} label="AI Replies This Month"
          value={`${stats?.ai_replies_used || 0} / ${stats?.ai_replies_limit || 500}`}
          color="text-blue-400" />
        <StatsCard icon={DollarSign} label="AI Offers Created"
          value={stats?.ai_offers_created || 0} color="text-emerald-400" />
        <StatsCard icon={CreditCard} label="AI Offers Paid"
          value={stats?.ai_offers_paid || 0} color="text-amber-400" />
        <StatsCard icon={TrendingUp} label="Active Sessions"
          value={stats?.active_sessions || 0} color="text-purple-400" />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="settings" className="w-full">
        <TabsList className="bg-slate-800 border border-slate-700">
          <TabsTrigger value="settings" className="data-[state=active]:bg-slate-700">
            <Settings className="w-4 h-4 mr-1" /> Settings
          </TabsTrigger>
          <TabsTrigger value="rates" className="data-[state=active]:bg-slate-700">
            <Bed className="w-4 h-4 mr-1" /> Room Rates
          </TabsTrigger>
          <TabsTrigger value="discounts" className="data-[state=active]:bg-slate-700">
            <Percent className="w-4 h-4 mr-1" /> Discounts
          </TabsTrigger>
          <TabsTrigger value="policies" className="data-[state=active]:bg-slate-700">
            <FileText className="w-4 h-4 mr-1" /> Policies
          </TabsTrigger>
        </TabsList>

        <TabsContent value="settings">
          <AISettingsTab settings={currentSettings} slug={tenant?.slug}
            propertyId={selectedPropertyId} refetch={refetchSettings} />
        </TabsContent>

        <TabsContent value="rates">
          <RoomRatesTab rates={roomRates || []} slug={tenant?.slug}
            propertyId={selectedPropertyId} refetch={refetchRates} />
        </TabsContent>

        <TabsContent value="discounts">
          <DiscountRulesTab rules={discountRules || {}} slug={tenant?.slug}
            propertyId={selectedPropertyId} refetch={refetchDiscounts} />
        </TabsContent>

        <TabsContent value="policies">
          <PoliciesTab policies={policies || {}} slug={tenant?.slug}
            propertyId={selectedPropertyId} refetch={refetchPolicies} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StatsCard({ icon: Icon, label, value, color }) {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardContent className="p-4 flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-slate-800 ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-xs text-slate-400">{label}</p>
          <p className="text-lg font-semibold text-white">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function AISettingsTab({ settings, slug, propertyId, refetch }) {
  const [enabled, setEnabled] = useState(settings?.enabled || false);
  const [maxMessages, setMaxMessages] = useState(settings?.max_messages_without_human || 20);
  const [languages, setLanguages] = useState(settings?.allowed_languages || ['TR', 'EN']);
  const [keywords, setKeywords] = useState((settings?.escalation_keywords || []).join(', '));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setEnabled(settings?.enabled || false);
    setMaxMessages(settings?.max_messages_without_human || 20);
    setLanguages(settings?.allowed_languages || ['TR', 'EN']);
    setKeywords((settings?.escalation_keywords || []).join(', '));
  }, [settings]);

  const save = async () => {
    setSaving(true);
    try {
      await aiSalesAPI.updateSettings(slug, propertyId, {
        enabled,
        max_messages_without_human: maxMessages,
        allowed_languages: languages,
        escalation_keywords: keywords.split(',').map(k => k.trim()).filter(Boolean),
      });
      toast.success('AI settings saved');
      refetch();
    } catch (e) {
      toast.error('Failed to save settings');
    }
    setSaving(false);
  };

  return (
    <Card className="bg-slate-900 border-slate-800 mt-4">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Bot className="w-5 h-5 text-indigo-400" /> AI Auto-Reply Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between p-4 bg-slate-800 rounded-lg">
          <div>
            <p className="text-white font-medium">Enable AI Auto-Reply</p>
            <p className="text-sm text-slate-400">AI will automatically respond to guest webchat messages</p>
          </div>
          <Switch checked={enabled} onCheckedChange={setEnabled} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Max Messages Without Human</label>
            <Input type="number" value={maxMessages} onChange={e => setMaxMessages(parseInt(e.target.value) || 20)}
              className="bg-slate-800 border-slate-700 text-white" />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Languages</label>
            <div className="flex gap-2">
              {['TR', 'EN', 'AR', 'RU', 'DE'].map(lang => (
                <Badge key={lang}
                  className={`cursor-pointer ${languages.includes(lang)
                    ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-slate-700 hover:bg-slate-600'}`}
                  onClick={() => setLanguages(prev =>
                    prev.includes(lang) ? prev.filter(l => l !== lang) : [...prev, lang]
                  )}>
                  {lang}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-400 mb-1 block">Escalation Keywords (comma-separated)</label>
          <Input value={keywords} onChange={e => setKeywords(e.target.value)}
            className="bg-slate-800 border-slate-700 text-white"
            placeholder="complaint, manager, lawyer, sikayet, mudur" />
          <p className="text-xs text-slate-500 mt-1">When these words are detected, AI will suggest human escalation</p>
        </div>

        <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700">
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
      </CardContent>
    </Card>
  );
}

function RoomRatesTab({ rates, slug, propertyId, refetch }) {
  const [showDialog, setShowDialog] = useState(false);
  const [editRate, setEditRate] = useState(null);
  const [form, setForm] = useState({
    room_type_code: '', room_type_name: '', description: '',
    base_price_per_night: '', currency: 'TRY', weekend_multiplier: '1.0',
    min_stay_nights: '1', max_guests: '2', refundable: true, breakfast_included: false
  });
  const [saving, setSaving] = useState(false);

  const openCreate = () => {
    setEditRate(null);
    setForm({
      room_type_code: '', room_type_name: '', description: '',
      base_price_per_night: '', currency: 'TRY', weekend_multiplier: '1.0',
      min_stay_nights: '1', max_guests: '2', refundable: true, breakfast_included: false
    });
    setShowDialog(true);
  };

  const openEdit = (rate) => {
    setEditRate(rate);
    setForm({
      room_type_code: rate.room_type_code,
      room_type_name: rate.room_type_name || '',
      description: rate.description || '',
      base_price_per_night: String(rate.base_price_per_night || ''),
      currency: rate.currency || 'TRY',
      weekend_multiplier: String(rate.weekend_multiplier || '1.0'),
      min_stay_nights: String(rate.min_stay_nights || '1'),
      max_guests: String(rate.max_guests || '2'),
      refundable: rate.refundable !== false,
      breakfast_included: rate.breakfast_included || false,
    });
    setShowDialog(true);
  };

  const saveRate = async () => {
    setSaving(true);
    try {
      const data = {
        ...form,
        base_price_per_night: parseFloat(form.base_price_per_night),
        weekend_multiplier: parseFloat(form.weekend_multiplier),
        min_stay_nights: parseInt(form.min_stay_nights),
        max_guests: parseInt(form.max_guests),
      };
      if (editRate) {
        await aiSalesAPI.updateRoomRate(slug, propertyId, editRate.id, data);
        toast.success('Rate updated');
      } else {
        await aiSalesAPI.createRoomRate(slug, propertyId, data);
        toast.success('Rate created');
      }
      refetch();
      setShowDialog(false);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save');
    }
    setSaving(false);
  };

  const deleteRate = async (rateId) => {
    if (!window.confirm('Delete this rate?')) return;
    try {
      await aiSalesAPI.deleteRoomRate(slug, propertyId, rateId);
      toast.success('Rate deleted');
      refetch();
    } catch (e) {
      toast.error('Failed to delete');
    }
  };

  return (
    <Card className="bg-slate-900 border-slate-800 mt-4">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white flex items-center gap-2">
          <Bed className="w-5 h-5 text-emerald-400" /> Room Rates
        </CardTitle>
        <Button size="sm" onClick={openCreate} className="bg-emerald-600 hover:bg-emerald-700">
          <Plus className="w-4 h-4 mr-1" /> Add Rate
        </Button>
      </CardHeader>
      <CardContent>
        {rates.length === 0 ? (
          <p className="text-slate-400 text-center py-8">No room rates configured. Add rates for AI to quote prices.</p>
        ) : (
          <div className="space-y-3">
            {rates.map(rate => (
              <div key={rate.id} className="flex items-center justify-between p-4 bg-slate-800 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-white">{rate.room_type_name || rate.room_type_code}</p>
                    <Badge className="bg-slate-700 text-xs">{rate.room_type_code}</Badge>
                    {rate.breakfast_included && <Badge className="bg-amber-600/20 text-amber-400 text-xs">Breakfast</Badge>}
                    {!rate.is_active && <Badge className="bg-red-600/20 text-red-400 text-xs">Inactive</Badge>}
                  </div>
                  <p className="text-sm text-slate-400 mt-1">{rate.description}</p>
                  <div className="flex gap-4 mt-1 text-xs text-slate-500">
                    <span>{rate.base_price_per_night} {rate.currency}/night</span>
                    <span>Weekend: x{rate.weekend_multiplier}</span>
                    <span>Max: {rate.max_guests} guests</span>
                    <span>Min: {rate.min_stay_nights} night(s)</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => openEdit(rate)}>
                    <Pencil className="w-4 h-4 text-slate-400" />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => deleteRate(rate.id)}>
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-lg">
            <DialogHeader>
              <DialogTitle>{editRate ? 'Edit Room Rate' : 'New Room Rate'}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400">Code</label>
                  <Input value={form.room_type_code} disabled={!!editRate}
                    onChange={e => setForm(f => ({...f, room_type_code: e.target.value}))}
                    placeholder="standard" className="bg-slate-800 border-slate-700" />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Name</label>
                  <Input value={form.room_type_name}
                    onChange={e => setForm(f => ({...f, room_type_name: e.target.value}))}
                    placeholder="Standard Room" className="bg-slate-800 border-slate-700" />
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-400">Description</label>
                <Input value={form.description}
                  onChange={e => setForm(f => ({...f, description: e.target.value}))}
                  placeholder="Room description..." className="bg-slate-800 border-slate-700" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-slate-400">Base Price/Night</label>
                  <Input type="number" value={form.base_price_per_night}
                    onChange={e => setForm(f => ({...f, base_price_per_night: e.target.value}))}
                    className="bg-slate-800 border-slate-700" />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Currency</label>
                  <Select value={form.currency} onValueChange={v => setForm(f => ({...f, currency: v}))}>
                    <SelectTrigger className="bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="TRY">TRY</SelectItem>
                      <SelectItem value="USD">USD</SelectItem>
                      <SelectItem value="EUR">EUR</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-xs text-slate-400">Weekend Multiplier</label>
                  <Input type="number" step="0.05" value={form.weekend_multiplier}
                    onChange={e => setForm(f => ({...f, weekend_multiplier: e.target.value}))}
                    className="bg-slate-800 border-slate-700" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400">Min Stay (nights)</label>
                  <Input type="number" value={form.min_stay_nights}
                    onChange={e => setForm(f => ({...f, min_stay_nights: e.target.value}))}
                    className="bg-slate-800 border-slate-700" />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Max Guests</label>
                  <Input type="number" value={form.max_guests}
                    onChange={e => setForm(f => ({...f, max_guests: e.target.value}))}
                    className="bg-slate-800 border-slate-700" />
                </div>
              </div>
              <div className="flex gap-6">
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <Switch checked={form.breakfast_included}
                    onCheckedChange={v => setForm(f => ({...f, breakfast_included: v}))} />
                  Breakfast included
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <Switch checked={form.refundable}
                    onCheckedChange={v => setForm(f => ({...f, refundable: v}))} />
                  Refundable
                </label>
              </div>
              <Button onClick={saveRate} disabled={saving} className="w-full bg-emerald-600 hover:bg-emerald-700">
                {saving ? 'Saving...' : editRate ? 'Update Rate' : 'Create Rate'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}

function DiscountRulesTab({ rules, slug, propertyId, refetch }) {
  const [enabled, setEnabled] = useState(rules?.enabled || false);
  const [maxDiscount, setMaxDiscount] = useState(rules?.max_discount_percent || 10);
  const [minNights, setMinNights] = useState(rules?.min_nights_for_discount || 3);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setEnabled(rules?.enabled || false);
    setMaxDiscount(rules?.max_discount_percent || 10);
    setMinNights(rules?.min_nights_for_discount || 3);
  }, [rules]);

  const save = async () => {
    setSaving(true);
    try {
      await aiSalesAPI.updateDiscountRules(slug, propertyId, {
        enabled,
        max_discount_percent: maxDiscount,
        min_nights_for_discount: minNights,
      });
      toast.success('Discount rules saved');
      refetch();
    } catch (e) {
      toast.error('Failed to save');
    }
    setSaving(false);
  };

  return (
    <Card className="bg-slate-900 border-slate-800 mt-4">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <Percent className="w-5 h-5 text-amber-400" /> Discount Rules
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-slate-800 rounded-lg">
          <div>
            <p className="text-white font-medium">Enable Discounts</p>
            <p className="text-sm text-slate-400">Allow AI to offer discounts within rules</p>
          </div>
          <Switch checked={enabled} onCheckedChange={setEnabled} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Max Discount %</label>
            <Input type="number" value={maxDiscount} onChange={e => setMaxDiscount(parseInt(e.target.value) || 0)}
              className="bg-slate-800 border-slate-700 text-white" />
            <p className="text-xs text-slate-500 mt-1">AI will never exceed this percentage</p>
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Min Nights for Discount</label>
            <Input type="number" value={minNights} onChange={e => setMinNights(parseInt(e.target.value) || 1)}
              className="bg-slate-800 border-slate-700 text-white" />
            <p className="text-xs text-slate-500 mt-1">Guest must stay at least this many nights</p>
          </div>
        </div>

        <div className="p-3 bg-amber-900/20 border border-amber-800/30 rounded-lg">
          <div className="flex items-start gap-2">
            <Shield className="w-4 h-4 text-amber-400 mt-0.5" />
            <div>
              <p className="text-sm text-amber-300 font-medium">Safety Rule</p>
              <p className="text-xs text-amber-400/70">AI will never invent discounts. All discount decisions are validated against these rules via backend tools.</p>
            </div>
          </div>
        </div>

        <Button onClick={save} disabled={saving} className="bg-amber-600 hover:bg-amber-700">
          {saving ? 'Saving...' : 'Save Discount Rules'}
        </Button>
      </CardContent>
    </Card>
  );
}

function PoliciesTab({ policies, slug, propertyId, refetch }) {
  const [form, setForm] = useState({
    check_in_time: policies?.check_in_time || '14:00',
    check_out_time: policies?.check_out_time || '12:00',
    cancellation_policy_text: policies?.cancellation_policy_text || '',
    pets_allowed: policies?.pets_allowed || false,
    smoking_policy: policies?.smoking_policy || 'Non-smoking',
    parking_info: policies?.parking_info || '',
    location_info: policies?.location_info || '',
    contact_phone: policies?.contact_phone || '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm({
      check_in_time: policies?.check_in_time || '14:00',
      check_out_time: policies?.check_out_time || '12:00',
      cancellation_policy_text: policies?.cancellation_policy_text || '',
      pets_allowed: policies?.pets_allowed || false,
      smoking_policy: policies?.smoking_policy || 'Non-smoking',
      parking_info: policies?.parking_info || '',
      location_info: policies?.location_info || '',
      contact_phone: policies?.contact_phone || '',
    });
  }, [policies]);

  const save = async () => {
    setSaving(true);
    try {
      await aiSalesAPI.updatePolicies(slug, propertyId, form);
      toast.success('Policies saved');
      refetch();
    } catch (e) {
      toast.error('Failed to save');
    }
    setSaving(false);
  };

  return (
    <Card className="bg-slate-900 border-slate-800 mt-4">
      <CardHeader>
        <CardTitle className="text-white flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-400" /> Business Policies
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-400">These policies are included in the AI's knowledge. The AI will use them when answering guest questions.</p>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Check-in Time</label>
            <Input value={form.check_in_time}
              onChange={e => setForm(f => ({...f, check_in_time: e.target.value}))}
              className="bg-slate-800 border-slate-700 text-white" placeholder="14:00" />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Check-out Time</label>
            <Input value={form.check_out_time}
              onChange={e => setForm(f => ({...f, check_out_time: e.target.value}))}
              className="bg-slate-800 border-slate-700 text-white" placeholder="12:00" />
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-400 mb-1 block">Cancellation Policy</label>
          <Input value={form.cancellation_policy_text}
            onChange={e => setForm(f => ({...f, cancellation_policy_text: e.target.value}))}
            className="bg-slate-800 border-slate-700 text-white"
            placeholder="Free cancellation up to 48 hours..." />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Parking Info</label>
            <Input value={form.parking_info}
              onChange={e => setForm(f => ({...f, parking_info: e.target.value}))}
              className="bg-slate-800 border-slate-700 text-white" />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Contact Phone</label>
            <Input value={form.contact_phone}
              onChange={e => setForm(f => ({...f, contact_phone: e.target.value}))}
              className="bg-slate-800 border-slate-700 text-white" />
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-400 mb-1 block">Location Info</label>
          <Input value={form.location_info}
            onChange={e => setForm(f => ({...f, location_info: e.target.value}))}
            className="bg-slate-800 border-slate-700 text-white"
            placeholder="Located in Beyoglu, near Istiklal Street..." />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Smoking Policy</label>
            <Select value={form.smoking_policy}
              onValueChange={v => setForm(f => ({...f, smoking_policy: v}))}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Non-smoking">Non-smoking</SelectItem>
                <SelectItem value="Smoking areas available">Smoking areas available</SelectItem>
                <SelectItem value="Smoking allowed">Smoking allowed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <Switch checked={form.pets_allowed}
                onCheckedChange={v => setForm(f => ({...f, pets_allowed: v}))} />
              Pets allowed
            </label>
          </div>
        </div>

        <Button onClick={save} disabled={saving} className="bg-blue-600 hover:bg-blue-700">
          {saving ? 'Saving...' : 'Save Policies'}
        </Button>
      </CardContent>
    </Card>
  );
}
