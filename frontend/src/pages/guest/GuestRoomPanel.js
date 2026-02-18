import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { guestAPI, guestServicesAPI } from '../../lib/api';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { statusColors, timeAgo } from '../../lib/utils';
import {
  Hotel, Sparkles, Wrench, UtensilsCrossed, BellRing, HelpCircle, Send, Star, Loader2,
  CheckCircle2, Wifi, Phone, MapPin, Clock, Coffee, Waves, Dumbbell, Car, Shirt,
  AlarmClock, KeyRound, ShoppingBag, LogOut, MessageCircle, Info, Megaphone,
  ChevronRight, ArrowLeft, Luggage, AlertCircle, Heart, ClipboardList
} from 'lucide-react';
import { toast } from 'sonner';

const TABS = [
  { id: 'home', label: 'Home', icon: Hotel },
  { id: 'services', label: 'Services', icon: ClipboardList },
  { id: 'dining', label: 'Dining', icon: UtensilsCrossed },
  { id: 'info', label: 'Hotel Info', icon: Info },
  { id: 'requests', label: 'My Requests', icon: MessageCircle },
];

const categoryConfig = {
  housekeeping: { label: 'Housekeeping', labelTr: 'Kat Hizmeti', icon: Sparkles, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  maintenance: { label: 'Technical', labelTr: 'Teknik Servis', icon: Wrench, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  room_service: { label: 'Room Service', labelTr: 'Oda Servisi', icon: UtensilsCrossed, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  reception: { label: 'Reception', labelTr: 'Resepsiyon', icon: BellRing, color: 'text-purple-400', bg: 'bg-purple-500/10' },
  laundry: { label: 'Laundry', labelTr: 'Camasir/Utu', icon: Shirt, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  spa: { label: 'Spa & Wellness', labelTr: 'Spa & Masaj', icon: Heart, color: 'text-pink-400', bg: 'bg-pink-500/10' },
  transport: { label: 'Transport', labelTr: 'Transfer', icon: Car, color: 'text-orange-400', bg: 'bg-orange-500/10' },
  wakeup: { label: 'Wake-up Call', labelTr: 'Uyandirma', icon: AlarmClock, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  bellboy: { label: 'Bellboy', labelTr: 'Bellboy', icon: Luggage, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
  key_access: { label: 'Key/Card', labelTr: 'Anahtar/Kart', icon: KeyRound, color: 'text-red-400', bg: 'bg-red-500/10' },
  minibar: { label: 'Minibar', labelTr: 'Minibar', icon: Coffee, color: 'text-teal-400', bg: 'bg-teal-500/10' },
  checkout: { label: 'Express Check-out', labelTr: 'Hizli Cikis', icon: LogOut, color: 'text-gray-400', bg: 'bg-gray-500/10' },
  complaint: { label: 'Complaint', labelTr: 'Sikayet', icon: AlertCircle, color: 'text-rose-400', bg: 'bg-rose-500/10' },
  other: { label: 'Other', labelTr: 'Diger', icon: HelpCircle, color: 'text-gray-400', bg: 'bg-gray-500/10' },
};

const statusSteps = ['OPEN', 'IN_PROGRESS', 'DONE', 'CLOSED'];

export default function GuestRoomPanel() {
  const { tenantSlug, roomCode } = useParams();
  const [roomInfo, setRoomInfo] = useState(null);
  const [hotelInfo, setHotelInfo] = useState(null);
  const [announcements, setAnnouncements] = useState([]);
  const [spaServices, setSpaServices] = useState([]);
  const [menuData, setMenuData] = useState({ categories: [], items: [] });
  const [requests, setRequests] = useState([]);
  const [myOrders, setMyOrders] = useState({ room_service_orders: [], minibar_orders: [] });
  const [myBookings, setMyBookings] = useState({ spa_bookings: [], transport_requests: [], wakeup_calls: [], laundry_requests: [] });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('home');
  const [lang, setLang] = useState('en');
  const [showRequestForm, setShowRequestForm] = useState(false);
  const [showSpaDialog, setShowSpaDialog] = useState(false);
  const [showTransportDialog, setShowTransportDialog] = useState(false);
  const [showLaundryDialog, setShowLaundryDialog] = useState(false);
  const [showWakeupDialog, setShowWakeupDialog] = useState(false);
  const [showSurveyDialog, setShowSurveyDialog] = useState(false);
  const [showRoomServiceDialog, setShowRoomServiceDialog] = useState(false);
  const [cartItems, setCartItems] = useState([]);
  const [guestName, setGuestName] = useState('');
  const [guestPhone, setGuestPhone] = useState('');

  const [form, setForm] = useState({ category: 'housekeeping', description: '', priority: 'normal' });
  const [spaForm, setSpaForm] = useState({ service_type: '', preferred_date: '', preferred_time: '', persons: 1, notes: '' });
  const [transportForm, setTransportForm] = useState({ transport_type: 'taxi', pickup_date: '', pickup_time: '', destination: '', passengers: 1, notes: '' });
  const [laundryForm, setLaundryForm] = useState({ service_type: 'regular', items_description: '', pickup_time: '', notes: '' });
  const [wakeupForm, setWakeupForm] = useState({ wakeup_date: '', wakeup_time: '07:00', notes: '' });
  const [surveyForm, setSurveyForm] = useState({ overall_rating: 0, cleanliness_rating: 0, service_rating: 0, food_rating: 0, comfort_rating: 0, comments: '', would_recommend: null });
  const [ratingForm, setRatingForm] = useState({ requestId: null, rating: 0, comment: '' });

  useEffect(() => {
    loadData();
    const interval = setInterval(loadRequests, 8000);
    return () => clearInterval(interval);
  }, [tenantSlug, roomCode]);

  const loadData = async () => {
    try {
      const [infoRes, reqRes] = await Promise.all([
        guestAPI.roomInfo(tenantSlug, roomCode),
        guestAPI.roomRequests(tenantSlug, roomCode),
      ]);
      setRoomInfo(infoRes.data);
      setRequests(reqRes.data);

      // Load additional data
      try {
        const [hiRes, annRes, spaRes, menuRes, ordRes, bookRes] = await Promise.all([
          guestServicesAPI.hotelInfo(tenantSlug).catch(() => ({ data: null })),
          guestServicesAPI.getAnnouncements(tenantSlug).catch(() => ({ data: [] })),
          guestServicesAPI.getSpaServices(tenantSlug).catch(() => ({ data: [] })),
          guestServicesAPI.roomServiceMenu(tenantSlug).catch(() => ({ data: { categories: [], items: [] } })),
          guestServicesAPI.getMyOrders(tenantSlug, roomCode).catch(() => ({ data: { room_service_orders: [], minibar_orders: [] } })),
          guestServicesAPI.getMyBookings(tenantSlug, roomCode).catch(() => ({ data: { spa_bookings: [], transport_requests: [], wakeup_calls: [], laundry_requests: [] } })),
        ]);
        setHotelInfo(hiRes.data);
        setAnnouncements(annRes.data || []);
        setSpaServices(spaRes.data || []);
        setMenuData(menuRes.data || { categories: [], items: [] });
        setMyOrders(ordRes.data || { room_service_orders: [], minibar_orders: [] });
        setMyBookings(bookRes.data || { spa_bookings: [], transport_requests: [], wakeup_calls: [], laundry_requests: [] });
      } catch (e) { console.error('Additional data load error:', e); }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadRequests = async () => {
    try { const { data } = await guestAPI.roomRequests(tenantSlug, roomCode); setRequests(data); } catch (e) {}
  };

  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    if (!form.description.trim()) return;
    setSubmitting(true);
    try {
      await guestAPI.createRequest(tenantSlug, roomCode, { ...form, guest_name: guestName, guest_phone: guestPhone });
      toast.success(lang === 'tr' ? 'Talebiniz iletildi!' : 'Request submitted successfully!');
      setForm({ ...form, description: '', priority: 'normal' });
      setShowRequestForm(false);
      loadRequests();
    } catch (e) {
      toast.error(lang === 'tr' ? 'Talep gonderilemedi' : 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSpaBooking = async () => {
    if (!spaForm.service_type) return;
    setSubmitting(true);
    try {
      await guestServicesAPI.createSpaBooking(tenantSlug, roomCode, { ...spaForm, guest_name: guestName, guest_phone: guestPhone });
      toast.success(lang === 'tr' ? 'Spa randevunuz alindi!' : 'Spa booking submitted!');
      setShowSpaDialog(false);
      setSpaForm({ service_type: '', preferred_date: '', preferred_time: '', persons: 1, notes: '' });
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleTransport = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.createTransportRequest(tenantSlug, roomCode, { ...transportForm, guest_name: guestName, guest_phone: guestPhone });
      toast.success(lang === 'tr' ? 'Transfer talebiniz alindi!' : 'Transport request submitted!');
      setShowTransportDialog(false);
      setTransportForm({ transport_type: 'taxi', pickup_date: '', pickup_time: '', destination: '', passengers: 1, notes: '' });
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleLaundry = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.createLaundryRequest(tenantSlug, roomCode, { ...laundryForm, guest_name: guestName, guest_phone: guestPhone });
      toast.success(lang === 'tr' ? 'Camasir talebiniz alindi!' : 'Laundry request submitted!');
      setShowLaundryDialog(false);
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleWakeup = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.createWakeupCall(tenantSlug, roomCode, { ...wakeupForm, guest_name: guestName });
      toast.success(lang === 'tr' ? 'Uyandirma servisi ayarlandi!' : 'Wake-up call set!');
      setShowWakeupDialog(false);
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleRoomServiceOrder = async () => {
    if (cartItems.length === 0) return;
    setSubmitting(true);
    try {
      await guestServicesAPI.createRoomServiceOrder(tenantSlug, roomCode, {
        items: cartItems, guest_name: guestName, guest_phone: guestPhone, notes: ''
      });
      toast.success(lang === 'tr' ? 'Siparisiniz alindi!' : 'Order placed successfully!');
      setCartItems([]);
      setShowRoomServiceDialog(false);
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleSurvey = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.submitSurvey(tenantSlug, roomCode, { ...surveyForm, guest_name: guestName });
      toast.success(lang === 'tr' ? 'Anketiniz icin tesekkurler!' : 'Thank you for your feedback!');
      setShowSurveyDialog(false);
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleRate = async (requestId) => {
    if (ratingForm.rating < 1) return;
    try {
      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      await fetch(`${BACKEND_URL}/api/tenants/${tenantSlug}/requests/${requestId}/rate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: ratingForm.rating, comment: ratingForm.comment }),
      });
      toast.success(lang === 'tr' ? 'Degerlendirmeniz icin tesekkurler!' : 'Thank you for your feedback!');
      setRatingForm({ requestId: null, rating: 0, comment: '' });
      loadRequests();
    } catch (e) { toast.error('Failed'); }
  };

  const addToCart = (item) => {
    const existing = cartItems.find(c => c.menu_item_id === item.id);
    if (existing) {
      setCartItems(cartItems.map(c => c.menu_item_id === item.id ? { ...c, quantity: c.quantity + 1 } : c));
    } else {
      setCartItems([...cartItems, { menu_item_id: item.id, menu_item_name: item.name, quantity: 1, price: item.price }]);
    }
  };

  const t = (en, tr) => lang === 'tr' ? tr : en;

  if (loading) return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--primary))]" />
    </div>
  );

  if (!roomInfo) return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4">
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md w-full">
        <CardContent className="p-8 text-center">
          <Hotel className="w-12 h-12 mx-auto mb-4 text-[hsl(var(--muted-foreground))]" />
          <h2 className="text-xl font-bold">{t('Room Not Found', 'Oda Bulunamadi')}</h2>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-2">{t('This QR code is invalid or expired.', 'Bu QR kod gecersiz veya suresi dolmus.')}</p>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] pb-20">
      {/* Header */}
      <div className="guest-header-gradient bg-noise">
        <div className="relative z-10 max-w-md mx-auto px-4 pt-6 pb-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[hsl(var(--primary))] flex items-center justify-center">
                <Hotel className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold">{roomInfo.tenant.name}</h1>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  {t('Room', 'Oda')} {roomInfo.room.room_number} • {roomInfo.room.room_type}
                </p>
              </div>
            </div>
            <div className="flex gap-1">
              <Button size="sm" variant={lang === 'en' ? 'default' : 'ghost'} className="text-xs px-2 h-7" onClick={() => setLang('en')}>EN</Button>
              <Button size="sm" variant={lang === 'tr' ? 'default' : 'ghost'} className="text-xs px-2 h-7" onClick={() => setLang('tr')}>TR</Button>
            </div>
          </div>
          {/* WiFi quick info */}
          {hotelInfo?.wifi_name && (
            <div className="flex items-center gap-2 text-xs bg-[hsl(var(--secondary))] rounded-lg px-3 py-2">
              <Wifi className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
              <span className="text-[hsl(var(--muted-foreground))]">WiFi:</span>
              <span className="font-medium">{hotelInfo.wifi_name}</span>
              <span className="text-[hsl(var(--muted-foreground))]">|</span>
              <span className="font-mono text-[hsl(var(--primary))]">{hotelInfo.wifi_password}</span>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 -mt-1">
        {/* Announcements */}
        {announcements.length > 0 && activeTab === 'home' && (
          <div className="mb-4">
            {announcements.map(ann => (
              <div key={ann.id} className="flex items-start gap-2 bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)] rounded-lg px-3 py-2 mb-2">
                <Megaphone className="w-4 h-4 text-[hsl(var(--primary))] flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold">{ann.title}</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{ann.body}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* TAB CONTENT */}
        {activeTab === 'home' && (
          <div className="space-y-3">
            {/* Quick Actions Grid */}
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <h3 className="font-semibold mb-3 text-sm">{t('Quick Services', 'Hizli Servisler')}</h3>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { key: 'housekeeping', action: () => { setForm({...form, category:'housekeeping'}); setShowRequestForm(true); }},
                    { key: 'room_service', action: () => setShowRoomServiceDialog(true) },
                    { key: 'maintenance', action: () => { setForm({...form, category:'maintenance'}); setShowRequestForm(true); }},
                    { key: 'spa', action: () => setShowSpaDialog(true) },
                    { key: 'transport', action: () => setShowTransportDialog(true) },
                    { key: 'laundry', action: () => setShowLaundryDialog(true) },
                    { key: 'wakeup', action: () => setShowWakeupDialog(true) },
                    { key: 'reception', action: () => { setForm({...form, category:'reception'}); setShowRequestForm(true); }},
                  ].map(({ key, action }) => {
                    const cfg = categoryConfig[key];
                    const Icon = cfg.icon;
                    return (
                      <button key={key} onClick={action} className={`p-2.5 rounded-xl border border-[hsl(var(--border))] ${cfg.bg} hover:scale-105 transition-all text-center`}>
                        <Icon className={`w-5 h-5 mx-auto mb-1 ${cfg.color}`} />
                        <span className="text-[10px] font-medium leading-tight block">{lang === 'tr' ? cfg.labelTr : cfg.label}</span>
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* More Services */}
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <h3 className="font-semibold mb-3 text-sm">{t('More Services', 'Diger Servisler')}</h3>
                <div className="grid grid-cols-4 gap-2">
                  {['bellboy', 'key_access', 'minibar', 'checkout', 'complaint', 'other'].map(key => {
                    const cfg = categoryConfig[key];
                    const Icon = cfg.icon;
                    return (
                      <button key={key} onClick={() => { setForm({...form, category: key}); setShowRequestForm(true); }}
                        className={`p-2.5 rounded-xl border border-[hsl(var(--border))] ${cfg.bg} hover:scale-105 transition-all text-center`}>
                        <Icon className={`w-5 h-5 mx-auto mb-1 ${cfg.color}`} />
                        <span className="text-[10px] font-medium leading-tight block">{lang === 'tr' ? cfg.labelTr : cfg.label}</span>
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Active Requests Summary */}
            {requests.filter(r => r.status !== 'CLOSED').length > 0 && (
              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-sm">{t('Active Requests', 'Aktif Talepler')}</h3>
                    <Badge className="text-xs">{requests.filter(r => r.status !== 'CLOSED').length}</Badge>
                  </div>
                  {requests.filter(r => r.status !== 'CLOSED').slice(0, 3).map(req => {
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
                  <Button size="sm" variant="ghost" className="w-full mt-2 text-xs" onClick={() => setActiveTab('requests')}>
                    {t('View All', 'Tumunu Gor')} <ChevronRight className="w-3 h-3 ml-1" />
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Survey Button */}
            <Button variant="outline" className="w-full text-sm" onClick={() => setShowSurveyDialog(true)}>
              <Star className="w-4 h-4 mr-2" /> {t('Rate Your Stay', 'Konaklamanizi Degerlendirin')}
            </Button>
          </div>
        )}

        {activeTab === 'services' && (
          <div className="space-y-3">
            <h3 className="font-semibold">{t('All Services', 'Tum Servisler')}</h3>
            {Object.entries(categoryConfig).map(([key, cfg]) => {
              const Icon = cfg.icon;
              return (
                <button key={key} onClick={() => {
                  if (key === 'spa') { setShowSpaDialog(true); return; }
                  if (key === 'transport') { setShowTransportDialog(true); return; }
                  if (key === 'laundry') { setShowLaundryDialog(true); return; }
                  if (key === 'wakeup') { setShowWakeupDialog(true); return; }
                  if (key === 'room_service') { setShowRoomServiceDialog(true); return; }
                  setForm({...form, category: key}); setShowRequestForm(true);
                }}
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
        )}

        {activeTab === 'dining' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{t('Room Service Menu', 'Oda Servisi Menusu')}</h3>
              {cartItems.length > 0 && (
                <Button size="sm" onClick={() => setShowRoomServiceDialog(true)}>
                  <ShoppingBag className="w-4 h-4 mr-1" /> {t('Cart', 'Sepet')} ({cartItems.reduce((a,c) => a+c.quantity, 0)})
                </Button>
              )}
            </div>
            {menuData.categories.map(cat => (
              <div key={cat.id}>
                <h4 className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-2 mt-3">{cat.name}</h4>
                {menuData.items.filter(i => i.category_id === cat.id).map(item => (
                  <div key={item.id} className="flex items-center gap-3 p-3 mb-2 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
                    <div className="flex-1">
                      <p className="text-sm font-medium">{item.name}</p>
                      {item.description && <p className="text-xs text-[hsl(var(--muted-foreground))]">{item.description}</p>}
                    </div>
                    <span className="text-sm font-bold text-[hsl(var(--primary))]">{item.price} TRY</span>
                    <Button size="sm" variant="outline" className="h-8 w-8 p-0" onClick={() => addToCart(item)}>+</Button>
                  </div>
                ))}
              </div>
            ))}
            {menuData.categories.length === 0 && (
              <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                <UtensilsCrossed className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">{t('Menu not available', 'Menu mevcut degil')}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'info' && hotelInfo && (
          <div className="space-y-3">
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <h3 className="font-semibold mb-1">{hotelInfo.hotel_name || roomInfo.tenant.name}</h3>
                {hotelInfo.description && <p className="text-xs text-[hsl(var(--muted-foreground))] mb-3">{hotelInfo.description}</p>}
                <div className="space-y-2 text-xs">
                  {hotelInfo.address && <div className="flex items-center gap-2"><MapPin className="w-3.5 h-3.5 text-[hsl(var(--primary))]" /><span>{hotelInfo.address}</span></div>}
                  {hotelInfo.phone && <div className="flex items-center gap-2"><Phone className="w-3.5 h-3.5 text-[hsl(var(--primary))]" /><span>{hotelInfo.phone}</span></div>}
                  {hotelInfo.wifi_name && <div className="flex items-center gap-2"><Wifi className="w-3.5 h-3.5 text-[hsl(var(--primary))]" /><span>WiFi: {hotelInfo.wifi_name} / {hotelInfo.wifi_password}</span></div>}
                  <div className="flex items-center gap-2"><Clock className="w-3.5 h-3.5 text-[hsl(var(--primary))]" /><span>Check-in: {hotelInfo.check_in_time} | Check-out: {hotelInfo.check_out_time}</span></div>
                </div>
              </CardContent>
            </Card>

            {/* Facilities */}
            {hotelInfo.facilities?.length > 0 && (
              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4">
                  <h3 className="font-semibold mb-3 text-sm">{t('Facilities', 'Tesisler')}</h3>
                  <div className="space-y-2">
                    {hotelInfo.facilities.map((f, i) => (
                      <div key={i} className="flex items-start gap-3 p-2 rounded-lg bg-[hsl(var(--secondary))]">
                        <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center flex-shrink-0">
                          {f.icon === 'pool' ? <Waves className="w-4 h-4 text-blue-400" /> :
                           f.icon === 'spa' ? <Heart className="w-4 h-4 text-pink-400" /> :
                           f.icon === 'gym' ? <Dumbbell className="w-4 h-4 text-green-400" /> :
                           f.icon === 'restaurant' ? <UtensilsCrossed className="w-4 h-4 text-amber-400" /> :
                           <Hotel className="w-4 h-4 text-[hsl(var(--primary))]" />}
                        </div>
                        <div className="flex-1">
                          <p className="text-xs font-semibold">{f.name}</p>
                          <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{f.hours} • {f.floor}</p>
                          {f.description && <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{f.description}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Emergency Contacts */}
            {hotelInfo.emergency_contacts?.length > 0 && (
              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                <CardContent className="p-4">
                  <h3 className="font-semibold mb-3 text-sm">{t('Emergency Contacts', 'Acil Numaralar')}</h3>
                  {hotelInfo.emergency_contacts.map((c, i) => (
                    <div key={i} className="flex items-center justify-between py-1.5 border-b border-[hsl(var(--border))] last:border-0">
                      <div>
                        <p className="text-xs font-medium">{c.name}</p>
                        <p className="text-[10px] text-[hsl(var(--muted-foreground))]">{c.description}</p>
                      </div>
                      <a href={`tel:${c.number}`} className="text-xs font-bold text-[hsl(var(--primary))]">{c.number}</a>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Policies */}
            <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4">
                <h3 className="font-semibold mb-3 text-sm">{t('Policies', 'Kurallar')}</h3>
                <div className="space-y-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                  {hotelInfo.parking_info && <p>🅿️ {hotelInfo.parking_info}</p>}
                  {hotelInfo.pet_policy && <p>🐾 {hotelInfo.pet_policy}</p>}
                  {hotelInfo.smoking_policy && <p>🚭 {hotelInfo.smoking_policy}</p>}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'requests' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{t('My Requests', 'Taleplerim')}</h3>
              <Button size="sm" onClick={() => setShowRequestForm(true)}>{t('New Request', 'Yeni Talep')}</Button>
            </div>
            {requests.length === 0 && (
              <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">{t('No requests yet', 'Henuz talep yok')}</p>
              </div>
            )}
            {requests.map(req => {
              const cat = categoryConfig[req.category] || categoryConfig.other;
              const Icon = cat.icon;
              const stepIndex = statusSteps.indexOf(req.status);
              return (
                <Card key={req.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3 mb-3">
                      <div className={`w-9 h-9 rounded-lg ${cat.bg} flex items-center justify-center flex-shrink-0`}>
                        <Icon className={`w-4 h-4 ${cat.color}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{req.description}</p>
                        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{timeAgo(req.created_at)}</p>
                      </div>
                      <Badge className={`${statusColors[req.status]} text-[10px]`}>{req.status.replace('_', ' ')}</Badge>
                    </div>
                    <div className="flex items-center gap-1 mb-2">
                      {statusSteps.map((step, i) => (
                        <React.Fragment key={step}>
                          <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] ${
                            i <= stepIndex ? 'bg-[hsl(var(--primary))] text-white' : 'bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))]'
                          }`}>
                            {i <= stepIndex ? <CheckCircle2 className="w-3 h-3" /> : i + 1}
                          </div>
                          {i < statusSteps.length - 1 && <div className={`flex-1 h-0.5 ${i < stepIndex ? 'bg-[hsl(var(--primary))]' : 'bg-[hsl(var(--secondary))]'}`} />}
                        </React.Fragment>
                      ))}
                    </div>
                    {req.status === 'DONE' && !req.rating && (
                      <div className="border-t border-[hsl(var(--border))] pt-2 mt-2">
                        <p className="text-[10px] text-[hsl(var(--muted-foreground))] mb-1">{t('Rate this service:', 'Bu hizmeti degerlendirin:')}</p>
                        <div className="flex gap-1 mb-1">
                          {[1,2,3,4,5].map(n => (
                            <button key={n} onClick={() => setRatingForm({...ratingForm, requestId: req.id, rating: n})}>
                              <Star className={`w-5 h-5 ${ratingForm.requestId === req.id && ratingForm.rating >= n ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />
                            </button>
                          ))}
                        </div>
                        {ratingForm.requestId === req.id && ratingForm.rating > 0 && (
                          <Button size="sm" className="mt-1 h-7 text-xs" onClick={() => handleRate(req.id)}>
                            {t('Submit Rating', 'Gonder')}
                          </Button>
                        )}
                      </div>
                    )}
                    {req.rating && (
                      <div className="flex items-center gap-1 text-xs text-amber-400 mt-1">
                        {[...Array(req.rating)].map((_, i) => <Star key={i} className="w-3 h-3 fill-amber-400" />)}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Bottom Tab Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-[hsl(var(--card))] border-t border-[hsl(var(--border))] z-50">
        <div className="max-w-md mx-auto flex">
          {TABS.map(tab => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex flex-col items-center py-2.5 ${activeTab === tab.id ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--muted-foreground))]'}`}>
                <Icon className="w-5 h-5" />
                <span className="text-[10px] mt-0.5 font-medium">{t(tab.label, tab.label)}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* REQUEST FORM DIALOG */}
      <Dialog open={showRequestForm} onOpenChange={setShowRequestForm}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('Submit Request', 'Talep Gonder')}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmitRequest} className="space-y-3">
            <div className="grid grid-cols-4 gap-2">
              {Object.entries(categoryConfig).slice(0, 8).map(([key, cfg]) => {
                const Icon = cfg.icon;
                return (
                  <button key={key} type="button" onClick={() => setForm({...form, category: key})}
                    className={`p-2 rounded-lg border text-center transition-all ${form.category === key ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)]' : 'border-[hsl(var(--border))]'}`}>
                    <Icon className={`w-4 h-4 mx-auto mb-0.5 ${cfg.color}`} />
                    <span className="text-[9px] font-medium">{lang === 'tr' ? cfg.labelTr : cfg.label}</span>
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
            <Button type="submit" className="w-full" disabled={!form.description.trim() || submitting}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
              {t('Submit', 'Gonder')}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* SPA BOOKING DIALOG */}
      <Dialog open={showSpaDialog} onOpenChange={setShowSpaDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{t('Spa & Wellness Booking', 'Spa Randevusu')}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            {spaServices.map(s => (
              <button key={s.id} onClick={() => setSpaForm({...spaForm, service_type: s.name})}
                className={`w-full text-left p-3 rounded-lg border transition-all ${spaForm.service_type === s.name ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]' : 'border-[hsl(var(--border))]'}`}>
                <div className="flex justify-between"><span className="text-sm font-medium">{s.name}</span><span className="text-sm font-bold text-[hsl(var(--primary))]">{s.price} TRY</span></div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">{s.description} • {s.duration_minutes} min</p>
              </button>
            ))}
            <div className="grid grid-cols-2 gap-2">
              <Input type="date" value={spaForm.preferred_date} onChange={(e) => setSpaForm({...spaForm, preferred_date: e.target.value})} className="bg-[hsl(var(--secondary))]" />
              <Input type="time" value={spaForm.preferred_time} onChange={(e) => setSpaForm({...spaForm, preferred_time: e.target.value})} className="bg-[hsl(var(--secondary))]" />
            </div>
            <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} placeholder={t('Your name', 'Adiniz')} className="bg-[hsl(var(--secondary))]" />
            <Textarea value={spaForm.notes} onChange={(e) => setSpaForm({...spaForm, notes: e.target.value})} placeholder={t('Notes', 'Notlar')} className="bg-[hsl(var(--secondary))]" />
            <Button className="w-full" onClick={handleSpaBooking} disabled={!spaForm.service_type || submitting}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Heart className="w-4 h-4 mr-2" />}
              {t('Book Spa', 'Randevu Al')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* TRANSPORT DIALOG */}
      <Dialog open={showTransportDialog} onOpenChange={setShowTransportDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md">
          <DialogHeader><DialogTitle>{t('Transport Request', 'Transfer Talebi')}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Select value={transportForm.transport_type} onValueChange={(v) => setTransportForm({...transportForm, transport_type: v})}>
              <SelectTrigger className="bg-[hsl(var(--secondary))]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="taxi">{t('Taxi', 'Taksi')}</SelectItem>
                <SelectItem value="airport_transfer">{t('Airport Transfer', 'Havalimani Transfer')}</SelectItem>
                <SelectItem value="shuttle">{t('Hotel Shuttle', 'Otel Servisi')}</SelectItem>
                <SelectItem value="car_rental">{t('Car Rental', 'Arac Kiralama')}</SelectItem>
              </SelectContent>
            </Select>
            <Input value={transportForm.destination} onChange={(e) => setTransportForm({...transportForm, destination: e.target.value})} placeholder={t('Destination', 'Varilacak Yer')} className="bg-[hsl(var(--secondary))]" />
            <div className="grid grid-cols-2 gap-2">
              <Input type="date" value={transportForm.pickup_date} onChange={(e) => setTransportForm({...transportForm, pickup_date: e.target.value})} className="bg-[hsl(var(--secondary))]" />
              <Input type="time" value={transportForm.pickup_time} onChange={(e) => setTransportForm({...transportForm, pickup_time: e.target.value})} className="bg-[hsl(var(--secondary))]" />
            </div>
            <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} placeholder={t('Your name', 'Adiniz')} className="bg-[hsl(var(--secondary))]" />
            <Button className="w-full" onClick={handleTransport} disabled={submitting}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Car className="w-4 h-4 mr-2" />}
              {t('Request Transport', 'Transfer Talep Et')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* LAUNDRY DIALOG */}
      <Dialog open={showLaundryDialog} onOpenChange={setShowLaundryDialog}>
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
            <Button className="w-full" onClick={handleLaundry} disabled={submitting}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Shirt className="w-4 h-4 mr-2" />}
              {t('Request Laundry', 'Camasir Talep Et')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* WAKEUP DIALOG */}
      <Dialog open={showWakeupDialog} onOpenChange={setShowWakeupDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md">
          <DialogHeader><DialogTitle>{t('Wake-up Call', 'Uyandirma Servisi')}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <Input type="date" value={wakeupForm.wakeup_date} onChange={(e) => setWakeupForm({...wakeupForm, wakeup_date: e.target.value})} className="bg-[hsl(var(--secondary))]" />
              <Input type="time" value={wakeupForm.wakeup_time} onChange={(e) => setWakeupForm({...wakeupForm, wakeup_time: e.target.value})} className="bg-[hsl(var(--secondary))]" />
            </div>
            <Textarea value={wakeupForm.notes} onChange={(e) => setWakeupForm({...wakeupForm, notes: e.target.value})} placeholder={t('Notes (e.g. second call after 5 min)', 'Notlar')} className="bg-[hsl(var(--secondary))]" />
            <Button className="w-full" onClick={handleWakeup} disabled={submitting}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <AlarmClock className="w-4 h-4 mr-2" />}
              {t('Set Wake-up Call', 'Uyandirma Ayarla')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ROOM SERVICE ORDER DIALOG */}
      <Dialog open={showRoomServiceDialog} onOpenChange={setShowRoomServiceDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{t('Room Service Order', 'Oda Servisi Siparisi')}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            {cartItems.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">{t('Your cart is empty. Browse menu to add items.', 'Sepetiniz bos. Menuye giderek urun ekleyiniz.')}</p>
            ) : (
              <>
                {cartItems.map((item, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-[hsl(var(--secondary))]">
                    <div>
                      <p className="text-sm font-medium">{item.menu_item_name}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{item.price} TRY x {item.quantity}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => {
                        if (item.quantity <= 1) setCartItems(cartItems.filter((_, idx) => idx !== i));
                        else setCartItems(cartItems.map((c, idx) => idx === i ? {...c, quantity: c.quantity - 1} : c));
                      }}>-</Button>
                      <span className="text-sm font-bold w-6 text-center">{item.quantity}</span>
                      <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => setCartItems(cartItems.map((c, idx) => idx === i ? {...c, quantity: c.quantity + 1} : c))}>+</Button>
                    </div>
                  </div>
                ))}
                <div className="flex justify-between font-bold text-sm pt-2 border-t border-[hsl(var(--border))]">
                  <span>{t('Total', 'Toplam')}</span>
                  <span className="text-[hsl(var(--primary))]">{cartItems.reduce((a,c) => a + c.price * c.quantity, 0)} TRY</span>
                </div>
                <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} placeholder={t('Your name', 'Adiniz')} className="bg-[hsl(var(--secondary))]" />
                <Button className="w-full" onClick={handleRoomServiceOrder} disabled={submitting}>
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                  {t('Place Order', 'Siparis Ver')}
                </Button>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* SURVEY DIALOG */}
      <Dialog open={showSurveyDialog} onOpenChange={setShowSurveyDialog}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{t('Rate Your Stay', 'Konaklamanizi Degerlendirin')}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            {[
              { key: 'overall_rating', label: t('Overall', 'Genel') },
              { key: 'cleanliness_rating', label: t('Cleanliness', 'Temizlik') },
              { key: 'service_rating', label: t('Service', 'Hizmet') },
              { key: 'food_rating', label: t('Food & Dining', 'Yemek') },
              { key: 'comfort_rating', label: t('Comfort', 'Konfor') },
            ].map(({ key, label }) => (
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
            <Button className="w-full" onClick={handleSurvey} disabled={submitting}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Star className="w-4 h-4 mr-2" />}
              {t('Submit Survey', 'Anketi Gonder')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
