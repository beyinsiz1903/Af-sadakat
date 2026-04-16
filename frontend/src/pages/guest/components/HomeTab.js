import React from 'react';
import { Card, CardContent } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { ChevronRight, Star, Megaphone, LogOut, BedDouble, ClipboardCheck } from 'lucide-react';
import { statusColors } from '../../../lib/utils';
import { categoryConfig } from '../constants';
import { useGuest } from '../GuestContext';

export default function HomeTab({ requests, activeServices, announcements, onOpenService, onSetTab, onShowSurvey, onShowCheckout, onShowReservation, onShowCheckin }) {
  const { lang, t } = useGuest();

  const activeKeys = activeServices.length > 0
    ? activeServices.map(s => s.key)
    : Object.keys(categoryConfig);

  const primaryKeys = ['housekeeping','room_service','maintenance','spa','transport','laundry','wakeup','reception'];
  const primary = primaryKeys.filter(k => activeKeys.includes(k));
  const secondary = activeKeys.filter(k => !primaryKeys.includes(k));

  const renderGrid = (keys) => (
    <div className="grid grid-cols-4 gap-2">
      {keys.map(key => {
        const cfg = categoryConfig[key];
        if (!cfg) return null;
        const Icon = cfg.icon;
        return (
          <button key={key} onClick={() => onOpenService(key)} className={`p-2.5 rounded-xl border border-[hsl(var(--border))] ${cfg.bg} hover:scale-105 transition-all text-center`}>
            <Icon className={`w-5 h-5 mx-auto mb-1 ${cfg.color}`} />
            <span className="text-[10px] font-medium leading-tight block">{lang === 'tr' ? cfg.labelTr : cfg.label}</span>
          </button>
        );
      })}
    </div>
  );

  const activeRequests = requests.filter(r => r.status !== 'CLOSED');

  return (
    <div className="space-y-3">
      {announcements.length > 0 && (
        <div className="mb-4">
          {announcements.map(ann => (
            <div key={ann.id} className="flex items-start gap-2 bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)] rounded-lg px-3 py-2 mb-2">
              <Megaphone className="w-4 h-4 text-[hsl(var(--primary))] flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold">{lang === 'tr' && ann.title_tr ? ann.title_tr : ann.title}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">{lang === 'tr' && ann.body_tr ? ann.body_tr : ann.body}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {primary.length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <h3 className="font-semibold mb-3 text-sm">{t('Quick Services', 'Hizli Servisler')}</h3>
            {renderGrid(primary)}
          </CardContent>
        </Card>
      )}

      {secondary.length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <h3 className="font-semibold mb-3 text-sm">{t('More Services', 'Diger Servisler')}</h3>
            {renderGrid(secondary)}
          </CardContent>
        </Card>
      )}

      {activeRequests.length > 0 && (
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">{t('Active Requests', 'Aktif Talepler')}</h3>
              <Badge className="text-xs">{activeRequests.length}</Badge>
            </div>
            {activeRequests.slice(0, 3).map(req => {
              const cat = categoryConfig[req.category] || categoryConfig.other;
              const Icon = cat.icon;
              return (
                <div key={req.id} className="flex items-center gap-2 py-2 border-b border-[hsl(var(--border))] last:border-0">
                  <Icon className={`w-4 h-4 ${cat.color}`} />
                  <span className="text-xs flex-1 truncate">{req.description}</span>
                  <Badge className={`${statusColors[req.status]} text-[10px]`}>{req.status.replace('_', ' ')}</Badge>
                </div>
              );
            })}
            <Button size="sm" variant="ghost" className="w-full mt-2 text-xs" onClick={() => onSetTab('requests')}>
              {t('View All', 'Tumunu Gor')} <ChevronRight className="w-3 h-3 ml-1" />
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-3 gap-2">
        <button onClick={onShowCheckin} className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] hover:scale-105 transition-all text-center">
          <ClipboardCheck className="w-5 h-5 mx-auto mb-1 text-blue-400" />
          <span className="text-[10px] font-medium">{t('Check-in', 'Check-in')}</span>
        </button>
        <button onClick={onShowReservation} className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] hover:scale-105 transition-all text-center">
          <BedDouble className="w-5 h-5 mx-auto mb-1 text-purple-400" />
          <span className="text-[10px] font-medium">{t('Book Room', 'Oda Ayirt')}</span>
        </button>
        <button onClick={onShowCheckout} className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] hover:scale-105 transition-all text-center">
          <LogOut className="w-5 h-5 mx-auto mb-1 text-orange-400" />
          <span className="text-[10px] font-medium">{t('Check-out', 'Cikis')}</span>
        </button>
      </div>

      <Button variant="outline" className="w-full text-sm" onClick={onShowSurvey}>
        <Star className="w-4 h-4 mr-2" /> {t('Rate Your Stay', 'Konaklamanizi Degerlendirin')}
      </Button>
    </div>
  );
}
