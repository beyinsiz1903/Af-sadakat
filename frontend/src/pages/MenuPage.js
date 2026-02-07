import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import { menuAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Plus, Trash2, Edit } from 'lucide-react';
import { toast } from 'sonner';
import { formatCurrency } from '../lib/utils';

export default function MenuPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [catDialogOpen, setCatDialogOpen] = useState(false);
  const [itemDialogOpen, setItemDialogOpen] = useState(false);
  const [newCat, setNewCat] = useState({ name: '', sort_order: 0 });
  const [newItem, setNewItem] = useState({ name: '', description: '', price: '', category_id: '', available: true });
  const [selectedCat, setSelectedCat] = useState('all');

  const { data: categories = [] } = useQuery({
    queryKey: ['menu-categories', tenant?.slug],
    queryFn: () => menuAPI.listCategories(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const { data: items = [] } = useQuery({
    queryKey: ['menu-items', tenant?.slug, selectedCat],
    queryFn: () => menuAPI.listItems(tenant?.slug, { category_id: selectedCat === 'all' ? undefined : selectedCat }).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const createCatMutation = useMutation({
    mutationFn: (data) => menuAPI.createCategory(tenant?.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['menu-categories']);
      toast.success('Category created');
      setNewCat({ name: '', sort_order: 0 });
      setCatDialogOpen(false);
    },
  });

  const createItemMutation = useMutation({
    mutationFn: (data) => menuAPI.createItem(tenant?.slug, { ...data, price: parseFloat(data.price) }),
    onSuccess: () => {
      queryClient.invalidateQueries(['menu-items']);
      toast.success('Item created');
      setNewItem({ name: '', description: '', price: '', category_id: '', available: true });
      setItemDialogOpen(false);
    },
  });

  const deleteItemMutation = useMutation({
    mutationFn: (id) => menuAPI.deleteItem(tenant?.slug, id),
    onSuccess: () => { queryClient.invalidateQueries(['menu-items']); toast.success('Item deleted'); },
  });

  const toggleItemMutation = useMutation({
    mutationFn: ({ id, available }) => menuAPI.updateItem(tenant?.slug, id, { available }),
    onSuccess: () => { queryClient.invalidateQueries(['menu-items']); },
  });

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Menu</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{categories.length} categories, {items.length} items</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={catDialogOpen} onOpenChange={setCatDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" data-testid="add-category-btn"><Plus className="w-4 h-4 mr-2" /> Category</Button>
            </DialogTrigger>
            <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <DialogHeader><DialogTitle>Add Category</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <Input value={newCat.name} onChange={(e) => setNewCat({...newCat, name: e.target.value})} placeholder="Main Course" className="bg-[hsl(var(--secondary))]" data-testid="category-name-input" />
                <Input type="number" value={newCat.sort_order} onChange={(e) => setNewCat({...newCat, sort_order: parseInt(e.target.value) || 0})} placeholder="Sort order" className="bg-[hsl(var(--secondary))]" />
                <Button onClick={() => createCatMutation.mutate(newCat)} disabled={!newCat.name} className="w-full" data-testid="create-category-btn">Create</Button>
              </div>
            </DialogContent>
          </Dialog>
          <Dialog open={itemDialogOpen} onOpenChange={setItemDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-item-btn"><Plus className="w-4 h-4 mr-2" /> Menu Item</Button>
            </DialogTrigger>
            <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <DialogHeader><DialogTitle>Add Menu Item</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <Input value={newItem.name} onChange={(e) => setNewItem({...newItem, name: e.target.value})} placeholder="Item name" className="bg-[hsl(var(--secondary))]" data-testid="item-name-input" />
                <Textarea value={newItem.description} onChange={(e) => setNewItem({...newItem, description: e.target.value})} placeholder="Description" className="bg-[hsl(var(--secondary))]" />
                <Input type="number" value={newItem.price} onChange={(e) => setNewItem({...newItem, price: e.target.value})} placeholder="Price" className="bg-[hsl(var(--secondary))]" data-testid="item-price-input" />
                <Select value={newItem.category_id} onValueChange={(v) => setNewItem({...newItem, category_id: v})}>
                  <SelectTrigger className="bg-[hsl(var(--secondary))]" data-testid="item-category-select">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Button onClick={() => createItemMutation.mutate(newItem)} disabled={!newItem.name || !newItem.price || !newItem.category_id} className="w-full" data-testid="create-item-btn">Create Item</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
        <Button variant={selectedCat === 'all' ? 'default' : 'outline'} size="sm" onClick={() => setSelectedCat('all')}>All</Button>
        {categories.map(c => (
          <Button key={c.id} variant={selectedCat === c.id ? 'default' : 'outline'} size="sm" onClick={() => setSelectedCat(c.id)}>{c.name}</Button>
        ))}
      </div>

      {/* Items grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {items.map(item => {
          const cat = categories.find(c => c.id === item.category_id);
          return (
            <Card key={item.id} className={`bg-[hsl(var(--card))] border-[hsl(var(--border))] ${!item.available ? 'opacity-50' : ''}`}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium">{item.name}</h3>
                    {item.description && <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 line-clamp-2">{item.description}</p>}
                  </div>
                  <Switch checked={item.available} onCheckedChange={(v) => toggleItemMutation.mutate({ id: item.id, available: v })} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-bold">{formatCurrency(item.price)}</span>
                  {cat && <Badge variant="secondary" className="text-xs">{cat.name}</Badge>}
                </div>
                <Button variant="ghost" size="sm" className="w-full text-xs h-7 text-[hsl(var(--destructive))]" onClick={() => deleteItemMutation.mutate(item.id)}>
                  <Trash2 className="w-3 h-3 mr-1" /> Remove
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
