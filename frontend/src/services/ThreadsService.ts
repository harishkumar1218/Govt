import { apiUrl } from '../config/api';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('auth_token');
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Token ${token}` : '',
  };
}

export interface Answer {
  id: number;
  threadId: number;
  body: string;
  authorId: number;
  authorName: string;
  authorAvatarUrl?: string;
  createdAt: string;
  updatedAt: string;
  upvoteCount: number;
  hasCurrentUserUpvoted: boolean;
  isAccepted?: boolean;
}

export interface Thread {
  id: number;
  title: string;
  body: string;
  category: string;
  tags: string[];
  authorId: number;
  authorName: string;
  authorAvatarUrl?: string;
  createdAt: string;
  updatedAt: string;
  upvoteCount: number;
  answerCount: number;
  viewCount?: number;
  hasCurrentUserUpvoted: boolean;
  isSolved?: boolean;
  acceptedAnswerId?: number | null;
  shareUrl?: string;
  answers?: Answer[];
}

export interface ThreadStats {
  totalThreads: number;
  totalAnswers: number;
  categoryCounts: Record<string, number>;
}

export interface ListThreadsParams {
  search?: string;
  sort?: string;
  category?: string;
  page?: number;
  pageSize?: number;
}

export interface PaginatedThreads {
  results: Thread[];
  totalCount: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export const ThreadsService = {
  async listThreads(params?: ListThreadsParams): Promise<PaginatedThreads> {
    const query = new URLSearchParams();
    if (params?.search) query.append('q', params.search);
    if (params?.sort) query.append('sort', params.sort);
    if (params?.category) query.append('category', params.category);
    if (params?.page) query.append('page', String(params.page));
    if (params?.pageSize) query.append('pageSize', String(params.pageSize));

    const queryString = query.toString() ? `?${query.toString()}` : '';

    const res = await fetch(apiUrl(`/api/threads/${queryString}`), {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load threads');
    const data = await res.json();

    // Normalizer helper: handles both legacy unpaginated array responses and paginated responses
    if (Array.isArray(data)) {
      return {
        results: data,
        totalCount: data.length,
        page: 1,
        pageSize: data.length || 10,
        hasMore: false,
      };
    }

    return {
      results: data.results || [],
      totalCount: data.totalCount ?? 0,
      page: data.page ?? 1,
      pageSize: data.pageSize ?? 10,
      hasMore: data.hasMore ?? false,
    };
  },

  async getThreadById(id: number): Promise<Thread> {
    const res = await fetch(apiUrl(`/api/threads/${id}/`), {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error(`Failed to load thread ${id}`);
    return res.json();
  },

  async getStats(): Promise<ThreadStats> {
    const res = await fetch(apiUrl('/api/threads/stats/'), {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load thread statistics');
    return res.json();
  },

  async createThread(title: string, body: string, category: string, tags?: string[]): Promise<Thread> {
    const res = await fetch(apiUrl('/api/threads/'), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ title, body, category, tags: tags || [] }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create thread');
    }
    return res.json();
  },

  async updateThread(id: number, title: string, body: string, category: string, tags?: string[], isSolved?: boolean): Promise<Thread> {
    const payload: Record<string, any> = { title, body, category };
    if (tags !== undefined) payload.tags = tags;
    if (isSolved !== undefined) payload.isSolved = isSolved;

    const res = await fetch(apiUrl(`/api/threads/${id}/`), {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update thread');
    }
    return res.json();
  },

  async deleteThread(id: number): Promise<void> {
    const res = await fetch(apiUrl(`/api/threads/${id}/`), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete thread');
  },

  async upvoteThread(id: number): Promise<{ upvoteCount: number; hasCurrentUserUpvoted: boolean }> {
    const res = await fetch(apiUrl(`/api/threads/${id}/upvote/`), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to upvote thread');
    return res.json();
  },

  async removeThreadUpvote(id: number): Promise<{ upvoteCount: number; hasCurrentUserUpvoted: boolean }> {
    const res = await fetch(apiUrl(`/api/threads/${id}/upvote/`), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to remove thread upvote');
    return res.json();
  },

  async createAnswer(threadId: number, body: string): Promise<Answer> {
    const res = await fetch(apiUrl(`/api/threads/${threadId}/answers/`), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ body }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to submit answer');
    }
    return res.json();
  },

  async updateAnswer(answerId: number, body: string): Promise<Answer> {
    const res = await fetch(apiUrl(`/api/threads/answers/${answerId}/`), {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ body }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update answer');
    }
    return res.json();
  },

  async deleteAnswer(answerId: number): Promise<void> {
    const res = await fetch(apiUrl(`/api/threads/answers/${answerId}/`), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete answer');
  },

  async upvoteAnswer(answerId: number): Promise<{ upvoteCount: number; hasCurrentUserUpvoted: boolean }> {
    const res = await fetch(apiUrl(`/api/threads/answers/${answerId}/upvote/`), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to upvote answer');
    return res.json();
  },

  async removeAnswerUpvote(answerId: number): Promise<{ upvoteCount: number; hasCurrentUserUpvoted: boolean }> {
    const res = await fetch(apiUrl(`/api/threads/answers/${answerId}/upvote/`), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to remove answer upvote');
    return res.json();
  },

  async acceptAnswer(threadId: number, answerId: number): Promise<{ isSolved: boolean; acceptedAnswerId: number | null }> {
    const res = await fetch(apiUrl(`/api/threads/${threadId}/answers/${answerId}/accept/`), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to accept answer');
    }
    return res.json();
  },

  async unacceptAnswer(threadId: number, answerId: number): Promise<{ isSolved: boolean; acceptedAnswerId: number | null }> {
    const res = await fetch(apiUrl(`/api/threads/${threadId}/answers/${answerId}/accept/`), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to unaccept answer');
    }
    return res.json();
  },
};
