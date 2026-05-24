export default function ErrorState({
  message = 'An unexpected error occurred.',
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-2xl border border-rose-100 bg-rose-50/50 p-8 text-center max-w-md mx-auto my-8">
      <span className="text-4xl mb-4 block">⚠️</span>
      <h3 className="text-md font-bold text-rose-900 mb-2">Operation Error</h3>
      <p className="text-sm font-medium text-rose-700 mb-6">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-rose-500 transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}
