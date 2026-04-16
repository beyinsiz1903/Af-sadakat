import React from 'react';
import { ChevronRight } from 'lucide-react';
import { categoryConfig } from '../constants';
import { useGuest } from '../GuestContext';

export default function ServicesTab({ activeServices, onOpenService }) {
  const { lang, t } = useGuest();
  const keys = activeServices.length > 0 ? activeServices.map(s => s.key) : Object.keys(categoryConfig);

  return (
    <div className="space-y-3">
      <h3 className="font-semibold">{t('All Services', 'Tum Servisler')}</h3>
      {keys.map(key => {
        const cfg = categoryConfig[key];
        if (!cfg) return null;
        const Icon = cfg.icon;
        return (
          <button key={key} onClick={() => onOpenService(key)}
            className="w-full flex items-center gap-3 p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] hover:border-[hsl(var(--primary)/0.3)] transition-all">
            <div className={`w-10 h-10 rounded-lg ${cfg.bg} flex items-center justify-center`}>
              <Icon className={`w-5 h-5 ${cfg.color}`} />
            </div>
            <div className="flex-1 text-left">
              <p className="text-sm font-medium">{lang === 'tr' ? cfg.labelTr : cfg.label}</p>
            </div>
            <ChevronRight className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
          </button>
        );
      })}
    </div>
  );
}
