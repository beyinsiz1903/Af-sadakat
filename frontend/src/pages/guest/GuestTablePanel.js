import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { guestAPI } from '../../lib/api';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { ScrollArea } from '../../components/ui/scroll-area';
import { statusColors, formatCurrency, timeAgo } from '../../lib/utils';
import { UtensilsCrossed, Plus, Minus, ShoppingCart, Send, PhoneCall, Receipt, Loader2, X, ChefHat } from 'lucide-react';
import { toast } from 'sonner';

export default function GuestTablePanel() {
  const { tenantSlug, tableCode } = useParams();
  const [tableInfo, setTableInfo] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [cart, setCart] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [guestName, setGuestName] = useState('');
  const [guestPhone, setGuestPhone] = useState('');
  const [notes, setNotes] = useState('');

  useEffect(() => {
    loadData();
    const interval = setInterval(loadOrders, 8000);
    return () => clearInterval(interval);
  }, [tenantSlug, tableCode]);

  const loadData = async () => {
    try {
      const [infoRes, ordRes] = await Promise.all([
        guestAPI.tableInfo(tenantSlug, tableCode),
        guestAPI.tableOrders(tenantSlug, tableCode),
      ]);
      setTableInfo(infoRes.data);
      setOrders(ordRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadOrders = async () => {
    try {
      const { data } = await guestAPI.tableOrders(tenantSlug, tableCode);
      setOrders(data);
    } catch (e) {}
  };

  const addToCart = (item) => {
    const existing = cart.find(c => c.menu_item_id === item.id);
    if (existing) {
      setCart(cart.map(c => c.menu_item_id === item.id ? { ...c, quantity: c.quantity + 1 } : c));
    } else {
      setCart([...cart, { menu_item_id: item.id, menu_item_name: item.name, quantity: 1, price: item.price, notes: '' }]);
    }
    toast.success(`${item.name} added to cart`);
  };

  const removeFromCart = (itemId) => {
    const existing = cart.find(c => c.menu_item_id === itemId);
    if (existing && existing.quantity > 1) {
      setCart(cart.map(c => c.menu_item_id === itemId ? { ...c, quantity: c.quantity - 1 } : c));
    } else {
      setCart(cart.filter(c => c.menu_item_id !== itemId));
    }
  };

  const cartTotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  const handleOrder = async (orderType = 'dine_in') => {
    setSubmitting(true);
    try {
      await guestAPI.createOrder(tenantSlug, tableCode, {
        items: orderType === 'dine_in' ? cart : [],
        guest_name: guestName,
        guest_phone: guestPhone,
        notes,
        order_type: orderType,
      });
      toast.success(orderType === 'dine_in' ? 'Order placed!' : orderType === 'call_waiter' ? 'Waiter called!' : 'Bill requested!');
      if (orderType === 'dine_in') {
        setCart([]);
        setCartOpen(false);
      }
      setNotes('');
      loadOrders();
    } catch (e) {
      toast.error('Failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  if (!tableInfo) {
    return (
      <div className="min-h-screen bg-[hsl(var(--background))] flex items-center justify-center p-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-md w-full">
          <CardContent className="p-8 text-center">
            <UtensilsCrossed className="w-12 h-12 mx-auto mb-4 text-[hsl(var(--muted-foreground))]" />
            <h2 className="text-xl font-bold">Table Not Found</h2>
          </CardContent>
        </Card>
      </div>
    );
  }

  const categories = tableInfo.menu_categories || [];
  const items = tableInfo.menu_items || [];
  const filteredItems = selectedCategory === 'all' ? items : items.filter(i => i.category_id === selectedCategory);

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] pb-24">
      {/* Header */}
      <div className="guest-header-gradient bg-noise">
        <div className="relative z-10 max-w-md mx-auto px-4 pt-8 pb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-[hsl(var(--primary))] flex items-center justify-center">
              <ChefHat className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">{tableInfo.tenant.name}</h1>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Table {tableInfo.table.table_number} - {tableInfo.table.section}</p>
            </div>
          </div>

          {/* Quick actions */}
          <div className="flex gap-2">
            <Button size="sm" variant="outline" className="flex-1" onClick={() => handleOrder('call_waiter')} disabled={submitting} data-testid="call-waiter-btn">
              <PhoneCall className="w-4 h-4 mr-1" /> Call Waiter
            </Button>
            <Button size="sm" variant="outline" className="flex-1" onClick={() => handleOrder('request_bill')} disabled={submitting} data-testid="request-bill-btn">
              <Receipt className="w-4 h-4 mr-1" /> Request Bill
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 -mt-2">
        {/* Category tabs */}
        <div className="flex gap-2 overflow-x-auto pb-3 scrollbar-thin mb-4">
          <Button
            variant={selectedCategory === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory('all')}
            className="flex-shrink-0"
          >
            All
          </Button>
          {categories.map(cat => (
            <Button
              key={cat.id}
              variant={selectedCategory === cat.id ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(cat.id)}
              className="flex-shrink-0"
            >
              {cat.name}
            </Button>
          ))}
        </div>

        {/* Menu items */}
        <div className="space-y-3 mb-6">
          {filteredItems.map(item => {
            const inCart = cart.find(c => c.menu_item_id === item.id);
            return (
              <Card key={item.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 mr-3">
                      <h3 className="font-medium">{item.name}</h3>
                      {item.description && <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{item.description}</p>}
                      <p className="text-lg font-bold mt-2">{formatCurrency(item.price)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {inCart ? (
                        <div className="flex items-center gap-2 bg-[hsl(var(--secondary))] rounded-lg">
                          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => removeFromCart(item.id)}>
                            <Minus className="w-3 h-3" />
                          </Button>
                          <span className="text-sm font-semibold w-6 text-center">{inCart.quantity}</span>
                          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => addToCart(item)}>
                            <Plus className="w-3 h-3" />
                          </Button>
                        </div>
                      ) : (
                        <Button size="sm" onClick={() => addToCart(item)} data-testid={`guest-menu-add-to-cart-button-${item.id}`}>
                          <Plus className="w-4 h-4 mr-1" /> Add
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Active orders */}
        {orders.filter(o => o.order_type === 'dine_in').length > 0 && (
          <div className="mb-6">
            <h3 className="font-semibold mb-3">Your Orders</h3>
            <div className="space-y-3">
              {orders.filter(o => o.order_type === 'dine_in').map(order => (
                <Card key={order.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <Badge className={`${statusColors[order.status]} border text-xs`}>{order.status}</Badge>
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">{timeAgo(order.created_at)}</span>
                    </div>
                    {order.items?.map((item, i) => (
                      <div key={i} className="flex justify-between text-sm py-1">
                        <span className="text-[hsl(var(--muted-foreground))]">{item.quantity}x {item.menu_item_name}</span>
                        <span>{formatCurrency(item.price * item.quantity)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between text-sm font-semibold pt-2 border-t border-[hsl(var(--border))] mt-2">
                      <span>Total</span>
                      <span>{formatCurrency(order.total)}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Cart bar */}
      {cartCount > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-[hsl(var(--card))] border-t border-[hsl(var(--border))] p-4 z-50">
          <div className="max-w-md mx-auto">
            {cartOpen ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">Your Cart</h3>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setCartOpen(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {cart.map(item => (
                    <div key={item.menu_item_id} className="flex items-center justify-between text-sm">
                      <span>{item.quantity}x {item.menu_item_name}</span>
                      <span className="font-medium">{formatCurrency(item.price * item.quantity)}</span>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} placeholder="Your name" className="bg-[hsl(var(--secondary))] text-sm h-9" />
                  <Input value={guestPhone} onChange={(e) => setGuestPhone(e.target.value)} placeholder="Phone" className="bg-[hsl(var(--secondary))] text-sm h-9" />
                </div>
                <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Special notes..." className="bg-[hsl(var(--secondary))] text-sm h-9" />
                <Button className="w-full" onClick={() => handleOrder('dine_in')} disabled={submitting} data-testid="place-order-btn">
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                  Place Order - {formatCurrency(cartTotal)}
                </Button>
              </div>
            ) : (
              <Button className="w-full" onClick={() => setCartOpen(true)} data-testid="view-cart-btn">
                <ShoppingCart className="w-4 h-4 mr-2" />
                View Cart ({cartCount}) - {formatCurrency(cartTotal)}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
