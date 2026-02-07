import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatCurrency(amount) {
  return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(amount);
}

export function timeAgo(dateStr) {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const seconds = Math.floor((now - date) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export const statusColors = {
  OPEN: 'bg-blue-500/10 text-blue-400 border-blue-500/25',
  IN_PROGRESS: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/25',
  DONE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  CLOSED: 'bg-gray-500/10 text-gray-400 border-gray-500/25',
  RECEIVED: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
  PREPARING: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/25',
  SERVED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  COMPLETED: 'bg-gray-500/10 text-gray-400 border-gray-500/25',
  CANCELLED: 'bg-rose-500/10 text-rose-400 border-rose-500/25',
};

export const priorityColors = {
  low: 'bg-gray-500/10 text-gray-400',
  normal: 'bg-blue-500/10 text-blue-400',
  high: 'bg-amber-500/10 text-amber-400',
  urgent: 'bg-rose-500/10 text-rose-400',
};

export const categoryIcons = {
  housekeeping: 'Sparkles',
  maintenance: 'Wrench',
  room_service: 'UtensilsCrossed',
  reception: 'BellRing',
  other: 'HelpCircle',
};
