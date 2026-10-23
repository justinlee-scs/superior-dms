import { useEffect, useState } from "react";
import CorrectionReview from "@/app/components/correction-review";
import { apiFetch } from "@/lib/api";

interface QueueItem {
  id: string;
  document_version_id: string;
  status: string;
  created_at: string;
  low_confidence_field_count: number;
  total_field_count: number;
  filename: string;
  document_type: string | null;
}

export default function CorrectionQueuePage({
  darkMode,
  onDocumentChanged,
}: {
  darkMode: boolean;
  onDocumentChanged?: () => void;
}) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  const refreshQueue = () => {
    setLoading(true);
    return apiFetch<QueueItem[]>("/correction-queue")
      .then(setQueue)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refreshQueue();
  }, []);

  if (loading) {
    return <div className="p-8 text-sm text-gray-500">Loading correction queue…</div>;
  }

  if (queue.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
        <div className="text-3xl">✅</div>
        <p className={darkMode ? "text-gray-300" : "text-gray-600"}>
          Nothing needs review right now.
        </p>
      </div>
    );
  }

  const current = queue[index];

  return (
    <CorrectionReview
      key={current.document_version_id}
      documentVersionId={current.document_version_id}
      filename={current.filename}
      documentTypeLabel={current.document_type ?? undefined}
      position={{ index, total: queue.length }}
      onPrev={index > 0 ? () => setIndex((i) => i - 1) : undefined}
      onNext={index < queue.length - 1 ? () => setIndex((i) => i + 1) : undefined}
      onSubmitted={() => {
        // Document leaves the queue on submit - refresh and stay at the
        // same index (which now points to the next item), or step back
        // one if we just submitted the last item in the list.
        onDocumentChanged?.();
        refreshQueue().then(() => {
          setIndex((i) => Math.min(i, Math.max(0, queue.length - 2)));
        });
      }}
    />
  );
}
