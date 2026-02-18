import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { slaAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Shield, Clock, AlertTriangle, CheckCircle2, Zap, Users, FileText, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

export default function SLAManagementPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('rules');
  const [showRuleDialog, setShowRuleDialog] = useState(false);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [ruleForm, setRuleForm] = useState({ category: 'housekeeping', department_code: 'HK', priority: 'normal', response_time_minutes: 15, resolution_time_minutes: 60, escalation_after_minutes: 30, auto_escalation_enabled: true });
  const [templateForm, setTemplateForm] = useState({ name: '', category: '', body_tr: '', body_en: '', shortcut: '' });

  const { data: rules = [] } = useQuery({
    queryKey: ['sla-rules', tenant?.slug],
    queryFn: () => slaAPI.listRules(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: stats } = useQuery({
    queryKey: ['sla-stats', tenant?.slug],
    queryFn: () => slaAPI.getStats(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: templates = [] } = useQuery({
    queryKey: ['response-templates', tenant?.slug],
    queryFn: () => slaAPI.listResponseTemplates(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: assignmentRules = [] } = useQuery({
    queryKey: ['assignment-rules', tenant?.slug],
    queryFn: () => slaAPI.listAssignmentRules(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const createRule = useMutation({
    mutationFn: (data) => slaAPI.createRule(tenant?.slug, data),
    onSuccess: () => { queryClient.invalidateQueries(['sla-rules']); setShowRuleDialog(false); toast.success('SLA Rule created'); },
  });

  const deleteRule = useMutation({
    mutationFn: (id) => slaAPI.deleteRule(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries(['sla-rules']); toast.success('Deleted'); },
  });

  const createTemplate = useMutation({
    mutationFn: (data) => slaAPI.createResponseTemplate(tenant?.slug, data),
    onSuccess: () => { queryClient.invalidateQueries(['response-templates']); setShowTemplateDialog(false); toast.success('Template created'); },
  });

  const deleteTemplate = useMutation({
    mutationFn: (id) => slaAPI.deleteResponseTemplate(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries(['response-templates']); toast.success('Deleted'); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">SLA & Workflow Management</h1>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: 'Compliance Rate', value: `${stats.compliance_rate}%`, icon: Shield, color: stats.compliance_rate > 90 ? 'text-emerald-400' : 'text-amber-400' },
            { label: 'Avg Response', value: `${stats.avg_response_minutes}m`, icon: Clock, color: 'text-blue-400' },
            { label: 'Avg Resolution', value: `${stats.avg_resolution_minutes}m`, icon: Zap, color: 'text-purple-400' },
            { label: 'Active Breaches', value: stats.active_breaches, icon: AlertTriangle, color: stats.active_breaches > 0 ? 'text-red-400' : 'text-emerald-400' },
            { label: 'Total Requests', value: stats.total_requests, icon: CheckCircle2, color: 'text-gray-400' },
          ].map((s, i) => {
            const Icon = s.icon;
            return (
              <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4 text-center">
                  <Icon className={`w-5 h-5 mx-auto mb-1 ${s.color}`} />
                  <p className="text-xl font-bold">{s.value}</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{s.label}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2">
        {[{id:'rules', label:'SLA Rules', icon: Shield}, {id:'templates', label:'Response Templates', icon: FileText}, {id:'assignment', label:'Auto-Assignment', icon: Users}].map(t => (
          <Button key={t.id} variant={tab === t.id ? 'default' : 'outline'} size="sm" onClick={() => setTab(t.id)}>
            <t.icon className="w-4 h-4 mr-1" />{t.label}
          </Button>
        ))}
      </div>

      {tab === 'rules' && (
        <div className="space-y-3">
          <Button onClick={() => setShowRuleDialog(true)}>+ New SLA Rule</Button>
          {rules.map(rule => (
            <Card key={rule.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{rule.category}</Badge>
                      <Badge variant="outline">{rule.department_code}</Badge>
                      <Badge variant="outline">{rule.priority}</Badge>
                    </div>
                    <div className="flex gap-4 mt-2 text-xs text-[hsl(var(--muted-foreground))]">
                      <span>Response: <strong>{rule.response_time_minutes}m</strong></span>
                      <span>Resolution: <strong>{rule.resolution_time_minutes}m</strong></span>
                      <span>Escalate after: <strong>{rule.escalation_after_minutes}m</strong></span>
                      <span>Auto-escalation: <strong>{rule.auto_escalation_enabled ? 'ON' : 'OFF'}</strong></span>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => deleteRule.mutate(rule.id)}><Trash2 className="w-4 h-4 text-red-400" /></Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {tab === 'templates' && (
        <div className="space-y-3">
          <Button onClick={() => setShowTemplateDialog(true)}>+ New Template</Button>
          {templates.map(tpl => (
            <Card key={tpl.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">{tpl.name}</span>
                      {tpl.shortcut && <Badge variant="outline" className="text-[10px]">{tpl.shortcut}</Badge>}
                      <Badge variant="outline">{tpl.category}</Badge>
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{tpl.body_en}</p>
                    {tpl.body_tr && <p className="text-xs text-[hsl(var(--muted-foreground))] italic">{tpl.body_tr}</p>}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => deleteTemplate.mutate(tpl.id)}><Trash2 className="w-4 h-4 text-red-400" /></Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {tab === 'assignment' && (
        <div className="space-y-3">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">{assignmentRules.length} auto-assignment rules configured.</p>
          {assignmentRules.map(rule => (
            <Card key={rule.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <p className="text-sm font-medium">{rule.name}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">{rule.category} / {rule.department_code} → {rule.assign_to_user_name || 'Unassigned'}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* SLA Rule Dialog */}
      <Dialog open={showRuleDialog} onOpenChange={setShowRuleDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <DialogHeader><DialogTitle>New SLA Rule</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Select value={ruleForm.category} onValueChange={(v) => setRuleForm({...ruleForm, category: v})}>
              <SelectTrigger><SelectValue placeholder="Category" /></SelectTrigger>
              <SelectContent>
                {['housekeeping','maintenance','room_service','reception','laundry','spa','transport','bellboy','key_access','complaint'].map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
            <Input value={ruleForm.department_code} onChange={(e) => setRuleForm({...ruleForm, department_code: e.target.value})} placeholder="Department Code (HK, TECH, FB...)" />
            <div className="grid grid-cols-3 gap-2">
              <div><label className="text-xs">Response (min)</label><Input type="number" value={ruleForm.response_time_minutes} onChange={(e) => setRuleForm({...ruleForm, response_time_minutes: +e.target.value})} /></div>
              <div><label className="text-xs">Resolution (min)</label><Input type="number" value={ruleForm.resolution_time_minutes} onChange={(e) => setRuleForm({...ruleForm, resolution_time_minutes: +e.target.value})} /></div>
              <div><label className="text-xs">Escalate (min)</label><Input type="number" value={ruleForm.escalation_after_minutes} onChange={(e) => setRuleForm({...ruleForm, escalation_after_minutes: +e.target.value})} /></div>
            </div>
            <Button className="w-full" onClick={() => createRule.mutate(ruleForm)}>Create Rule</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Template Dialog */}
      <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <DialogHeader><DialogTitle>New Response Template</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input value={templateForm.name} onChange={(e) => setTemplateForm({...templateForm, name: e.target.value})} placeholder="Template name" />
            <Input value={templateForm.category} onChange={(e) => setTemplateForm({...templateForm, category: e.target.value})} placeholder="Category" />
            <Input value={templateForm.shortcut} onChange={(e) => setTemplateForm({...templateForm, shortcut: e.target.value})} placeholder="Shortcut (e.g. /towels)" />
            <Textarea value={templateForm.body_en} onChange={(e) => setTemplateForm({...templateForm, body_en: e.target.value})} placeholder="English text" />
            <Textarea value={templateForm.body_tr} onChange={(e) => setTemplateForm({...templateForm, body_tr: e.target.value})} placeholder="Turkish text" />
            <Button className="w-full" onClick={() => createTemplate.mutate(templateForm)}>Create Template</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
