import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { abTestingAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  FlaskConical, Play, Square, Pause, Plus, Trash2, BarChart3,
  Users, Zap, TrendingUp, Award, Eye, ChevronDown, ChevronUp,
  Target, ArrowRight, Trophy
} from 'lucide-react';

const STATUS_COLORS = {
  draft: 'bg-gray-500/10 text-gray-400',
  running: 'bg-emerald-500/10 text-emerald-400',
  paused: 'bg-amber-500/10 text-amber-400',
  completed: 'bg-blue-500/10 text-blue-400',
};

const STATUS_LABELS = {
  draft: 'Taslak',
  running: 'Calisyor',
  paused: 'Duraklatildi',
  completed: 'Tamamlandi',
};

export default function ABTestingPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [createDialog, setCreateDialog] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [newExp, setNewExp] = useState({
    name: '', description: '', hypothesis: '', feature_area: 'general',
    target_sample_size: 100, primary_metric: 'conversion_rate',
    variants: [
      { name: 'control', traffic_percent: 50, description: '' },
      { name: 'variant_a', traffic_percent: 50, description: '' },
    ],
  });

  const { data: stats } = useQuery({
    queryKey: ['ab-stats', tenant?.slug],
    queryFn: () => abTestingAPI.getStats(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: experimentsData } = useQuery({
    queryKey: ['ab-experiments', tenant?.slug],
    queryFn: () => abTestingAPI.listExperiments(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: resultsCache, refetch: refetchResults } = useQuery({
    queryKey: ['ab-results', tenant?.slug, expandedId],
    queryFn: () => abTestingAPI.getResults(tenant?.slug, expandedId).then(r => r.data),
    enabled: !!tenant?.slug && !!expandedId,
  });

  const createExperiment = useMutation({
    mutationFn: (data) => abTestingAPI.createExperiment(tenant?.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ab-experiments'] });
      queryClient.invalidateQueries({ queryKey: ['ab-stats'] });
      setCreateDialog(false);
      toast.success('Deney olusturuldu');
      setNewExp({ name: '', description: '', hypothesis: '', feature_area: 'general', target_sample_size: 100, primary_metric: 'conversion_rate', variants: [{ name: 'control', traffic_percent: 50, description: '' }, { name: 'variant_a', traffic_percent: 50, description: '' }] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Hata'),
  });

  const startExperiment = useMutation({
    mutationFn: (id) => abTestingAPI.startExperiment(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ab-experiments'] }); queryClient.invalidateQueries({ queryKey: ['ab-stats'] }); toast.success('Deney baslatildi'); },
  });

  const stopExperiment = useMutation({
    mutationFn: (id) => abTestingAPI.stopExperiment(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ab-experiments'] }); queryClient.invalidateQueries({ queryKey: ['ab-stats'] }); toast.success('Deney durduruldu'); },
  });

  const pauseExperiment = useMutation({
    mutationFn: (id) => abTestingAPI.pauseExperiment(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ab-experiments'] }); toast.success('Deney duraklatildi'); },
  });

  const deleteExperiment = useMutation({
    mutationFn: (id) => abTestingAPI.deleteExperiment(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ab-experiments'] }); queryClient.invalidateQueries({ queryKey: ['ab-stats'] }); toast.success('Deney silindi'); },
  });

  const experiments = experimentsData?.data || [];

  const addVariant = () => {
    const variants = [...newExp.variants, { name: `variant_${String.fromCharCode(97 + newExp.variants.length - 1)}`, traffic_percent: 0, description: '' }];
    setNewExp({ ...newExp, variants });
  };

  const updateVariant = (index, field, value) => {
    const variants = [...newExp.variants];
    variants[index] = { ...variants[index], [field]: field === 'traffic_percent' ? parseInt(value) || 0 : value };
    setNewExp({ ...newExp, variants });
  };

  const removeVariant = (index) => {
    if (newExp.variants.length <= 2) return;
    const variants = newExp.variants.filter((_, i) => i !== index);
    setNewExp({ ...newExp, variants });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">A/B Testing</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Deneyler olusturun, varyantlari test edin ve sonuclari analiz edin</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Toplam Deney</p>
                <p className="text-2xl font-bold">{stats?.total_experiments || 0}</p>
              </div>
              <FlaskConical className="w-8 h-8 text-purple-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Aktif Deney</p>
                <p className="text-2xl font-bold text-emerald-400">{stats?.running || 0}</p>
              </div>
              <Play className="w-8 h-8 text-emerald-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Toplam Katilimci</p>
                <p className="text-2xl font-bold">{stats?.total_participants || 0}</p>
              </div>
              <Users className="w-8 h-8 text-blue-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Izlenen Olay</p>
                <p className="text-2xl font-bold">{stats?.total_events_tracked || 0}</p>
              </div>
              <Zap className="w-8 h-8 text-amber-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Create Experiment */}
      <div className="flex justify-end">
        <Dialog open={createDialog} onOpenChange={setCreateDialog}>
          <DialogTrigger asChild>
            <Button><Plus className="w-4 h-4 mr-1" /> Yeni Deney Olustur</Button>
          </DialogTrigger>
          <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-lg max-h-[80vh] overflow-y-auto">
            <DialogHeader><DialogTitle>Yeni A/B Deney Olustur</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Deney Adi" value={newExp.name} onChange={e => setNewExp({...newExp, name: e.target.value})} />
              <Input placeholder="Aciklama" value={newExp.description} onChange={e => setNewExp({...newExp, description: e.target.value})} />
              <Input placeholder="Hipotez" value={newExp.hypothesis} onChange={e => setNewExp({...newExp, hypothesis: e.target.value})} />
              <div className="flex gap-2">
                <select className="flex-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm" value={newExp.feature_area} onChange={e => setNewExp({...newExp, feature_area: e.target.value})}>
                  <option value="general">Genel</option>
                  <option value="guest_experience">Misafir Deneyimi</option>
                  <option value="room_service">Oda Servisi</option>
                  <option value="loyalty">Sadakat</option>
                  <option value="communication">Iletisim</option>
                  <option value="booking">Rezervasyon</option>
                  <option value="pricing">Fiyatlandirma</option>
                </select>
                <Input type="number" placeholder="Hedef Orneklem" className="w-32" value={newExp.target_sample_size} onChange={e => setNewExp({...newExp, target_sample_size: parseInt(e.target.value) || 0})} />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Varyantlar</p>
                  <Button size="sm" variant="outline" onClick={addVariant}><Plus className="w-3 h-3 mr-1" /> Ekle</Button>
                </div>
                {newExp.variants.map((v, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <Input placeholder="Varyant adi" value={v.name} onChange={e => updateVariant(i, 'name', e.target.value)} className="flex-1" />
                    <Input type="number" placeholder="%" value={v.traffic_percent} onChange={e => updateVariant(i, 'traffic_percent', e.target.value)} className="w-20" />
                    {newExp.variants.length > 2 && (
                      <Button size="sm" variant="ghost" onClick={() => removeVariant(i)}><Trash2 className="w-3 h-3 text-red-400" /></Button>
                    )}
                  </div>
                ))}
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Toplam: {newExp.variants.reduce((s, v) => s + (v.traffic_percent || 0), 0)}% (100% olmali)</p>
              </div>

              <Button onClick={() => createExperiment.mutate(newExp)} disabled={!newExp.name || createExperiment.isPending}>
                Deney Olustur
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Experiments List */}
      <div className="space-y-4">
        {experiments.map(exp => (
          <Card key={exp.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                    <FlaskConical className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{exp.name}</h3>
                      <Badge className={STATUS_COLORS[exp.status]}>{STATUS_LABELS[exp.status]}</Badge>
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{exp.description}</p>
                    {exp.hypothesis && <p className="text-xs text-blue-400 mt-0.5 italic">Hipotez: {exp.hypothesis}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {exp.status === 'draft' && (
                    <Button size="sm" variant="outline" onClick={() => startExperiment.mutate(exp.id)}>
                      <Play className="w-4 h-4 mr-1" /> Baslat
                    </Button>
                  )}
                  {exp.status === 'running' && (
                    <>
                      <Button size="sm" variant="outline" onClick={() => pauseExperiment.mutate(exp.id)}>
                        <Pause className="w-4 h-4" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => stopExperiment.mutate(exp.id)}>
                        <Square className="w-4 h-4 mr-1" /> Durdur
                      </Button>
                    </>
                  )}
                  {exp.status === 'paused' && (
                    <Button size="sm" variant="outline" onClick={() => startExperiment.mutate(exp.id)}>
                      <Play className="w-4 h-4 mr-1" /> Devam
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => setExpandedId(expandedId === exp.id ? null : exp.id)}>
                    {expandedId === exp.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => { if(window.confirm('Bu deneyi silmek istediginize emin misiniz?')) deleteExperiment.mutate(exp.id); }}>
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </Button>
                </div>
              </div>

              {/* Meta info */}
              <div className="flex items-center gap-4 mt-3 text-xs text-[hsl(var(--muted-foreground))]">
                <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {exp.total_participants} katilimci</span>
                <span className="flex items-center gap-1"><Target className="w-3 h-3" /> Hedef: {exp.target_sample_size}</span>
                <Badge variant="outline" className="text-[10px]">{exp.feature_area}</Badge>
                <Badge variant="outline" className="text-[10px]">{exp.primary_metric}</Badge>
              </div>

              {/* Variant bars */}
              <div className="flex gap-1 mt-3 h-3 rounded-full overflow-hidden">
                {exp.variants?.map((v, i) => (
                  <div key={v.name} className={`h-full transition-all ${i === 0 ? 'bg-blue-500' : i === 1 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                    style={{ width: `${v.traffic_percent}%` }}
                    title={`${v.name}: ${v.traffic_percent}%`} />
                ))}
              </div>
              <div className="flex gap-3 mt-1">
                {exp.variants?.map((v, i) => (
                  <span key={v.name} className="text-[10px] text-[hsl(var(--muted-foreground))] flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-full ${i === 0 ? 'bg-blue-500' : i === 1 ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    {v.name} ({v.traffic_percent}%)
                  </span>
                ))}
              </div>

              {/* Expanded Results */}
              {expandedId === exp.id && resultsCache && (
                <div className="mt-4 pt-4 border-t border-[hsl(var(--border))]">
                  <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4" /> Deney Sonuclari
                    {resultsCache.winner && (
                      <Badge className="bg-emerald-500/10 text-emerald-400">
                        <Trophy className="w-3 h-3 mr-1" /> Kazanan: {resultsCache.winner}
                      </Badge>
                    )}
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {resultsCache.results?.map((r, i) => (
                      <div key={r.variant_name} className={`p-3 rounded-lg border ${
                        resultsCache.winner === r.variant_name ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-[hsl(var(--border))]'
                      }`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className={`w-3 h-3 rounded-full ${i === 0 ? 'bg-blue-500' : i === 1 ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                            <span className="font-medium text-sm">{r.variant_name}</span>
                          </div>
                          {resultsCache.winner === r.variant_name && <Trophy className="w-4 h-4 text-emerald-400" />}
                        </div>
                        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{r.description}</p>
                        <div className="grid grid-cols-2 gap-2 mt-2">
                          <div>
                            <p className="text-xs text-[hsl(var(--muted-foreground))]">Katilimci</p>
                            <p className="font-semibold">{r.participants}</p>
                          </div>
                          <div>
                            <p className="text-xs text-[hsl(var(--muted-foreground))]">Donusum</p>
                            <p className="font-semibold text-[hsl(var(--primary))]">{r.conversion_rate}%</p>
                          </div>
                          <div>
                            <p className="text-xs text-[hsl(var(--muted-foreground))]">Olaylar</p>
                            <p className="font-semibold">{r.total_events}</p>
                          </div>
                          <div>
                            <p className="text-xs text-[hsl(var(--muted-foreground))]">Ort. Deger</p>
                            <p className="font-semibold">{r.avg_value}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {experiments.length === 0 && (
          <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
            <CardContent className="p-8 text-center">
              <FlaskConical className="w-12 h-12 text-[hsl(var(--muted-foreground))] mx-auto mb-3 opacity-50" />
              <p className="text-[hsl(var(--muted-foreground))]">Henuz deney olusturulmamis</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Yeni bir A/B deney olusturarak baslayabilirsiniz</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
