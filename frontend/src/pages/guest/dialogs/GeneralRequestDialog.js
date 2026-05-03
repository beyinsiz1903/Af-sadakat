import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Textarea } from '../../../components/ui/textarea';
import { Badge } from '../../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Send, Loader2, Camera, Paperclip } from 'lucide-react';
import { categoryConfig } from '../constants';
import { useGuest } from '../GuestContext';

export default function GeneralRequestDialog({
  open, onOpenChange, form, setForm,
  guestName, setGuestName, guestPhone, setGuestPhone,
  uploadFiles, setUploadFiles, submitting, onSubmit
}) {
  const { lang, t } = useGuest();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('Submit Request', 'Talep Gonder')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(categoryConfig).slice(0, 8).map(([key, cfg]) => {
              const Icon = cfg.icon;
              return (
                <button key={key} type="button" onClick={() => setForm({...form, category: key})}
                  className={`p-2 rounded-lg border text-center transition-all ${form.category === key ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)]' : 'border-[hsl(var(--border))]'}`}>
                  <Icon className={`w-4 h-4 mx-auto mb-0.5 ${cfg.color}`} />
                  <span className="text-[9px] font-medium">{t(cfg.label, cfg.labelTr)}</span>
                </button>
              );
            })}
          </div>
          <Textarea value={form.description} onChange={(e) => setForm({...form, description: e.target.value})}
            placeholder={t('Describe what you need...', 'Neye ihtiyaciniz oldugunu yazin...')}
            className="bg-[hsl(var(--secondary))] border-[hsl(var(--border))] min-h-[80px]" />
          <div className="grid grid-cols-2 gap-2">
            <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} placeholder={t('Your name', 'Adiniz')} className="bg-[hsl(var(--secondary))]" />
            <Input value={guestPhone} onChange={(e) => setGuestPhone(e.target.value)} placeholder={t('Phone', 'Telefon')} className="bg-[hsl(var(--secondary))]" />
          </div>
          <Select value={form.priority} onValueChange={(v) => setForm({...form, priority: v})}>
            <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="low">{t('Low Priority', 'Dusuk Oncelik')}</SelectItem>
              <SelectItem value="normal">{t('Normal', 'Normal')}</SelectItem>
              <SelectItem value="high">{t('High Priority', 'Yuksek Oncelik')}</SelectItem>
              <SelectItem value="urgent">{t('Urgent', 'Acil')}</SelectItem>
            </SelectContent>
          </Select>
          <div>
            <label className="flex items-center gap-2 cursor-pointer text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] transition-colors">
              <Camera className="w-4 h-4" />
              <span>{t('Attach Photo/File', 'Fotograf/Dosya Ekle')}</span>
              <input type="file" multiple accept="image/*,.pdf,.doc,.docx" className="hidden"
                onChange={(e) => setUploadFiles(Array.from(e.target.files || []))} />
            </label>
            {uploadFiles.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {uploadFiles.map((f, i) => (
                  <Badge key={i} variant="outline" className="text-[10px] gap-1">
                    <Paperclip className="w-3 h-3" />{f.name}
                    <button onClick={() => setUploadFiles(uploadFiles.filter((_, idx) => idx !== i))} className="ml-1 text-red-400">×</button>
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={!form.description.trim() || submitting}>
            {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
            {t('Submit', 'Gonder')}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
