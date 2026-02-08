import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { paymentsAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { CreditCard, CheckCircle2, CalendarDays, Users, BedDouble, Loader2, Hotel, AlertCircle } from 'lucide-react';

export default function PaymentPage() {
  const { paymentLinkId } = useParams();
  const [paymentState, setPaymentState] = useState('idle'); // idle, processing, success, error
  const [confirmationCode, setConfirmationCode] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['payment-page', paymentLinkId],
    queryFn: () => paymentsAPI.getPaymentData(paymentLinkId).then(r => r.data),
    enabled: !!paymentLinkId,
    retry: 1,
  });

  const checkoutMutation = useMutation({
    mutationFn: () => paymentsAPI.checkout(paymentLinkId),
    onSuccess: () => {
      // After checkout initiated, simulate success
      setTimeout(() => {
        succeedMutation.mutate();
      }, 1500);
    },
    onError: (e) => {
      setPaymentState('error');
    },
  });

  const succeedMutation = useMutation({
    mutationFn: () => paymentsAPI.mockSucceed({ paymentLinkId }),
    onSuccess: (res) => {
      setPaymentState('success');
      setConfirmationCode(res.data?.confirmation_code || res.data?.reservation?.confirmation_code || '');
      refetch();
    },
    onError: () => setPaymentState('error'),
  });

  const handlePay = () => {
    setPaymentState('processing');
    checkoutMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md w-full">
          <CardContent className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">Payment Link Not Found</h2>
            <p className="text-[hsl(var(--muted-foreground))]">This payment link may have expired or is invalid.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Already paid state
  if (data.status === 'ALREADY_PAID' || paymentState === 'success') {
    const reservation = data.reservation || {};
    const code = confirmationCode || reservation.confirmation_code || '';
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md w-full">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Payment Confirmed!</h2>
            <p className="text-[hsl(var(--muted-foreground))] mb-6">Your reservation has been confirmed.</p>
            {code && (
              <div className="bg-[hsl(var(--secondary))] rounded-xl p-6 mb-4">
                <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">Confirmation Code</p>
                <p className="text-3xl font-mono font-bold text-[hsl(var(--primary))]">{code}</p>
              </div>
            )}
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Please save your confirmation code. You'll need it at check-in.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const offer = data.offer || {};
  const pl = data.payment_link || {};

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4">
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md w-full">
        <CardHeader className="text-center border-b border-[hsl(var(--border))] pb-4">
          <div className="w-12 h-12 rounded-xl bg-[hsl(var(--primary)/0.2)] flex items-center justify-center mx-auto mb-3">
            <Hotel className="w-6 h-6 text-[hsl(var(--primary))]" />
          </div>
          <CardTitle className="text-lg">{data.tenant_name}</CardTitle>
          {data.property_name && (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">{data.property_name}</p>
          )}
        </CardHeader>
        <CardContent className="p-6">
          <h3 className="text-sm font-medium text-[hsl(var(--muted-foreground))] mb-4">Reservation Details</h3>
          
          <div className="space-y-3 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <BedDouble className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                <span>Room Type</span>
              </div>
              <span className="font-medium capitalize">{offer.room_type}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <CalendarDays className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                <span>Check-in</span>
              </div>
              <span className="font-medium">{offer.check_in}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <CalendarDays className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                <span>Check-out</span>
              </div>
              <span className="font-medium">{offer.check_out}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <Users className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                <span>Guests</span>
              </div>
              <span className="font-medium">{offer.guests_count}</span>
            </div>
            {offer.notes && (
              <div className="bg-[hsl(var(--secondary))] rounded-lg p-3 text-sm text-[hsl(var(--muted-foreground))]">
                {offer.notes}
              </div>
            )}
          </div>

          <div className="border-t border-[hsl(var(--border))] pt-4 mb-6">
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">Total</span>
              <span className="text-2xl font-bold text-[hsl(var(--primary))]">
                {offer.currency} {offer.price_total?.toLocaleString()}
              </span>
            </div>
          </div>

          {paymentState === 'error' && (
            <div className="bg-rose-500/10 border border-rose-500/25 rounded-lg p-3 mb-4 text-sm text-rose-400">
              Payment failed. Please try again.
            </div>
          )}

          <Button 
            onClick={handlePay} 
            disabled={paymentState === 'processing'}
            className="w-full h-12 text-base"
            data-testid="pay-now-btn"
          >
            {paymentState === 'processing' ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                Processing Payment...
              </>
            ) : (
              <>
                <CreditCard className="w-5 h-5 mr-2" />
                Pay Now (Mock)
              </>
            )}
          </Button>

          <p className="text-xs text-center text-[hsl(var(--muted-foreground))] mt-4">
            This is a mock payment for demo purposes. No real charge will be made.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
