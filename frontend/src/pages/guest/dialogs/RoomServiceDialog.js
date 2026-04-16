import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Send, Loader2 } from 'lucide-react';
import { useGuest } from '../GuestContext';

export default function RoomServiceDialog({ open, onOpenChange, cartItems, setCartItems, guestName, setGuestName, submitting, onSubmit }) {
  const { t } = useGuest();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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
              <Button className="w-full" onClick={onSubmit} disabled={submitting}>
                {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                {t('Place Order', 'Siparis Ver')}
              </Button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
