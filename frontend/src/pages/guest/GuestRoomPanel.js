import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { guestAPI } from '../../lib/api';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { statusColors, timeAgo, formatDate } from '../../lib/utils';
import { Hotel, Sparkles, Wrench, UtensilsCrossed, BellRing, HelpCircle, Send, Star, Loader2, CheckCircle2, Clock, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

const categoryConfig = {
  housekeeping: { label: 'Housekeeping', icon: Sparkles, color: 'text-blue-400' },
  maintenance: { label: 'Maintenance', icon: Wrench, color: 'text-amber-400' },
  room_service: { label: 'Room Service', icon: UtensilsCrossed, color: 'text-emerald-400' },
  reception: { label: 'Reception', icon: BellRing, color: 'text-purple-400' },
  other: { label: 'Other', icon: HelpCircle, color: 'text-gray-400' },
};

const statusSteps = ['OPEN', 'IN_PROGRESS', 'DONE', 'CLOSED'];

export default function GuestRoomPanel() {
  const { tenantSlug, roomCode } = useParams();
  const [roomInfo, setRoomInfo] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    category: 'housekeeping',
    description: '',
    priority: 'normal',
    guest_name: '',
    guest_phone: '',
  });
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
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadRequests = async () => {
    try {
      const { data } = await guestAPI.roomRequests(tenantSlug, roomCode);
      setRequests(data);
    } catch (e) {}
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.description.trim()) return;
    setSubmitting(true);
    try {
      await guestAPI.createRequest(tenantSlug, roomCode, form);
      toast.success('Request submitted successfully!');
      setForm({ ...form, description: '', priority: 'normal' });
      loadRequests();
    } catch (e) {
      toast.error('Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRate = async (requestId) => {
    if (ratingForm.rating < 1) return;
    try {
      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      await fetch(`${BACKEND_URL}/api/tenants/${tenantSlug}/requests/${requestId}/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: ratingForm.rating, comment: ratingForm.comment }),
      });
      toast.success('Thank you for your feedback!');
      setRatingForm({ requestId: null, rating: 0, comment: '' });
      loadRequests();
    } catch (e) {
      toast.error('Failed to submit rating');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  if (!roomInfo) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md w-full">
          <CardContent className="p-8 text-center">
            <Hotel className="w-12 h-12 mx-auto mb-4 text-[hsl(var(--muted-foreground))]" />
            <h2 className="text-xl font-bold">Room Not Found</h2>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-2">This QR code link is invalid or expired.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--background))]">
      {/* Header */}
      <div className="guest-header-gradient bg-noise">
        <div className="relative z-10 max-w-md mx-auto px-4 pt-8 pb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-[hsl(var(--primary))] flex items-center justify-center">
              <Hotel className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">{roomInfo.tenant.name}</h1>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Room {roomInfo.room.room_number} - {roomInfo.room.room_type}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 -mt-2">
        {/* Request Form */}
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] mb-6">
          <CardContent className="p-5">
            <h2 className="font-semibold mb-4">How can we help you?</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Category selector */}
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(categoryConfig).filter(([k]) => k !== 'other').map(([key, config]) => {
                  const Icon = config.icon;
                  return (
                    <button
                      key={key}
                      type="button"
                      className={`p-3 rounded-xl border text-center transition-all ${
                        form.category === key
                          ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)]'
                          : 'border-[hsl(var(--border))] bg-[hsl(var(--secondary))] hover:border-[hsl(var(--primary)/0.3)]'
                      }`}
                      onClick={() => setForm({ ...form, category: key })}
                      data-testid={`category-${key}`}
                    >
                      <Icon className={`w-5 h-5 mx-auto mb-1 ${config.color}`} />
                      <span className="text-xs font-medium">{config.label}</span>
                    </button>
                  );
                })}
              </div>

              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Describe what you need..."
                className="bg-[hsl(var(--secondary))] border-[hsl(var(--border))] min-h-[80px]"
                data-testid="request-description"
              />

              <div className="grid grid-cols-2 gap-3">
                <Input
                  value={form.guest_name}
                  onChange={(e) => setForm({ ...form, guest_name: e.target.value })}
                  placeholder="Your name (optional)"
                  className="bg-[hsl(var(--secondary))] border-[hsl(var(--border))]"
                  data-testid="guest-name-input"
                />
                <Input
                  value={form.guest_phone}
                  onChange={(e) => setForm({ ...form, guest_phone: e.target.value })}
                  placeholder="Phone (optional)"
                  className="bg-[hsl(var(--secondary))] border-[hsl(var(--border))]"
                />
              </div>

              <Button type="submit" className="w-full" disabled={!form.description.trim() || submitting} data-testid="submit-request-btn">
                {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                Submit Request
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Active Requests */}
        {requests.length > 0 && (
          <div className="mb-6">
            <h3 className="font-semibold mb-3">Your Requests</h3>
            <div className="space-y-3">
              {requests.map(req => {
                const cat = categoryConfig[req.category] || categoryConfig.other;
                const Icon = cat.icon;
                const stepIndex = statusSteps.indexOf(req.status);

                return (
                  <Card key={req.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3 mb-3">
                        <div className="w-9 h-9 rounded-lg bg-[hsl(var(--secondary))] flex items-center justify-center flex-shrink-0">
                          <Icon className={`w-4 h-4 ${cat.color}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium">{req.description}</p>
                          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{timeAgo(req.created_at)}</p>
                        </div>
                        <Badge className={`${statusColors[req.status]} border text-xs flex-shrink-0`}>{req.status.replace('_', ' ')}</Badge>
                      </div>

                      {/* Status stepper */}
                      <div className="flex items-center gap-1 mb-3">
                        {statusSteps.map((step, i) => (
                          <React.Fragment key={step}>
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                              i <= stepIndex ? 'bg-[hsl(var(--primary))] text-white' : 'bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))]'
                            }`}>
                              {i <= stepIndex ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                            </div>
                            {i < statusSteps.length - 1 && (
                              <div className={`flex-1 h-0.5 ${i < stepIndex ? 'bg-[hsl(var(--primary))]' : 'bg-[hsl(var(--secondary))]'}`} />
                            )}
                          </React.Fragment>
                        ))}
                      </div>

                      {/* Rating */}
                      {req.status === 'DONE' && !req.rating && (
                        <div className="border-t border-[hsl(var(--border))] pt-3 mt-3">
                          <p className="text-xs text-[hsl(var(--muted-foreground))] mb-2">Rate this service:</p>
                          <div className="flex gap-1 mb-2">
                            {[1,2,3,4,5].map(n => (
                              <button
                                key={n}
                                onClick={() => setRatingForm({ ...ratingForm, requestId: req.id, rating: n })}
                                className="p-1"
                                data-testid={`rate-star-${n}`}
                              >
                                <Star className={`w-5 h-5 ${ratingForm.requestId === req.id && n <= ratingForm.rating ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />
                              </button>
                            ))}
                          </div>
                          {ratingForm.requestId === req.id && ratingForm.rating > 0 && (
                            <div className="flex gap-2">
                              <Input
                                value={ratingForm.comment}
                                onChange={(e) => setRatingForm({ ...ratingForm, comment: e.target.value })}
                                placeholder="Comment (optional)"
                                className="bg-[hsl(var(--secondary))] text-sm h-8"
                              />
                              <Button size="sm" className="h-8" onClick={() => handleRate(req.id)} data-testid="submit-rating-btn">Submit</Button>
                            </div>
                          )}
                        </div>
                      )}
                      {req.rating && (
                        <div className="flex items-center gap-1 pt-2 border-t border-[hsl(var(--border))] mt-2">
                          {[...Array(5)].map((_, i) => (
                            <Star key={i} className={`w-3.5 h-3.5 ${i < req.rating ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />
                          ))}
                          {req.rating_comment && <span className="text-xs text-[hsl(var(--muted-foreground))] ml-2">{req.rating_comment}</span>}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center pb-8">
          <div className="p-3 bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg mb-4">
            <p className="text-xs text-[hsl(var(--muted-foreground))] text-center">
              Having connection issues? Call reception: <strong>0</strong> from your room phone
            </p>
          </div>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Powered by OmniHub</p>
        </div>
      </div>
    </div>
  );
}
