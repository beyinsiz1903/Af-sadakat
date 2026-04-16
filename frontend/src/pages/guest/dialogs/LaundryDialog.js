import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Shirt, Loader2 } from 'lucide-react';
import { useGuest } from '../GuestContext';

export default function LaundryDialog({ open, onOpenChange, laundryForm, setLaundryForm, submitting, onSubmit }) {
  const { t } = useGuest();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md">
        <DialogHeader><DialogTitle>{t('Laundry Service', 'Camasir Servisi')}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <Select value={laundryForm.service_type} onValueChange={(v) => setLaundryForm({...laundryForm, service_type: v})}>
            <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="regular">{t('Regular Wash', 'Normal Yikama')}</SelectItem>
              <SelectItem value="express">{t('Express (3h)', 'Ekspres (3 saat)')}</SelectItem>
              <SelectItem value="dry_clean">{t('Dry Cleaning', 'Kuru Temizleme')}</SelectItem>
              <SelectItem value="ironing">{t('Ironing Only', 'Sadece Utu')}</SelectItem>
            </SelectContent>
          </Select>
          <Textarea value={laundryForm.items_description} onChange={(e) => setLaundryForm({...laundryForm, items_description: e.target.value})}
            placeholder={t('Describe items...', 'Kiyafetlerinizi tanimlayiniz...')} className="bg-[hsl(var(--secondary))]" />
          <Button className="w-full" onClick={onSubmit} disabled={submitting}>
            {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Shirt className="w-4 h-4 mr-2" />}
            {t('Request Laundry', 'Camasir Talep Et')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
