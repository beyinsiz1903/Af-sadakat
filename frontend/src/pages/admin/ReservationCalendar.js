import React, { useMemo, useState, useEffect } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { useTranslation } from 'react-i18next';
import { reservationsAPI } from '../../lib/api';
import { useAuthStore } from '../../lib/store';

const localizer = momentLocalizer(moment);

const STATUS_COLORS = {
  CONFIRMED: '#16a34a',
  PENDING: '#f59e0b',
  CHECKED_IN: '#2563eb',
  CHECKED_OUT: '#6b7280',
  CANCELLED: '#dc2626',
  NO_SHOW: '#7c3aed',
};

export default function ReservationCalendar() {
  const { t } = useTranslation();
  const tenant = useAuthStore((s) => s.tenant);
  const slug = tenant?.slug;
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    setError(null);
    reservationsAPI.list(slug, { limit: 500 })
      .then((res) => {
        const payload = res?.data;
        const data = Array.isArray(payload?.data)
          ? payload.data
          : Array.isArray(payload?.items)
            ? payload.items
            : Array.isArray(payload)
              ? payload
              : [];
        setItems(data);
      })
      .catch((e) => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  const events = useMemo(() => {
    return items
      .map((r) => {
        const startStr = r.check_in || r.start_date || r.start_at || r.created_at;
        const endStr = r.check_out || r.end_date || r.end_at || startStr;
        if (!startStr) return null;
        const start = new Date(startStr);
        const end = new Date(endStr);
        if (isNaN(start.getTime())) return null;
        const safeEnd = isNaN(end.getTime()) ? start : end;
        return {
          id: r.id,
          title: `${r.guest_name || 'Guest'} • ${r.confirmation_code || ''}`.trim(),
          start,
          end: safeEnd,
          resource: r,
        };
      })
      .filter(Boolean);
  }, [items]);

  const eventStyleGetter = (event) => {
    const color = STATUS_COLORS[event.resource?.status] || '#3b82f6';
    return {
      style: {
        backgroundColor: color, borderRadius: '4px', border: 'none',
        color: 'white', fontSize: '12px', padding: '2px 4px',
      },
    };
  };

  const messages = {
    today: t('calendar.today'), previous: t('calendar.previous'), next: t('calendar.next'),
    month: t('calendar.month'), week: t('calendar.week'), day: t('calendar.day'),
    agenda: t('calendar.agenda'), noEventsInRange: t('calendar.noEvents'),
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">{t('calendar.title')}</h1>
        {loading && <span className="text-sm text-gray-500">{t('common.loading')}</span>}
      </div>
      {error && <div className="mb-3 p-2 bg-red-50 text-red-700 text-sm rounded">{error}</div>}
      <div className="bg-white rounded-lg shadow p-3" style={{ height: '75vh' }}>
        <Calendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          eventPropGetter={eventStyleGetter}
          messages={messages}
          views={['month', 'week', 'day', 'agenda']}
          popup
        />
      </div>
      <div className="mt-3 flex flex-wrap gap-3 text-xs">
        {Object.entries(STATUS_COLORS).map(([k, v]) => (
          <div key={k} className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: v }} />
            <span>{k}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
