import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { aiAPI } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Star, MessageSquare, Sparkles, Send, Loader2, ThumbsUp, ThumbsDown, Minus } from 'lucide-react';
import { formatDate, timeAgo } from '../lib/utils';
import { toast } from 'sonner';

const sentimentConfig = {
  positive: { label: 'Positive', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25', icon: ThumbsUp },
  neutral: { label: 'Neutral', color: 'bg-gray-500/10 text-gray-400 border-gray-500/25', icon: Minus },
  negative: { label: 'Negative', color: 'bg-rose-500/10 text-rose-400 border-rose-500/25', icon: ThumbsDown },
};

export default function ReviewsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [sourceFilter, setSourceFilter] = useState('all');
  const [selectedReview, setSelectedReview] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  const { data: reviewsData, refetch } = useQuery({
    queryKey: ['reviews', tenant?.slug, sourceFilter],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/reviews`, {
      params: { source: sourceFilter === 'all' ? undefined : sourceFilter }
    }).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const reviews = reviewsData?.data || [];

  // Seed reviews if empty
  useEffect(() => {
    if (reviews.length === 0 && tenant?.slug) {
      api.post(`/tenants/${tenant.slug}/reviews/seed-stubs`).then(() => refetch()).catch(() => {});
    }
  }, [reviews.length, tenant?.slug]);

  const replyMutation = useMutation({
    mutationFn: ({ reviewId, content }) => api.post(`/tenants/${tenant?.slug}/reviews/${reviewId}/reply`, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries(['reviews']);
      toast.success('Reply saved');
      setSelectedReview(null);
      setReplyText('');
      setAiSuggestion(null);
    },
  });

  const generateAiReply = async (reviewText) => {
    setAiLoading(true);
    try {
      const { data } = await aiAPI.suggestReply(tenant?.slug, { message: reviewText, sector: 'hotel' });
      setAiSuggestion(data.suggestion);
    } catch (e) {}
    setAiLoading(false);
  };

  // Stats
  const avgRating = reviews.length > 0 ? (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1) : 0;
  const sentimentCounts = {
    positive: reviews.filter(r => r.sentiment === 'positive').length,
    neutral: reviews.filter(r => r.sentiment === 'neutral').length,
    negative: reviews.filter(r => r.sentiment === 'negative').length,
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Reviews</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            {reviews.length} reviews - Avg {avgRating}/5
          </p>
        </div>
        <Select value={sourceFilter} onValueChange={setSourceFilter}>
          <SelectTrigger className="w-[200px] bg-[hsl(var(--card))]" data-testid="review-source-filter">
            <SelectValue placeholder="All Sources" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sources</SelectItem>
            <SelectItem value="GOOGLE_REVIEWS">Google Reviews</SelectItem>
            <SelectItem value="TRIPADVISOR">TripAdvisor</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Sentiment summary */}
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(sentimentCounts).map(([key, count]) => {
          const config = sentimentConfig[key];
          const Icon = config.icon;
          return (
            <Card key={key} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${config.color.split(' ')[0]} flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${config.color.split(' ')[1]}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold">{count}</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))] capitalize">{key}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Reviews list */}
      <div className="space-y-3">
        {reviews.map(review => {
          const sConfig = sentimentConfig[review.sentiment] || sentimentConfig.neutral;
          return (
            <Card key={review.id} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all">
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-0.5">
                      {[...Array(5)].map((_, i) => (
                        <Star key={i} className={`w-4 h-4 ${i < review.rating ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />
                      ))}
                    </div>
                    <Badge className={`${sConfig.color} border text-xs`}>{sConfig.label}</Badge>
                    <Badge variant="secondary" className="text-xs">{review.source === 'GOOGLE_REVIEWS' ? 'Google' : 'TripAdvisor'}</Badge>
                  </div>
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">{formatDate(review.created_at)}</span>
                </div>
                <p className="text-sm mb-2">{review.text}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">by {review.author}</span>
                  <div className="flex gap-2">
                    {review.replied ? (
                      <Badge className="bg-emerald-500/10 text-emerald-400 text-xs">Replied</Badge>
                    ) : (
                      <Button size="sm" variant="outline" className="text-xs h-7" onClick={() => { setSelectedReview(review); generateAiReply(review.text); }} data-testid={`reply-review-${review.id}`}>
                        <MessageSquare className="w-3 h-3 mr-1" /> Reply
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Reply Dialog */}
      <Dialog open={!!selectedReview} onOpenChange={(open) => !open && setSelectedReview(null)}>
        <DialogContent className="bg-[hsl(var(--card))] border-[hsl(var(--border))] max-w-lg">
          {selectedReview && (
            <>
              <DialogHeader>
                <DialogTitle>Reply to Review</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="p-3 bg-[hsl(var(--secondary))] rounded-lg">
                  <div className="flex items-center gap-1 mb-2">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className={`w-3.5 h-3.5 ${i < selectedReview.rating ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />
                    ))}
                    <span className="text-xs text-[hsl(var(--muted-foreground))] ml-2">{selectedReview.author}</span>
                  </div>
                  <p className="text-sm">{selectedReview.text}</p>
                </div>

                {(aiSuggestion || aiLoading) && (
                  <div className="p-3 bg-[hsl(var(--primary)/0.05)] border border-[hsl(var(--primary)/0.2)] rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
                      <span className="text-xs font-medium text-[hsl(var(--primary))]">AI Suggested Reply</span>
                    </div>
                    {aiLoading ? (
                      <div className="flex items-center gap-2 text-xs"><Loader2 className="w-3 h-3 animate-spin" /> Generating...</div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <p className="text-sm flex-1">{aiSuggestion}</p>
                        <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setReplyText(aiSuggestion)}>Use</Button>
                      </div>
                    )}
                  </div>
                )}

                <Textarea value={replyText} onChange={(e) => setReplyText(e.target.value)} placeholder="Write your reply..." className="bg-[hsl(var(--secondary))] min-h-[100px]" data-testid="review-reply-text" />
                <Button onClick={() => replyMutation.mutate({ reviewId: selectedReview.id, content: replyText })} disabled={!replyText.trim()} className="w-full" data-testid="submit-review-reply">
                  <Send className="w-4 h-4 mr-2" /> Save Reply
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
