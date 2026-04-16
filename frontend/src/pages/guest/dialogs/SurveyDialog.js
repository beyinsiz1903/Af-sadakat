import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Textarea } from '../../../components/ui/textarea';
import { Star, Loader2 } from 'lucide-react';
import { useGuest } from '../GuestContext';

export default function SurveyDialog({ open, onOpenChange, surveyForm, setSurveyForm, submitting, onSubmit }) {
  const { t } = useGuest();

  const criteria = [
    { key: 'overall_rating', label: t('Overall', 'Genel') },
    { key: 'cleanliness_rating', label: t('Cleanliness', 'Temizlik') },
    { key: 'service_rating', label: t('Service', 'Hizmet') },
    { key: 'food_rating', label: t('Food & Dining', 'Yemek') },
    { key: 'comfort_rating', label: t('Comfort', 'Konfor') },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{t('Rate Your Stay', 'Konaklamanizi Degerlendirin')}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          {criteria.map(({ key, label }) => (
            <div key={key}>
              <p className="text-xs font-medium mb-1">{label}</p>
              <div className="flex gap-1">
                {[1,2,3,4,5].map(n => (
                  <button key={n} onClick={() => setSurveyForm({...surveyForm, [key]: n})}>
                    <Star className={`w-7 h-7 ${surveyForm[key] >= n ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />
                  </button>
                ))}
              </div>
            </div>
          ))}
          <div>
            <p className="text-xs font-medium mb-1">{t('Would you recommend us?', 'Bizi tavsiye eder misiniz?')}</p>
            <div className="flex gap-2">
              <Button size="sm" variant={surveyForm.would_recommend === true ? 'default' : 'outline'} onClick={() => setSurveyForm({...surveyForm, would_recommend: true})}>
                {t('Yes', 'Evet')} 👍
              </Button>
              <Button size="sm" variant={surveyForm.would_recommend === false ? 'default' : 'outline'} onClick={() => setSurveyForm({...surveyForm, would_recommend: false})}>
                {t('No', 'Hayir')} 👎
              </Button>
            </div>
          </div>
          <Textarea value={surveyForm.comments} onChange={(e) => setSurveyForm({...surveyForm, comments: e.target.value})}
            placeholder={t('Any comments?', 'Yorumlariniz...')} className="bg-[hsl(var(--secondary))]" />
          <Button className="w-full" onClick={onSubmit} disabled={submitting}>
            {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Star className="w-4 h-4 mr-2" />}
            {t('Submit Survey', 'Anketi Gonder')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
