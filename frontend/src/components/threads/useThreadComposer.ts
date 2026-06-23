import { useState, useCallback } from 'react';

interface UseThreadComposerParams {
  initialTitle?: string;
  initialBody?: string;
  initialCategory?: string;
  initialTags?: string[];
  onSubmit: (title: string, body: string, category: string, tags: string[]) => Promise<void>;
}

export function useThreadComposer({
  initialTitle = '',
  initialBody = '',
  initialCategory = 'General',
  initialTags = [],
  onSubmit,
}: UseThreadComposerParams) {
  const [title, setTitle] = useState(initialTitle);
  const [body, setBody] = useState(initialBody);
  const [category, setCategory] = useState(initialCategory);
  const [tagsInput, setTagsInput] = useState(initialTags.join(', '));
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Field validation errors
  const [titleError, setTitleError] = useState<string | null>(null);
  const [bodyError, setBodyError] = useState<string | null>(null);
  const [tagsError, setTagsError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const getTagsArray = useCallback((): string[] => {
    return tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
  }, [tagsInput]);

  const validate = useCallback((): boolean => {
    let isValid = true;
    
    // Title validations (min: 8, max: 120)
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setTitleError('Title is required.');
      isValid = false;
    } else if (trimmedTitle.length < 8) {
      setTitleError('Title must be at least 8 characters.');
      isValid = false;
    } else if (trimmedTitle.length > 120) {
      setTitleError('Title cannot exceed 120 characters.');
      isValid = false;
    } else {
      setTitleError(null);
    }

    // Body validations (min: 20, max: 3000)
    const trimmedBody = body.trim();
    if (!trimmedBody) {
      setBodyError('Description is required.');
      isValid = false;
    } else if (trimmedBody.length < 20) {
      setBodyError('Description must be at least 20 characters.');
      isValid = false;
    } else if (trimmedBody.length > 3000) {
      setBodyError('Description cannot exceed 3000 characters.');
      isValid = false;
    } else {
      setBodyError(null);
    }

    // Optional tags validation: max 5 tags
    const tags = getTagsArray();
    if (tags.length > 5) {
      setTagsError('You can add a maximum of 5 tags.');
      isValid = false;
    } else {
      setTagsError(null);
    }

    return isValid;
  }, [title, body, getTagsArray]);

  const isDirty = useCallback((): boolean => {
    const origTags = initialTags.join(', ');
    return (
      title.trim() !== initialTitle.trim() ||
      body.trim() !== initialBody.trim() ||
      category !== initialCategory ||
      tagsInput.trim() !== origTags.trim()
    );
  }, [title, body, category, tagsInput, initialTitle, initialBody, initialCategory, initialTags]);

  const reset = useCallback(() => {
    setTitle(initialTitle);
    setBody(initialBody);
    setCategory(initialCategory);
    setTagsInput(initialTags.join(', '));
    setTitleError(null);
    setBodyError(null);
    setTagsError(null);
    setGeneralError(null);
  }, [initialTitle, initialBody, initialCategory, initialTags]);

  const submit = useCallback(async (): Promise<boolean> => {
    if (!validate()) return false;
    setIsSubmitting(true);
    setGeneralError(null);

    try {
      const tags = getTagsArray();
      await onSubmit(title.trim(), body.trim(), category, tags);
      return true;
    } catch (err: any) {
      setGeneralError(err.message || 'An unexpected error occurred.');
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, [title, body, category, getTagsArray, validate, onSubmit]);

  return {
    title,
    setTitle,
    body,
    setBody,
    category,
    setCategory,
    tagsInput,
    setTagsInput,
    isSubmitting,
    titleError,
    bodyError,
    tagsError,
    generalError,
    isDirty,
    reset,
    submit,
    validate,
  };
}
