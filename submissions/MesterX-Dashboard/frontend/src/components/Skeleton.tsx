export function Skeleton({ h = 16, w = '100%', style }: { h?: number; w?: number | string; style?: React.CSSProperties }) {
  return <div className="skeleton" style={{ height: h, width: w, ...style }} />;
}

export function SkeletonBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="skeleton-block">
      <Skeleton h={20} w="40%" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} h={14} w="100%" />
      ))}
    </div>
  );
}