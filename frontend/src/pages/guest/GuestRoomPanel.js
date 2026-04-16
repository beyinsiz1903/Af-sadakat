import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { guestAPI, guestServicesAPI, uploadAPI } from '../../lib/api';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Hotel, Wifi, Bell, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { TABS } from './constants';
import { GuestProvider } from './GuestContext';
import HomeTab from './components/HomeTab';
import ServicesTab from './components/ServicesTab';
import DiningTab from './components/DiningTab';
import FolioTab from './components/FolioTab';
import RequestsTab from './components/RequestsTab';
import GeneralRequestDialog from './dialogs/GeneralRequestDialog';
import SpaDialog from './dialogs/SpaDialog';
import TransportDialog from './dialogs/TransportDialog';
import LaundryDialog from './dialogs/LaundryDialog';
import WakeupDialog from './dialogs/WakeupDialog';
import RoomServiceDialog from './dialogs/RoomServiceDialog';
import SurveyDialog from './dialogs/SurveyDialog';
import RestaurantDialog from './dialogs/RestaurantDialog';
import NotificationPanel from './dialogs/NotificationPanel';
import NotifPrefsDialog from './dialogs/NotifPrefsDialog';

export default function GuestRoomPanel() {
  const { tenantSlug, roomCode } = useParams();
  const [roomInfo, setRoomInfo] = useState(null);
  const [hotelInfo, setHotelInfo] = useState(null);
  const [announcements, setAnnouncements] = useState([]);
  const [spaServices, setSpaServices] = useState([]);
  const [menuData, setMenuData] = useState({ categories: [], items: [] });
  const [requests, setRequests] = useState([]);
  const [myBookings, setMyBookings] = useState({ spa_bookings: [], transport_requests: [], wakeup_calls: [], laundry_requests: [], restaurant_reservations: [] });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('home');
  const [lang, setLang] = useState('en');
  const [guestName, setGuestName] = useState('');
  const [guestPhone, setGuestPhone] = useState('');
  const [activeServices, setActiveServices] = useState([]);
  const [cartItems, setCartItems] = useState([]);
  const [restaurants, setRestaurants] = useState([]);
  const [selectedRestaurant, setSelectedRestaurant] = useState(null);
  const [availableSlots, setAvailableSlots] = useState([]);

  const [showRequestForm, setShowRequestForm] = useState(false);
  const [showSpaDialog, setShowSpaDialog] = useState(false);
  const [showTransportDialog, setShowTransportDialog] = useState(false);
  const [showLaundryDialog, setShowLaundryDialog] = useState(false);
  const [showWakeupDialog, setShowWakeupDialog] = useState(false);
  const [showSurveyDialog, setShowSurveyDialog] = useState(false);
  const [showRoomServiceDialog, setShowRoomServiceDialog] = useState(false);
  const [showRestaurantDialog, setShowRestaurantDialog] = useState(false);

  const [form, setForm] = useState({ category: 'housekeeping', description: '', priority: 'normal' });
  const [spaForm, setSpaForm] = useState({ service_type: '', preferred_date: '', preferred_time: '', persons: 1, notes: '' });
  const [transportForm, setTransportForm] = useState({ transport_type: 'taxi', pickup_date: '', pickup_time: '', destination: '', passengers: 1, notes: '' });
  const [laundryForm, setLaundryForm] = useState({ service_type: 'regular', items_description: '', pickup_time: '', notes: '' });
  const [wakeupForm, setWakeupForm] = useState({ wakeup_date: '', wakeup_time: '07:00', notes: '' });
  const [surveyForm, setSurveyForm] = useState({ overall_rating: 0, cleanliness_rating: 0, service_rating: 0, food_rating: 0, comfort_rating: 0, comments: '', would_recommend: null });
  const [restaurantForm, setRestaurantForm] = useState({ restaurant_id: '', restaurant_name: '', date: '', time: '', party_size: 2, special_requests: '', occasion: '', seating_preference: 'no_preference' });
  const [ratingForm, setRatingForm] = useState({ requestId: null, rating: 0, comment: '' });
  const [uploadFiles, setUploadFiles] = useState([]);

  const [folioData, setFolioData] = useState(null);
  const [folioLoading, setFolioLoading] = useState(false);
  const folioLoadedRef = useRef(false);

  const [pushSupported, setPushSupported] = useState(false);
  const [pushSubscribed, setPushSubscribed] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);
  const [showNotifPanel, setShowNotifPanel] = useState(false);
  const [showNotifPrefs, setShowNotifPrefs] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifPrefs, setNotifPrefs] = useState({
    housekeeping: true, maintenance: true, room_service: true,
    laundry: true, spa: true, transport: true, wakeup: true, reception: true,
  });

  const t = (en, tr) => lang === 'tr' ? tr : en;

  const ctxValue = { tenantSlug, roomCode, roomInfo, hotelInfo, lang, guestName, guestPhone, t };

  useEffect(() => {
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      navigator.serviceWorker.register('/sw.js').then(() => {
        setPushSupported(true);
        checkPushSubscription();
      }).catch(e => console.error('SW registration failed:', e));
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadRequests, 8000);
    const notifInterval = setInterval(loadUnreadCount, 15000);
    return () => { clearInterval(interval); clearInterval(notifInterval); };
  }, [tenantSlug, roomCode]);

  useEffect(() => {
    if (activeTab === 'folio' && !folioData && !folioLoading && !folioLoadedRef.current) {
      folioLoadedRef.current = true;
      setFolioLoading(true);
      guestServicesAPI.getRoomFolio(tenantSlug, roomCode)
        .then(res => { setFolioData(res.data); setFolioLoading(false); })
        .catch(() => { setFolioData({ items: [], total: 0 }); setFolioLoading(false); });
    }
  }, [activeTab, folioData, folioLoading, tenantSlug, roomCode]);

  const urlBase64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
    return outputArray;
  };

  const checkPushSubscription = async () => {
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      setPushSubscribed(!!sub);
      if (sub) {
        const res = await guestServicesAPI.getPushPreferences(tenantSlug, roomCode, sub.endpoint);
        if (res.data?.subscribed) setNotifPrefs(res.data.preferences || notifPrefs);
      }
    } catch (e) { console.error('Push check error:', e); }
  };

  const loadData = async () => {
    try {
      const [infoRes, reqRes] = await Promise.all([
        guestAPI.roomInfo(tenantSlug, roomCode),
        guestAPI.roomRequests(tenantSlug, roomCode),
      ]);
      setRoomInfo(infoRes.data);
      setRequests(reqRes.data);
      if (infoRes.data?.current_guest_name) setGuestName(infoRes.data.current_guest_name);
      try {
        const [hiRes, annRes, spaRes, menuRes, , bookRes, svcRes, restRes] = await Promise.all([
          guestServicesAPI.hotelInfo(tenantSlug).catch(() => ({ data: null })),
          guestServicesAPI.getAnnouncements(tenantSlug).catch(() => ({ data: [] })),
          guestServicesAPI.getSpaServices(tenantSlug).catch(() => ({ data: [] })),
          guestServicesAPI.roomServiceMenu(tenantSlug).catch(() => ({ data: { categories: [], items: [] } })),
          guestServicesAPI.getMyOrders(tenantSlug, roomCode).catch(() => ({ data: { room_service_orders: [], minibar_orders: [] } })),
          guestServicesAPI.getMyBookings(tenantSlug, roomCode).catch(() => ({ data: { spa_bookings: [], transport_requests: [], wakeup_calls: [], laundry_requests: [], restaurant_reservations: [] } })),
          guestServicesAPI.getActiveServices(tenantSlug).catch(() => ({ data: [] })),
          guestServicesAPI.getRestaurants(tenantSlug).catch(() => ({ data: [] })),
        ]);
        setHotelInfo(hiRes.data);
        setAnnouncements(annRes.data || []);
        setSpaServices(spaRes.data || []);
        setMenuData(menuRes.data || { categories: [], items: [] });
        setMyBookings(bookRes.data || { spa_bookings: [], transport_requests: [], wakeup_calls: [], laundry_requests: [] });
        setActiveServices(svcRes.data || []);
        setRestaurants(restRes.data || []);
      } catch (e) { console.error('Additional data load error:', e); }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const loadRequests = async () => {
    try { const { data } = await guestAPI.roomRequests(tenantSlug, roomCode); setRequests(data); } catch (e) {}
  };

  const loadUnreadCount = async () => {
    try { const res = await guestServicesAPI.getUnreadNotifCount(tenantSlug, roomCode); setUnreadCount(res.data?.count || 0); } catch (e) {}
  };

  const handlePushToggle = async () => {
    setPushLoading(true);
    try {
      if (pushSubscribed) {
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
          await guestServicesAPI.pushUnsubscribe(tenantSlug, roomCode, { endpoint: sub.endpoint });
          await sub.unsubscribe();
        }
        setPushSubscribed(false);
        toast.success(t('Notifications disabled', 'Bildirimler kapatıldı'));
      } else {
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') { toast.error(t('Notification permission denied', 'Bildirim izni reddedildi')); setPushLoading(false); return; }
        const vapidRes = await guestServicesAPI.getVapidKey(tenantSlug);
        const vapidKey = vapidRes.data?.public_key;
        if (!vapidKey || vapidKey === 'dummy_public_key') { toast.error(t('Push service not configured', 'Bildirim servisi yapılandırılmamış')); setPushLoading(false); return; }
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(vapidKey) });
        await guestServicesAPI.pushSubscribe(tenantSlug, roomCode, { subscription: sub.toJSON(), preferences: notifPrefs, lang });
        setPushSubscribed(true);
        toast.success(t('Notifications enabled!', 'Bildirimler açıldı!'));
      }
    } catch (e) { console.error('Push toggle error:', e); toast.error(t('Failed to change notification setting', 'Bildirim ayarı değiştirilemedi')); }
    finally { setPushLoading(false); }
  };

  const handlePrefChange = async (key) => {
    const updated = { ...notifPrefs, [key]: !notifPrefs[key] };
    setNotifPrefs(updated);
    if (pushSubscribed) {
      try {
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        await guestServicesAPI.updatePushPreferences(tenantSlug, roomCode, { endpoint: sub?.endpoint || '', preferences: updated, lang });
      } catch (e) { console.error('Pref update error:', e); }
    }
  };

  const handleOpenNotifPanel = async () => {
    setShowNotifPanel(true);
    try {
      const res = await guestServicesAPI.getGuestNotifications(tenantSlug, roomCode);
      setNotifications(res.data || []);
    } catch (e) {}
    if (unreadCount > 0) { await guestServicesAPI.markNotificationsRead(tenantSlug, roomCode); setUnreadCount(0); }
  };

  const openService = (key) => {
    if (key === 'spa') { setShowSpaDialog(true); return; }
    if (key === 'transport') { setShowTransportDialog(true); return; }
    if (key === 'laundry') { setShowLaundryDialog(true); return; }
    if (key === 'wakeup') { setShowWakeupDialog(true); return; }
    if (key === 'room_service') { setShowRoomServiceDialog(true); return; }
    if (key === 'restaurant_reservation') { setShowRestaurantDialog(true); return; }
    setForm({...form, category: key}); setShowRequestForm(true);
  };

  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    if (!form.description.trim()) return;
    setSubmitting(true);
    try {
      const res = await guestAPI.createRequest(tenantSlug, roomCode, { ...form, guest_name: guestName, guest_phone: guestPhone });
      const requestId = res.data?.id || '';
      if (uploadFiles.length > 0 && requestId) {
        for (const file of uploadFiles) {
          const fd = new FormData(); fd.append('file', file); fd.append('entity_type', 'request'); fd.append('entity_id', requestId); fd.append('room_code', roomCode);
          try { await uploadAPI.guestUpload(tenantSlug, fd); } catch (ue) { console.error('Upload failed:', ue); }
        }
      }
      toast.success(t('Request submitted successfully!', 'Talebiniz iletildi!'));
      setForm({ ...form, description: '', priority: 'normal' }); setUploadFiles([]); setShowRequestForm(false); loadRequests();
    } catch (e) { toast.error(t('Failed to submit request', 'Talep gonderilemedi')); }
    finally { setSubmitting(false); }
  };

  const handleSpaBooking = async () => {
    if (!spaForm.service_type) return;
    setSubmitting(true);
    try {
      await guestServicesAPI.createSpaBooking(tenantSlug, roomCode, { ...spaForm, guest_name: guestName, guest_phone: guestPhone });
      toast.success(t('Spa booking submitted!', 'Spa randevunuz alindi!'));
      setShowSpaDialog(false); setSpaForm({ service_type: '', preferred_date: '', preferred_time: '', persons: 1, notes: '' });
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleTransport = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.createTransportRequest(tenantSlug, roomCode, { ...transportForm, guest_name: guestName, guest_phone: guestPhone });
      toast.success(t('Transport request submitted!', 'Transfer talebiniz alindi!'));
      setShowTransportDialog(false); setTransportForm({ transport_type: 'taxi', pickup_date: '', pickup_time: '', destination: '', passengers: 1, notes: '' });
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleLaundry = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.createLaundryRequest(tenantSlug, roomCode, { ...laundryForm, guest_name: guestName, guest_phone: guestPhone });
      toast.success(t('Laundry request submitted!', 'Camasir talebiniz alindi!'));
      setShowLaundryDialog(false);
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleWakeup = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.createWakeupCall(tenantSlug, roomCode, { ...wakeupForm, guest_name: guestName });
      toast.success(t('Wake-up call set!', 'Uyandirma servisi ayarlandi!'));
      setShowWakeupDialog(false);
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleRoomServiceOrder = async () => {
    if (cartItems.length === 0) return;
    setSubmitting(true);
    try {
      await guestServicesAPI.createRoomServiceOrder(tenantSlug, roomCode, { items: cartItems, guest_name: guestName, guest_phone: guestPhone, notes: '' });
      toast.success(t('Order placed successfully!', 'Siparisiniz alindi!'));
      setCartItems([]); setShowRoomServiceDialog(false);
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleSurvey = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.submitSurvey(tenantSlug, roomCode, { ...surveyForm, guest_name: guestName });
      toast.success(t('Thank you for your feedback!', 'Anketiniz icin tesekkurler!'));
      setShowSurveyDialog(false);
    } catch (e) { toast.error('Failed'); } finally { setSubmitting(false); }
  };

  const handleRestaurantReservation = async () => {
    setSubmitting(true);
    try {
      await guestServicesAPI.createRestaurantReservation(tenantSlug, roomCode, { ...restaurantForm, guest_name: guestName, guest_phone: guestPhone });
      toast.success(t('Reservation confirmed!', 'Rezervasyonunuz alindi!'));
      setShowRestaurantDialog(false);
      setRestaurantForm({ restaurant_id: '', restaurant_name: '', date: '', time: '', party_size: 2, special_requests: '', occasion: '', seating_preference: 'no_preference' });
      setAvailableSlots([]); setSelectedRestaurant(null);
    } catch (e) { toast.error(t('Failed', 'Hata')); } finally { setSubmitting(false); }
  };

  const handleRate = async (requestId) => {
    if (ratingForm.rating < 1) return;
    try {
      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      await fetch(`${BACKEND_URL}/api/tenants/${tenantSlug}/requests/${requestId}/rate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: ratingForm.rating, comment: ratingForm.comment }),
      });
      toast.success(t('Thank you for your feedback!', 'Degerlendirmeniz icin tesekkurler!'));
      setRatingForm({ requestId: null, rating: 0, comment: '' }); loadRequests();
    } catch (e) { toast.error('Failed'); }
  };

  const addToCart = (item) => {
    const existing = cartItems.find(c => c.menu_item_id === item.id);
    if (existing) setCartItems(cartItems.map(c => c.menu_item_id === item.id ? { ...c, quantity: c.quantity + 1 } : c));
    else setCartItems([...cartItems, { menu_item_id: item.id, menu_item_name: item.name, quantity: 1, price: item.price }]);
  };

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
    <GuestProvider value={ctxValue}>
      <div className="min-h-screen bg-[hsl(var(--background))] pb-20">
        <div className="guest-header-gradient bg-noise">
          <div className="relative z-10 max-w-md mx-auto px-4 pt-6 pb-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[hsl(var(--primary))] flex items-center justify-center">
                  <Hotel className="w-5 h-5 text-white" />
                </div>
                <div>
                  {roomInfo.current_guest_name ? (
                    <>
                      <h1 className="text-lg font-bold">{t('Welcome', 'Hosgeldiniz')}, {roomInfo.current_guest_name.split(' ')[0]}!</h1>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{roomInfo.tenant.name} • {t('Room', 'Oda')} {roomInfo.room.room_number}</p>
                    </>
                  ) : (
                    <>
                      <h1 className="text-lg font-bold">{roomInfo.tenant.name}</h1>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{t('Room', 'Oda')} {roomInfo.room.room_number} • {roomInfo.room.room_type}</p>
                    </>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1">
                {pushSupported && (
                  <button onClick={handleOpenNotifPanel} className="relative p-1.5 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors">
                    <Bell className={`w-4.5 h-4.5 ${pushSubscribed ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--muted-foreground))]'}`} />
                    {unreadCount > 0 && (
                      <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                        {unreadCount > 9 ? '9+' : unreadCount}
                      </span>
                    )}
                  </button>
                )}
                <Button size="sm" variant={lang === 'en' ? 'default' : 'ghost'} className="text-xs px-2 h-7" onClick={() => setLang('en')}>EN</Button>
                <Button size="sm" variant={lang === 'tr' ? 'default' : 'ghost'} className="text-xs px-2 h-7" onClick={() => setLang('tr')}>TR</Button>
              </div>
            </div>
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
          {activeTab === 'home' && <HomeTab requests={requests} activeServices={activeServices} announcements={announcements} onOpenService={openService} onSetTab={setActiveTab} onShowSurvey={() => setShowSurveyDialog(true)} />}
          {activeTab === 'services' && <ServicesTab activeServices={activeServices} onOpenService={openService} />}
          {activeTab === 'dining' && <DiningTab menuData={menuData} cartItems={cartItems} onAddToCart={addToCart} onShowCart={() => setShowRoomServiceDialog(true)} />}
          {activeTab === 'folio' && <FolioTab folioData={folioData} folioLoading={folioLoading} onRefresh={() => { setFolioData(null); setFolioLoading(false); folioLoadedRef.current = false; }} />}
          {activeTab === 'requests' && <RequestsTab requests={requests} myBookings={myBookings} ratingForm={ratingForm} setRatingForm={setRatingForm} onRate={handleRate} onShowRequestForm={() => setShowRequestForm(true)} />}
        </div>

        <div className="fixed bottom-0 left-0 right-0 bg-[hsl(var(--card))] border-t border-[hsl(var(--border))] z-50">
          <div className="max-w-md mx-auto flex">
            {TABS.map(tab => {
              const Icon = tab.icon;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex flex-col items-center py-2.5 ${activeTab === tab.id ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--muted-foreground))]'}`}>
                  <Icon className="w-5 h-5" />
                  <span className="text-[10px] mt-0.5 font-medium">{lang === 'tr' && tab.labelTr ? tab.labelTr : tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <GeneralRequestDialog open={showRequestForm} onOpenChange={setShowRequestForm} form={form} setForm={setForm} guestName={guestName} setGuestName={setGuestName} guestPhone={guestPhone} setGuestPhone={setGuestPhone} uploadFiles={uploadFiles} setUploadFiles={setUploadFiles} submitting={submitting} onSubmit={handleSubmitRequest} />
        <SpaDialog open={showSpaDialog} onOpenChange={setShowSpaDialog} spaServices={spaServices} spaForm={spaForm} setSpaForm={setSpaForm} guestName={guestName} setGuestName={setGuestName} submitting={submitting} onSubmit={handleSpaBooking} />
        <TransportDialog open={showTransportDialog} onOpenChange={setShowTransportDialog} transportForm={transportForm} setTransportForm={setTransportForm} guestName={guestName} setGuestName={setGuestName} submitting={submitting} onSubmit={handleTransport} />
        <LaundryDialog open={showLaundryDialog} onOpenChange={setShowLaundryDialog} laundryForm={laundryForm} setLaundryForm={setLaundryForm} submitting={submitting} onSubmit={handleLaundry} />
        <WakeupDialog open={showWakeupDialog} onOpenChange={setShowWakeupDialog} wakeupForm={wakeupForm} setWakeupForm={setWakeupForm} submitting={submitting} onSubmit={handleWakeup} />
        <RoomServiceDialog open={showRoomServiceDialog} onOpenChange={setShowRoomServiceDialog} cartItems={cartItems} setCartItems={setCartItems} guestName={guestName} setGuestName={setGuestName} submitting={submitting} onSubmit={handleRoomServiceOrder} />
        <SurveyDialog open={showSurveyDialog} onOpenChange={setShowSurveyDialog} surveyForm={surveyForm} setSurveyForm={setSurveyForm} submitting={submitting} onSubmit={handleSurvey} />
        <RestaurantDialog open={showRestaurantDialog} onOpenChange={setShowRestaurantDialog} restaurants={restaurants} restaurantForm={restaurantForm} setRestaurantForm={setRestaurantForm} selectedRestaurant={selectedRestaurant} setSelectedRestaurant={setSelectedRestaurant} availableSlots={availableSlots} setAvailableSlots={setAvailableSlots} guestName={guestName} setGuestName={setGuestName} guestPhone={guestPhone} setGuestPhone={setGuestPhone} submitting={submitting} onSubmit={handleRestaurantReservation} />
        <NotificationPanel open={showNotifPanel} onOpenChange={setShowNotifPanel} notifications={notifications} pushSubscribed={pushSubscribed} pushLoading={pushLoading} onPushToggle={handlePushToggle} onShowPrefs={() => { setShowNotifPanel(false); setShowNotifPrefs(true); }} />
        <NotifPrefsDialog open={showNotifPrefs} onOpenChange={setShowNotifPrefs} notifPrefs={notifPrefs} onPrefChange={handlePrefChange} />
      </div>
    </GuestProvider>
  );
}
