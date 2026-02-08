import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ScrollArea } from '../components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Star, MessageSquare, Sparkles, Send, Loader2, ThumbsUp, ThumbsDown, Minus, X } from 'lucide-react';
import { formatDate, timeAgo } from '../lib/utils';
import { toast } from 'sonner';

const sentimentConfig = {
  POS: { label: 'Positive', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25', icon: ThumbsUp },
  NEU: { label: 'Neutral', color: 'bg-gray-500/10 text-gray-400 border-gray-500/25', icon: Minus },
  NEG: { label: 'Negative', color: 'bg-rose-500/10 text-rose-400 border-rose-500/25', icon: ThumbsDown },
};

export default function ReviewsPage() {
  const tenant = useAuthStore((s) => s.tenant);
  const queryClient = useQueryClient();
  const [sourceFilter, setSourceFilter] = useState('all');
  const [selectedReview, setSelectedReview] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [aiSuggestion, setAiSuggestion] = useState(null);

  // V2 API
  const { data: reviewsData, refetch } = useQuery({
    queryKey: ['v2-reviews', tenant?.slug, sourceFilter],
    queryFn: () => api.get(`/v2/reviews/tenants/${tenant?.slug}`, {
      params: { source: sourceFilter === 'all' ? undefined : sourceFilter, limit: 50 }
    }).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  const reviews = reviewsData?.data || [];
  const summary = reviewsData?.summary || { positive: 0, neutral: 0, negative: 0 };

  // Pull connectors to seed reviews if empty
  const pullMutation = useMutation({
    mutationFn: () => api.post(`/v2/inbox/tenants/${tenant?.slug}/connectors/pull-now`),
    onSuccess: (res) => {
      refetch();
      toast.success(`Pulled ${res.data.reviews_created} reviews, ${res.data.messages_created} messages`);
    },
  });

  // Reply
  const replyMutation = useMutation({
    mutationFn: ({ reviewId, text }) => api.post(`/v2/reviews/tenants/${tenant?.slug}/${reviewId}/reply`, { text }),
    onSuccess: () => {
      queryClient.invalidateQueries(['v2-reviews']);
      toast.success('Reply saved');
      setSelectedReview(null);
      setReplyText('');
      setAiSuggestion(null);
    },
  });

  // AI Suggest
  const suggestMutation = useMutation({
    mutationFn: (reviewId) => api.post(`/v2/reviews/tenants/${tenant?.slug}/${reviewId}/ai-suggest`),
    onSuccess: (res) => setAiSuggestion(res.data),
    onError: (err) => {
      const detail = err.response?.data?.detail;
      if (detail?.code === 'AI_LIMIT_EXCEEDED') toast.error(detail.message);
      else toast.error('AI suggestion failed');
    },
  });

  const avgRating = reviews.length > 0 ? (reviews.reduce((s, r) => s + (r.rating || 0), 0) / reviews.length).toFixed(1) : '0';

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Reviews</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            {reviewsData?.total || 0} reviews - Avg {avgRating}/5
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => pullMutation.mutate()} disabled={pullMutation.isPending} data-testid="pull-reviews-btn">
            {pullMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
            Pull Now
          </Button>
          <Select value={sourceFilter} onValueChange={setSourceFilter}>
            <SelectTrigger className="w-[180px] bg-[hsl(var(--card))]" data-testid="review-source-filter">
              <SelectValue placeholder="All Sources" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="GOOGLE_REVIEWS">Google Reviews</SelectItem>
              <SelectItem value="TRIPADVISOR">TripAdvisor</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Sentiment Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { key: 'positive', sentiment: 'POS', count: summary.positive },
          { key: 'neutral', sentiment: 'NEU', count: summary.neutral },
          { key: 'negative', sentiment: 'NEG', count: summary.negative },
        ].map(({ key, sentiment, count }) => {
          const cfg = sentimentConfig[sentiment];
          const Icon = cfg.icon;
          return (
            <Card key={key} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-4 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${cfg.color.split(' ')[0]} flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${cfg.color.split(' ')[1]}`} />
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

      {/* Reviews List */}
      <div className="space-y-3">
        {reviews.map(review => {
          const sCfg = sentimentConfig[review.sentiment] || sentimentConfig.NEU;
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
                    <Badge className={`${sCfg.color} border text-xs`}>{sCfg.label}</Badge>
                    <Badge variant="secondary" className="text-xs">{review.source_type === 'GOOGLE_REVIEWS' ? 'Google' : 'TripAdvisor'}</Badge>
                  </div>
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">{formatDate(review.created_at)}</span>
                </div>
                <p className="text-sm mb-2">{review.text}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[hsl(var(--muted-foreground))]\">by {review.author_name}</span>
                  <div className="flex gap-2">
                    {review.replied || review.reply ? (
                      <Badge className="bg-emerald-500/10 text-emerald-400 text-xs">Replied</Badge>
                    ) : (
                      <Button size="sm" variant="outline" className="text-xs h-7" onClick={() => {
                        setSelectedReview(review);
                        setReplyText('');
                        setAiSuggestion(null);
                        suggestMutation.mutate(review.id);
                      }} data-testid={`reply-review-${review.id}`}>
                        <MessageSquare className="w-3 h-3 mr-1" /> Reply
                      </Button>
                    )}
                    {review.last_updated_by && (
                      <span className="text-[10px] text-[hsl(var(--muted-foreground))] self-center">by {review.last_updated_by}</span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
        {reviews.length === 0 && (
          <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
            <Star className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p>No reviews yet</p>
            <Button variant="outline" className="mt-3" onClick={() => pullMutation.mutate()}>Pull from connectors</Button>
          </div>
        )}
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
                    <span className="text-xs text-[hsl(var(--muted-foreground))] ml-2">{selectedReview.author_name}</span>
                  </div>
                  <p className="text-sm">{selectedReview.text}</p>
                </div>

                {(aiSuggestion || suggestMutation.isPending) && (
                  <div className="p-3 bg-[hsl(var(--primary)/0.05)] border border-[hsl(var(--primary)/0.2)] rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
                        <span className="text-xs font-medium text-[hsl(var(--primary))]">AI Suggested Reply</span>
                      </div>
                      {aiSuggestion?.usage && (
                        <span className="text-[10px] text-[hsl(var(--muted-foreground))]">{aiSuggestion.usage.used}/{aiSuggestion.usage.limit}</span>
                      )}
                    </div>
                    {suggestMutation.isPending ? (
                      <div className="flex items-center gap-2 text-xs"><Loader2 className="w-3 h-3 animate-spin" /> Generating...</div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <p className="text-sm flex-1">{aiSuggestion?.suggestion}</p>
                        <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setReplyText(aiSuggestion?.suggestion || '')}>Use</Button>
                      </div>
                    )}
                  </div>
                )}

                <Textarea value={replyText} onChange={(e) => setReplyText(e.target.value)} placeholder="Write your reply..." className="bg-[hsl(var(--secondary))] min-h-[100px]" data-testid="review-reply-text" />
                <Button onClick={() => replyMutation.mutate({ reviewId: selectedReview.id, text: replyText })} disabled={!replyText.trim()} className="w-full" data-testid="submit-review-reply">
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
