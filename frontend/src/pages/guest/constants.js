import {
  Hotel, Sparkles, Wrench, UtensilsCrossed, BellRing, HelpCircle,
  Shirt, Heart, Car, AlarmClock, KeyRound, Coffee, LogOut, AlertCircle,
  Luggage, CalendarDays, ClipboardList, MessageCircle, Receipt, Crown
} from 'lucide-react';

export const TABS = [
  { id: 'home', label: 'Home', labelTr: 'Ana Sayfa', icon: Hotel },
  { id: 'services', label: 'Services', labelTr: 'Servisler', icon: ClipboardList },
  { id: 'dining', label: 'Dining', labelTr: 'Yemek', icon: UtensilsCrossed },
  { id: 'folio', label: 'Folio', labelTr: 'Folyo', icon: Receipt },
  { id: 'loyalty', label: 'Loyalty', labelTr: 'Sadakat', icon: Crown },
  { id: 'requests', label: 'My Requests', labelTr: 'Taleplerim', icon: MessageCircle },
];

export const categoryConfig = {
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
  restaurant_reservation: { label: 'Restaurant', labelTr: 'Restoran Rez.', icon: CalendarDays, color: 'text-violet-400', bg: 'bg-violet-500/10' },
  other: { label: 'Other', labelTr: 'Diger', icon: HelpCircle, color: 'text-gray-400', bg: 'bg-gray-500/10' },
};

export const statusSteps = ['OPEN', 'IN_PROGRESS', 'DONE', 'CLOSED'];
