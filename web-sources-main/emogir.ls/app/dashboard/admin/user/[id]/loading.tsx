export default function Loading() {
  return (
    <div className="min-h-screen bg-black/40 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="space-y-3">
            <div className="h-8 w-48 bg-white/5 animate-pulse rounded" />
            <div className="h-5 w-32 bg-white/5 animate-pulse rounded" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-black/20 border border-white/5 rounded-xl p-6"
            >
              <div className="h-7 w-40 bg-white/5 animate-pulse rounded mb-6" />
              <div className="space-y-4">
                {[1, 2, 3].map((j) => (
                  <div
                    key={j}
                    className="h-12 bg-white/5 animate-pulse rounded"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
