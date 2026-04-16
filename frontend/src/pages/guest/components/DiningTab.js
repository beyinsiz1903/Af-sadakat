import React from 'react';
import { Button } from '../../../components/ui/button';
import { ShoppingBag, UtensilsCrossed } from 'lucide-react';
import { useGuest } from '../GuestContext';

export default function DiningTab({ menuData, cartItems, onAddToCart, onShowCart }) {
  const { t } = useGuest();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{t('Room Service Menu', 'Oda Servisi Menusu')}</h3>
        {cartItems.length > 0 && (
          <Button size="sm" onClick={onShowCart}>
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
              <Button size="sm" variant="outline" className="h-8 w-8 p-0" onClick={() => onAddToCart(item)}>+</Button>
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
  );
}
