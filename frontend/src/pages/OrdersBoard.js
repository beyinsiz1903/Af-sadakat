import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { ordersAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { statusColors, formatCurrency, timeAgo, formatDate } from '../lib/utils';
import { UtensilsCrossed, Clock, ArrowRight, ChefHat, HandPlatter, PhoneCall, Receipt } from 'lucide-react';
import { toast } from 'sonner';

const ORDER_STATUSES = ['RECEIVED', 'PREPARING', 'SERVED', 'COMPLETED'];

export default function OrdersBoard() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [view, setView] = useState('board');

  const { data: ordersData, refetch } = useQuery({
    queryKey: ['orders', tenant?.slug],
    queryFn: () => ordersAPI.list(tenant?.slug, { limit: 200 }).then(r => r.data),
    enabled: !!tenant?.slug,
    refetchInterval: 8000,
  });

  const orders = ordersData?.data || [];

  const updateMutation = useMutation({
    mutationFn: ({ id, status }) => ordersAPI.updateStatus(tenant?.slug, id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries(['orders']);
      toast.success('Order status updated');
    },
  });

  useEffect(() => {
    if (!window.__ws) return;
    const unsub = window.__ws.on('order', () => refetch());
    return unsub;
  }, [refetch]);

  const grouped = ORDER_STATUSES.reduce((acc, s) => {
    acc[s] = orders.filter(o => o.status === s);
    return acc;
  }, {});

  const getOrderIcon = (type) => {
    switch (type) {
      case 'call_waiter': return <PhoneCall className="w-4 h-4 text-amber-400" />;
      case 'request_bill': return <Receipt className="w-4 h-4 text-emerald-400" />;
      default: return <UtensilsCrossed className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Kitchen Orders</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            {orders.filter(o => ['RECEIVED', 'PREPARING'].includes(o.status)).length} active orders
          </p>
        </div>
        <Tabs value={view} onValueChange={setView}>
          <TabsList className="bg-[hsl(var(--secondary))]">
            <TabsTrigger value="board">Board</TabsTrigger>
            <TabsTrigger value="list">List</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {view === 'board' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {ORDER_STATUSES.map(status => (
            <div key={status} className="space-y-3" data-testid={`orders-board-column-${status.toLowerCase()}`}>
              <div className="flex items-center gap-2 px-1">
                <Badge className={`${statusColors[status]} border text-xs`}>{status}</Badge>
                <span className="text-sm text-[hsl(var(--muted-foreground))]">{grouped[status]?.length || 0}</span>
              </div>
              <ScrollArea className="h-[calc(100vh-260px)]">
                <div className="space-y-3 pr-2">
                  {(grouped[status] || []).map(order => (
                    <Card key={order.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all">
                      <CardContent className="p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {getOrderIcon(order.order_type)}
                            <span className="font-semibold">Table {order.table_number}</span>
                          </div>
                          <span className="text-xs text-[hsl(var(--muted-foreground))]">{timeAgo(order.created_at)}</span>
                        </div>
                        {order.order_type === 'dine_in' && order.items?.length > 0 && (
                          <div className="space-y-1">
                            {order.items.map((item, i) => (
                              <div key={i} className="flex justify-between text-sm">
                                <span className="text-[hsl(var(--muted-foreground))]">{item.quantity}x {item.menu_item_name}</span>
                                <span>{formatCurrency(item.price * item.quantity)}</span>
                              </div>
                            ))}
                            <div className="flex justify-between text-sm font-semibold pt-2 border-t border-[hsl(var(--border))]">
                              <span>Total</span>
                              <span>{formatCurrency(order.total)}</span>
                            </div>
                          </div>
                        )}
                        {order.order_type === 'call_waiter' && (
                          <p className="text-sm text-amber-400 font-medium">Waiter requested</p>
                        )}
                        {order.order_type === 'request_bill' && (
                          <p className="text-sm text-emerald-400 font-medium">Bill requested</p>
                        )}
                        {order.notes && (
                          <p className="text-xs text-[hsl(var(--muted-foreground))] italic">{order.notes}</p>
                        )}
                        {status !== 'COMPLETED' && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="w-full text-xs h-8"
                            onClick={() => {
                              const next = ORDER_STATUSES[ORDER_STATUSES.indexOf(status) + 1];
                              if (next) updateMutation.mutate({ id: order.id, status: next });
                            }}
                            data-testid={`order-advance-${order.id}`}
                          >
                            <ArrowRight className="w-3 h-3 mr-1" />
                            {ORDER_STATUSES[ORDER_STATUSES.indexOf(status) + 1]}
                          </Button>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                  {(grouped[status] || []).length === 0 && (
                    <div className="text-center py-8 text-sm text-[hsl(var(--muted-foreground))]">No orders</div>
                  )}
                </div>
              </ScrollArea>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {orders.map(order => (
            <Card key={order.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {getOrderIcon(order.order_type)}
                  <div>
                    <p className="font-medium">Table {order.table_number}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{order.items?.length || 0} items - {formatCurrency(order.total)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge className={`${statusColors[order.status]} border text-xs`}>{order.status}</Badge>
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">{timeAgo(order.created_at)}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
