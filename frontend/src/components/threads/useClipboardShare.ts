import { useCallback } from 'react';
import { useToast } from './ToastContext';

export function useClipboardShare() {
  const { showToast } = useToast();

  const shareThread = useCallback(async (threadId: number, threadTitle: string) => {
    const shareUrl = `${window.location.origin}/?tab=threads&threadId=${threadId}`;
    try {
      if (navigator.share) {
        await navigator.share({
          title: threadTitle,
          text: `Check out this UPSC doubt thread: ${threadTitle}`,
          url: shareUrl,
        });
      } else {
        await navigator.clipboard.writeText(shareUrl);
        showToast('Link copied to clipboard!', 'success');
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        try {
          await navigator.clipboard.writeText(shareUrl);
          showToast('Link copied to clipboard!', 'success');
        } catch {
          showToast('Could not copy link.', 'error');
        }
      }
    }
  }, [showToast]);

  return { shareThread };
}
