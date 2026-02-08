import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { ordersAPI } from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { statusColors, formatCurrency, timeAgo } from '../lib/utils';
import { UtensilsCrossed, PhoneCall, Receipt } from 'lucide-react';
import { toast } from 'sonner';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const ORDER_STATUSES = ['RECEIVED', 'PREPARING', 'SERVED', 'COMPLETED'];

function SortableOrderCard({ order }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: order.id,
    data: { status: order.status },
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const getOrderIcon = (type) => {
    switch (type) {
      case 'call_waiter': return <PhoneCall className="w-4 h-4 text-amber-400" />;
      case 'request_bill': return <Receipt className="w-4 h-4 text-emerald-400" />;
      default: return <UtensilsCrossed className="w-4 h-4" />;
    }
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all cursor-grab active:cursor-grabbing">
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
        </CardContent>
      </Card>
    </div>
  );
}

export default function OrdersBoard() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [view, setView] = useState('board');
  const [activeId, setActiveId] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

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

  const handleDragStart = (event) => setActiveId(event.active.id);

  const handleDragEnd = (event) => {
    const { active, over } = event;
    setActiveId(null);
    if (!over) return;

    const draggedOrder = orders.find(o => o.id === active.id);
    if (!draggedOrder) return;

    const overOrder = orders.find(o => o.id === over.id);
    let targetStatus = overOrder?.status;

    if (targetStatus && targetStatus !== draggedOrder.status) {
      updateMutation.mutate({ id: draggedOrder.id, status: targetStatus });
    }
  };

  const activeOrder = activeId ? orders.find(o => o.id === activeId) : null;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Kitchen Orders</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            {orders.filter(o => ['RECEIVED', 'PREPARING'].includes(o.status)).length} active orders - Drag to update status
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
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {ORDER_STATUSES.map(status => (
              <div key={status} className="space-y-3" data-testid={`orders-board-column-${status.toLowerCase()}`}>
                <div className="flex items-center gap-2 px-1">
                  <Badge className={`${statusColors[status]} border text-xs`}>{status}</Badge>
                  <span className="text-sm text-[hsl(var(--muted-foreground))]">{grouped[status]?.length || 0}</span>
                </div>
                <ScrollArea className="h-[calc(100vh-260px)]">
                  <SortableContext items={(grouped[status] || []).map(o => o.id)} strategy={verticalListSortingStrategy}>
                    <div className="space-y-3 pr-2 min-h-[200px]">
                      {(grouped[status] || []).map(order => (
                        <SortableOrderCard key={order.id} order={order} />
                      ))}
                      {(grouped[status] || []).length === 0 && (
                        <div className="text-center py-8 text-sm text-[hsl(var(--muted-foreground))] border-2 border-dashed border-[hsl(var(--border))] rounded-lg">
                          Drop here
                        </div>
                      )}
                    </div>
                  </SortableContext>
                </ScrollArea>
              </div>
            ))}
          </div>

          <DragOverlay>
            {activeOrder ? (
              <Card className="bg-[hsl(var(--card))] border-[hsl(var(--primary))] shadow-2xl w-[280px] opacity-90">
                <CardContent className="p-4">
                  <span className="font-semibold">Table {activeOrder.table_number}</span>
                  <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
                    {activeOrder.items?.length || 0} items - {formatCurrency(activeOrder.total)}
                  </p>
                </CardContent>
              </Card>
            ) : null}
          </DragOverlay>
        </DndContext>
      ) : (
        <div className="space-y-2">
          {orders.map(order => (
            <Card key={order.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <UtensilsCrossed className="w-4 h-4" />
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
